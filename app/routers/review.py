#app/routers/review.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models import GoogleReviewModel, UserModel
from app.schemas.review_schema import GoogleReviewWebhook, ReviewResponse, BaseResponse, WebhookData
from app.schemas.base_schema import ApiResponse 
from app.services.reply_generator import ReviewBotService

router = APIRouter(prefix="/api", tags=["Review"])


@router.post("/webhook/google-review", status_code=201, response_model=BaseResponse[WebhookData])
async def handle_google_review_webhook(payload: GoogleReviewWebhook, db: Session = Depends(get_db_main)):
    # 1. Validasi apakah review sudah pernah diproses sebelumnya
    existing_review = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == payload.review_id).first()

    if existing_review:
        return ApiResponse.error(message="This review ID has already been processed.", code=400)

    # 2. Generate template balasan resmi rumah sakit
    bot_reply = ReviewBotService.generate_reply_template(payload.rating)
    
    # 3. Simpan data awal dengan status pending terlebih dahulu
    new_review = GoogleReviewModel(
        review_id=payload.review_id,
        reviewer_name=payload.reviewer_name,
        rating=payload.rating,
        comment=payload.comment,
        reply_text=bot_reply,
        status="pending",
    )
    db.add(new_review)
    db.commit()  # Commit awal agar data terkunci di database dan tidak terjadi double-insert dari request lain
    db.refresh(new_review)

    # 4. Tembak balasan ke API Google secara asinkron (Jaringan I/O)
    is_success = await ReviewBotService.send_reply_to_google(payload.review_id, bot_reply)
    
    # 5. Update status akhir berdasarkan respons Google API
    new_review.status = "replied" if is_success else "failed"
    db.commit()

    return ApiResponse.success(
        data=WebhookData(
            review_id=new_review.review_id,
            reviewer_name=new_review.reviewer_name,
            rating=new_review.rating,
            bot_status=new_review.status,
            reply_text=bot_reply,
        ),
        message="The review has been saved and replied to by the bot.",
        code=201
    )


@router.get("/reviews", response_model=BaseResponse[List[ReviewResponse]])
def get_all_reviews_for_dashboard(db: Session = Depends(get_db_main), current_user: UserModel = Depends(get_current_user)):
    reviews = db.query(GoogleReviewModel).order_by(GoogleReviewModel.created_at.desc()).all()

    return ApiResponse.success(
        data=reviews,
        message="The review data has been successfully retrieved.",
        code=200
    )


@router.post("/reviews/sync", response_model=BaseResponse[dict])
async def sync_old_reviews(db: Session = Depends(get_db_main), current_user: UserModel = Depends(get_current_user)):
    old_reviews = await ReviewBotService.fetch_and_sync_old_reviews()
    count_saved = 0
    
    for rev in old_reviews:
        review_id = rev.get("reviewId")
        existing = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()

        if not existing:
            rating = ReviewBotService.parse_rating(rev.get("starRating"))
            comment = rev.get("comment", "")
            reviewer_name = rev.get("reviewer", {}).get("displayName", "Pasien")
            bot_reply = ReviewBotService.generate_reply_template(rating)

            has_replied = "reviewReply" in rev
            status_reply = "replied"

            if not has_replied:
                # Kirim ke Google jika belum dibalas sama sekali di dashboard manapun
                success = await ReviewBotService.send_reply_to_google(review_id, bot_reply)
                status_reply = "replied" if success else "failed"
            else:
                # Jika sudah dibalas manual oleh admin/humas, pakai balasan yang sudah ada di Google
                bot_reply = rev["reviewReply"].get("comment", bot_reply)

            # PERBAIKAN SINKRONISASI WAKTU: Ubah format string ISO Google ke Objek Datetime Python
            raw_time = rev.get("createTime")
            parsed_date = datetime.now() # Fallback waktu saat ini jika field kosong
            if raw_time:
                try:
                    # Menghilangkan penanda timezone 'Z' di akhir string untuk kompatibilitas database lokal
                    clean_time_str = raw_time.replace("Z", "+00:00")
                    parsed_date = datetime.fromisoformat(clean_time_str)
                except ValueError:
                    parsed_date = datetime.now()

            new_review = GoogleReviewModel(
                review_id=review_id,
                reviewer_name=reviewer_name,
                rating=rating,
                comment=comment,
                reply_text=bot_reply,
                status=status_reply,
                created_at=parsed_date  # Menggunakan hasil parsing yang aman
            )
            db.add(new_review)
            count_saved += 1

    # Lakukan commit di akhir iterasi agar eksekusi batch menjadi jauh lebih cepat
    if count_saved > 0:
        db.commit()

    return ApiResponse.success(
        data={"synchronized_count": count_saved},
        message=f"Successfully synchronized {count_saved} old reviews.",
        code=200
    )