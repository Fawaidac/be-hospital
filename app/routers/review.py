# app/routers/review.py
from fastapi import APIRouter, Depends, status, Body
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.review import GoogleReviewModel
from app.models.user import UserModel
from app.schemas.review import GoogleReviewWebhook, ReviewResponse, WebhookData, UpdateTemplateRequest
from app.schemas.base import BaseResponse, ApiResponse
from app.services.review_bot import ReviewBotService
from app.models.review_template import ReviewTemplateModel

router = APIRouter(prefix="/api", tags=["Review"])


@router.post("/webhook/google-review", status_code=201, response_model=BaseResponse[WebhookData])
async def handle_google_review_webhook(payload: GoogleReviewWebhook, db: Session = Depends(get_db_main)):
    existing_review = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == payload.review_id).first()

    if existing_review:
        return ApiResponse.error(message="This review ID has already been processed.", code=400)
    
    rating_int = ReviewBotService.parse_rating(payload.rating)

    is_asking = await ReviewBotService.is_customer_asking(payload.comment)

    if rating_int in [1, 2] or is_asking:
        new_review = GoogleReviewModel(
            review_id=payload.review_id,
            reviewer_name=payload.reviewer_name,
            rating=rating_int,
            comment=payload.comment,
            reply_text=None, 
            status="pending",
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        log_msg = "Pertanyaan terdeteksi oleh AI." if is_asking else "Review rating rendah."
        return ApiResponse.success(
            data=WebhookData(
                review_id=new_review.review_id,
                reviewer_name=new_review.reviewer_name,
                rating=new_review.rating,
                bot_status=new_review.status,
                reply_text="",
            ),
            message=f"{log_msg} Dialihkan ke antrean manual dashboard Humas.",
            code=201
        )
    
    else:

        bot_reply = await ReviewBotService.generate_reply_template(payload.rating, db)

        new_review = GoogleReviewModel(
            review_id=payload.review_id,
            reviewer_name=payload.reviewer_name,
            rating=payload.rating,
            comment=payload.comment,
            reply_text=bot_reply,
            status="pending",
        )

        db.add(new_review)
        db.commit()  
        db.refresh(new_review)

        is_success = await ReviewBotService.send_reply_to_google(payload.review_id, bot_reply)

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

@router.post("/reviews/{review_id}/reply", response_model=BaseResponse[dict])
async def reply_review_manually(
    review_id: str,
    reply_text: str = Body(..., embed=True),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint khusus untuk Humas membalas review bintang 1 & 2 secara manual melalui Dashboard"""
    review = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()

    if not review:
        return ApiResponse.error(message="Data review tidak ditemukan di database.", code=404)

    if review.status == "replied":
        return ApiResponse.error(message="Review ini sudah pernah dibalas sebelumnya.", code=400)

    is_success = await ReviewBotService.send_reply_to_google(review_id, reply_text)

    if is_success:
        review.reply_text = reply_text
        review.status = "replied"
        db.commit()
        return ApiResponse.success(
            data={"review_id": review_id, "status": "replied"},
            message="Balasan manual Anda berhasil dikirim ke Google Maps!",
            code=200
        )
    else:
        review.status = "failed"
        db.commit()
        return ApiResponse.error(message="Gagal mengirimkan balasan ke Google API. Periksa koneksi/token.", code=500)
    
@router.get("/reviews", response_model=BaseResponse[List[ReviewResponse]])
def get_all_reviews_for_dashboard(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    reviews = db.query(GoogleReviewModel).order_by(GoogleReviewModel.created_at.desc()).all()

    return ApiResponse.success(
        data=reviews,
        message="The review data has been successfully retrieved.",
        code=200
    )


@router.post("/reviews/sync", response_model=BaseResponse[dict])
async def sync_old_reviews(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    old_reviews = await ReviewBotService.fetch_and_sync_old_reviews()
    count_saved = 0

    for rev in old_reviews:
        review_id = rev.get("reviewId")
        existing = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()

        if not existing:
            rating = ReviewBotService.parse_rating(rev.get("starRating"))
            comment = rev.get("comment", "")
            reviewer_name = rev.get("reviewer", {}).get("displayName", "Pasien")
            bot_reply = await ReviewBotService.generate_reply_template(rating, db)

            has_replied = "reviewReply" in rev
            status_reply = "replied"

            if not has_replied:
                success = await ReviewBotService.send_reply_to_google(review_id, bot_reply)
                status_reply = "replied" if success else "failed"
            else:
                bot_reply = rev["reviewReply"].get("comment", bot_reply)

            raw_time = rev.get("createTime")
            parsed_date = datetime.now()
            if raw_time:
                try:
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
                created_at=parsed_date
            )
            db.add(new_review)
            count_saved += 1

    if count_saved > 0:
        db.commit()

    return ApiResponse.success(
        data={"synchronized_count": count_saved},
        message=f"Successfully synchronized {count_saved} old reviews.",
        code=200
    )



@router.post("/reviews/templates", response_model=BaseResponse[dict])
def create_review_template(
    payload: UpdateTemplateRequest,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint murni untuk menambah template baru (Create)"""
    existing_template = db.query(ReviewTemplateModel).filter(ReviewTemplateModel.rating == payload.rating).first()
    
    if existing_template:
        return ApiResponse.error(message=f"Template untuk bintang {payload.rating} sudah ada. Gunakan method PUT untuk update.", code=400)
        
    new_template = ReviewTemplateModel(
        rating=payload.rating,
        template_text=payload.template_text
    )
    db.add(new_template)
    db.commit()
    
    return ApiResponse.success(data={"rating": payload.rating}, message="Template baru berhasil disimpan.", code=201)   

@router.get("/reviews/templates", response_model=BaseResponse[List[dict]])
def get_all_review_templates(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint untuk mengambil semua daftar master template yang ada di database"""
    templates = db.query(ReviewTemplateModel).order_by(ReviewTemplateModel.rating.asc()).all()
    
    data_list = [
        {
            "id": t.id,
            "rating": t.rating,
            "template_text": t.template_text,
            "updated_at": t.updated_at
        }
        for t in templates
    ]

    return ApiResponse.success(
        data=data_list,
        message="get all review templates success",
        code=200
    )

@router.put("/reviews/templates/{rating}", response_model=BaseResponse[dict])
def update_review_template(
    rating: int,
    template_text: str = Body(..., embed=True),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint murni untuk mengubah isi template yang sudah ada (Update)"""
    template = db.query(ReviewTemplateModel).filter(ReviewTemplateModel.rating == rating).first()
    
    if not template:
        return ApiResponse.error(message=f"Template untuk bintang {rating} belum dibuat. Gunakan method POST dulu.", code=404)
        
    template.template_text = template_text
    db.commit()
    
    return ApiResponse.success(data={"rating": rating}, message="Template berhasil diperbarui.", code=200)

@router.delete("/reviews/templates/{rating}", response_model=BaseResponse[dict])
def delete_review_template(
    rating: int,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint untuk menghapus template otomatis berdasarkan rating bintangnya"""
    template = db.query(ReviewTemplateModel).filter(ReviewTemplateModel.rating == rating).first()

    if not template:
        return ApiResponse.error(message=f"Template untuk bintang {rating} tidak ditemukan.", code=404)

    db.delete(template)
    db.commit()

    return ApiResponse.success(
        data={"deleted_rating": rating},
        message=f"Template untuk ulasan bintang {rating} berhasil dihapus.",
        code=200
    )