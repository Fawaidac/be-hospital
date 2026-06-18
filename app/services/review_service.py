# app/services/review_service.py
import asyncio
import random
from sqlalchemy import text

from app.core.database import SessionLocalMain
from app.services.review_bot import ReviewBotService
from app.services.logger_service import ActivityLogger


def save_review_to_db_sync(
    review_id: str,
    reviewer_name: str,
    rating: str,
    comment: str,
    reply_text: str
):
    """
    Fungsi sinkron untuk menyimpan log balasan review ke database.
    Dijalankan di threadpool agar tidak memblokir event loop asyncio.
    """
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
        ActivityLogger.log(
            db=db,
            action="REVIEW_BOT_REPLY",
            description=f"Bot automatically replied to review '{review_id}' with rating {ReviewBotService.parse_rating(rating)}."
        )
        print(f"💾 [ReviewBot] Berhasil menyimpan balasan ulasan ID {review_id} ke DB.")
    except Exception as db_err:
        db.rollback()
        print(f"❌ [ReviewBot] Gagal menyimpan ke DB: {str(db_err)}")
    finally:
        db.close()


async def google_review_bot_worker(replied_reviews_cache: set):
    """
    Background worker yang berjalan setiap 5 menit.
    Mengambil review terbaru dari Google API dan membalas yang belum dibalas.
    """
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

                    db_session = SessionLocalMain()
                    try:
                        bot_reply = await ReviewBotService.generate_reply_template(rating, db_session)
                    finally:
                        db_session.close()
                    success = await ReviewBotService.send_reply_to_google(review_id, bot_reply)

                    if success:
                        replied_reviews_cache.add(review_id)

                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(
                            None,
                            save_review_to_db_sync,
                            review_id,
                            r.get("reviewer", {}).get("displayName", "Pasien"),
                            rating,
                            r.get("comment", ""),
                            bot_reply
                        )

                        await asyncio.sleep(random.randint(3, 7))

        except Exception as e:
            print(f"❌ [ReviewBot] Terjadi kendala pada background worker: {str(e)}")

        await asyncio.sleep(300)
