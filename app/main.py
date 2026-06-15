import asyncio
import random  
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.core.database import BaseMain, BasePSC, engine_main, engine_psc, SessionLocalMain
from app.routers import komplain, revenue, review, auth
from app.core.security import AuthException
from app.schemas.base_schema import ApiResponse 
from app.services.reply_generator import ReviewBotService

BaseMain.metadata.create_all(bind=engine_main)
BasePSC.metadata.create_all(bind=engine_psc)

app = FastAPI(title="RSUD dr. Soebandi - Google Review Bot API")

replied_reviews_cache = set()

def save_review_to_db_sync(review_id: str, reviewer_name: str, rating: str, comment: str, reply_text: str):
    """Fungsi pembantu berbasis sinkron untuk mengamankan penulisan log ke DB"""
    db = SessionLocalMain()
    try:
        query = text("""
            INSERT INTO reviews (review_id, reviewer_name, rating, comment, reply_text, status, created_at)
            VALUES (:review_id, :reviewer_name, :rating, :comment, :reply_text, :status, NOW())
            ON DUPLICATE KEY UPDATE reply_text = :reply_text, status = :status
        """)
        db.execute(query, {
            "review_id": review_id,
            "reviewer_name": reviewer_name,
            "rating": ReviewBotService.parse_rating(rating),
            "comment": comment,
            "reply_text": reply_text,
            "status": "replied"
        })
        db.commit()
        print(f"💾 [ReviewBot] Berhasil menyimpan balasan ulasan ID {review_id} ke DB.")
    except Exception as db_err:
        db.rollback()
        print(f"❌ [ReviewBot] Gagal menyimpan ke DB: {str(db_err)}")
    finally:
        db.close()

async def google_review_bot_worker():
    """Worker otomatis 5 menitan yang aman dari deadlock session"""
    print("🤖 [ReviewBot] Worker otomatis telah aktif di latar belakang...")
    
    while True:
        try:
            print("🔄 [ReviewBot] Melakukan pengecekan review terbaru ke Google API...")
            reviews = await ReviewBotService.fetch_and_sync_old_reviews()
            
            for r in reviews:
                review_id = r.get("reviewId")
                rating = r.get("starRating")
                existing_reply = r.get("reviewReply") 

                if review_id not in replied_reviews_cache and not existing_reply:
                    print(f"📌 [ReviewBot] Menemukan review baru (ID: {review_id}) dengan Rating: {rating}")
                    
                    reply_text = ReviewBotService.generate_reply_template(rating)
                    success = await ReviewBotService.send_reply_to_google(review_id, reply_text)
                    
                    if success:
                        replied_reviews_cache.add(review_id)
                        
                        # Jalankan fungsi penyimpanan DB di dalam threadpool agar tidak memblokir event loop
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(
                            None, 
                            save_review_to_db_sync,
                            review_id,
                            r.get("reviewer", {}).get("displayName", "Pasien"),
                            rating,
                            r.get("comment", ""),
                            reply_text
                        )

                        await asyncio.sleep(random.randint(3, 7))
                        
        except Exception as e:
            print(f"❌ [ReviewBot] Terjadi kendala pada background worker: {str(e)}")
            
        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(google_review_bot_worker())

# --- Exception Handler & Router Loader Tetap Sama ---
@app.exception_handler(AuthException)
async def auth_exception_handler(request, exc: AuthException):
    return ApiResponse.error(message=exc.message, code=exc.status_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "code": 422,
            "data": exc.errors(),
        },
    )

app.include_router(auth.router)
app.include_router(review.router)
app.include_router(komplain.router) 
app.include_router(revenue.router)