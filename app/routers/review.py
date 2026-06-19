# app/routers/review.py
from fastapi import APIRouter, Depends, status, Body, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import case, func, text
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.review import GoogleReviewModel, ReviewKeywordModel
from app.models.user import UserModel
from app.schemas.review import (
    DashboardStatsResponse, GoogleReviewWebhook, ReviewResponse, 
    WebhookData, UpdateTemplateRequest, SentimentAnalysisResponse, SentimentDetail, KeywordTrendDetail
)
from app.schemas.base import BaseResponse, ApiResponse
from app.services.review_bot import ReviewBotService
from app.models.review_template import ReviewTemplateModel
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api", tags=["Review"])

@router.post("/webhook/google-review", status_code=201, response_model=BaseResponse[WebhookData])
async def handle_google_review_webhook(payload: GoogleReviewWebhook, db: Session = Depends(get_db_main)):
    existing_review = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == payload.review_id).first()

    if existing_review:
        return ApiResponse.error(message="This review ID has already been processed.", code=400)
    
    rating_int = ReviewBotService.parse_rating(payload.rating)
    ai_analysis = await ReviewBotService.analyze_review_intent_and_sentiment(payload.comment, rating_int)
    is_asking = ai_analysis["is_asking"]
    detected_sentiment = ai_analysis["sentiment"]

    if rating_int in [1, 2] or is_asking:
        new_review = GoogleReviewModel(
            review_id=payload.review_id,
            reviewer_name=payload.reviewer_name,
            rating=rating_int,
            comment=payload.comment,
            reply_text=None, 
            status="pending",
            sentiment=detected_sentiment
        )
        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        for kw in ai_analysis["keywords"]:
            db.add(ReviewKeywordModel(review_id=payload.review_id, keyword=kw))
        db.commit()

        ActivityLogger.log(
            db=db,
            action="REVIEW_MANUAL_QUEUE",
            description=f"Review '{new_review.review_id}' from '{new_review.reviewer_name}' was added to the manual queue."
        )

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
            sentiment=detected_sentiment
        )

        db.add(new_review)
        db.commit()  
        db.refresh(new_review)

        for kw in ai_analysis["keywords"]:
            db.add(ReviewKeywordModel(review_id=payload.review_id, keyword=kw))
        db.commit()

        is_success = await ReviewBotService.send_reply_to_google(payload.review_id, bot_reply)
        new_review.status = "replied" if is_success else "failed"
        if is_success:
            new_review.replied_at = func.now()
        db.commit()

        ActivityLogger.log(
            db=db,
            action="REVIEW_AUTO_REPLY" if is_success else "REVIEW_AUTO_REPLY_FAILED",
            description=f"Bot {'replied to' if is_success else 'failed to reply to'} review '{new_review.review_id}' with rating {new_review.rating}."
        )

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
    review = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()
    if not review:
        return ApiResponse.error(message="Data review tidak ditemukan di database.", code=404)
    if review.status == "replied":
        return ApiResponse.error(message="Review ini sudah pernah dibalas sebelumnya.", code=400)

    is_success = await ReviewBotService.send_reply_to_google(review_id, reply_text)
    if is_success:
        review.reply_text = reply_text
        review.status = "replied"
        review.replied_at = func.now()
        db.commit()
        ActivityLogger.log(
            db=db, username=current_user.username, action="REVIEW_MANUAL_REPLY",
            description=f"User '{current_user.username}' manually replied to review '{review_id}'."
        )
        return ApiResponse.success(data={"review_id": review_id, "status": "replied"}, message="Balasan manual Anda berhasil dikirim!", code=200)
    else:
        review.status = "failed"
        db.commit()
        ActivityLogger.log(
            db=db, username=current_user.username, action="REVIEW_MANUAL_REPLY_FAILED",
            description=f"User '{current_user.username}' failed manual reply for '{review_id}'."
        )
        return ApiResponse.error(message="Gagal mengirimkan balasan ke Google API.", code=500)
    
@router.get("/reviews", response_model=BaseResponse[List[ReviewResponse]])
def get_all_reviews_for_dashboard(
    status: Optional[str] = Query(None, description="Filter berdasarkan status: 'pending' atau 'replied'"),
    time_range: Optional[str] = Query(None, description="Filter waktu: '7_days', '30_days', atau 'all_time'"),
    rating: Optional[int] = Query(None, description="Filter rating bintang: 1 sampai 5", ge=1, le=5),
    sentiment: Optional[str] = Query(None, description="Filter sentimen: 'POSITIVE', 'NEUTRAL', atau 'NEGATIVE'"),
    limit: Optional[int] = Query(None, description="Membatasi jumlah data ulasan yang ditarik", ge=1),
    db: Session = Depends(get_db_main), 
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(GoogleReviewModel).options(joinedload(GoogleReviewModel.keywords_rel))

    if status:
        query = query.filter(GoogleReviewModel.status == status.lower())

    if rating:
        query = query.filter(GoogleReviewModel.rating == rating)

    if sentiment:
        query = query.filter(GoogleReviewModel.sentiment == sentiment.upper())

    if time_range:
        now = datetime.now()
        if time_range == "7_days":
            start_date = now - timedelta(days=7)
            query = query.filter(GoogleReviewModel.created_at >= start_date)
        elif time_range == "30_days":
            start_date = now - timedelta(days=30)
            query = query.filter(GoogleReviewModel.created_at >= start_date)

    query = query.order_by(GoogleReviewModel.created_at.desc())
    
    if limit:
        query = query.limit(limit)

    reviews_db = query.all()

    formatted_reviews = []
    for r in reviews_db:
        formatted_reviews.append(
            ReviewResponse(
                id=r.id,
                review_id=r.review_id,
                reviewer_name=r.reviewer_name,
                rating=r.rating,
                comment=r.comment,
                reply_text=r.reply_text,
                status=r.status,
                sentiment=r.sentiment,
                created_at=r.created_at,
                replied_at=r.replied_at,
                keywords=[k.keyword for k in r.keywords_rel] 
            )
        )

    return ApiResponse.success(
        data=formatted_reviews, 
        message="The review data has been successfully filtered and retrieved.", 
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
            
            ai_analysis = await ReviewBotService.analyze_review_intent_and_sentiment(comment, rating)
            is_asking = ai_analysis["is_asking"]
            detected_sentiment = ai_analysis["sentiment"]

            raw_create_time = rev.get("createTime")
            review_created_at = datetime.now()
            if raw_create_time:
                try:
                    review_created_at = datetime.fromisoformat(raw_create_time.replace("Z", "+00:00"))
                except ValueError:
                    review_created_at = datetime.now()

            has_replied = "reviewReply" in rev
            review_replied_at = None

            if has_replied:
                bot_reply = rev["reviewReply"].get("comment", "")
                status_reply = "replied"
                
                raw_reply_time = rev["reviewReply"].get("updateTime")
                if raw_reply_time:
                    try:
                        review_replied_at = datetime.fromisoformat(raw_reply_time.replace("Z", "+00:00"))
                    except ValueError:
                        review_replied_at = review_created_at 
                else:
                    review_replied_at = review_created_at
            else:
                if rating in [1, 2] or is_asking:
                    bot_reply = None
                    status_reply = "pending"
                    review_replied_at = None
                else:
                    bot_reply = await ReviewBotService.generate_reply_template(rating, db)
                    success = await ReviewBotService.send_reply_to_google(review_id, bot_reply)
                    status_reply = "replied" if success else "failed"
                    review_replied_at = datetime.now() if success else None

            new_review = GoogleReviewModel(
                review_id=review_id,
                reviewer_name=reviewer_name,
                rating=rating,
                comment=comment,
                reply_text=bot_reply,
                status=status_reply,
                sentiment=detected_sentiment,
                created_at=review_created_at, 
                replied_at=review_replied_at 
            )
            db.add(new_review)
            db.commit()

            for kw in ai_analysis["keywords"]:
                db.add(ReviewKeywordModel(review_id=review_id, keyword=kw))
            db.commit()
            
            count_saved += 1
            await asyncio.sleep(4.0) 

    if count_saved > 0:
        ActivityLogger.log(
            db=db, username=current_user.username, action="REVIEW_SYNC",
            description=f"User '{current_user.username}' synchronized {count_saved} old reviews."
        )

    return ApiResponse.success(data={"synchronized_count": count_saved}, message=f"Successfully synchronized {count_saved} reviews.", code=200)

@router.get("/reviews/stats", response_model=BaseResponse[DashboardStatsResponse])
def get_dashboard_statistics(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint komplit untuk menyuplai data 3 kartu metrik utama beserta tren komparasi waktu"""
    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    sixty_days_ago = now - timedelta(days=60)

    stats = db.query(
        func.count(GoogleReviewModel.id).label("total"),
        func.avg(GoogleReviewModel.rating).label("average"),
        func.sum(case((GoogleReviewModel.created_at >= thirty_days_ago, 1), else_=0)).label("total_this_month"),
        func.sum(
            case(
                (
                    (GoogleReviewModel.sentiment == "POSITIVE")
                    & (GoogleReviewModel.created_at >= thirty_days_ago),
                    1,
                ),
                else_=0,
            )
        ).label("positive_this_month"),
        func.sum(
            case(
                (
                    (GoogleReviewModel.created_at >= sixty_days_ago)
                    & (GoogleReviewModel.created_at < thirty_days_ago),
                    1,
                ),
                else_=0,
            )
        ).label("total_last_month"),
        func.sum(
            case(
                (
                    (GoogleReviewModel.sentiment == "POSITIVE")
                    & (GoogleReviewModel.created_at >= sixty_days_ago)
                    & (GoogleReviewModel.created_at < thirty_days_ago),
                    1,
                ),
                else_=0,
            )
        ).label("positive_last_month"),
        func.sum(case((GoogleReviewModel.status == "pending", 1), else_=0)).label("pending_count"),
    ).first()

    total_reviews = stats.total or 0
    rating_average = round(float(stats.average), 1) if stats.average is not None else 0.0
    positive_vibes = 0.0
    positive_trend = 0.0
    avg_response_hours = 0.0
    target_diff_minutes = 0
    pending_count = stats.pending_count or 0

    if total_reviews > 0:
        total_this_month = stats.total_this_month or 0
        positive_this_month = stats.positive_this_month or 0
        total_last_month = stats.total_last_month or 0
        positive_last_month = stats.positive_last_month or 0

        this_month_ratio = float((positive_this_month / total_this_month) * 100) if total_this_month > 0 else 0.0
        last_month_ratio = float((positive_last_month / total_last_month) * 100) if total_last_month > 0 else 0.0

        positive_vibes = round(this_month_ratio, 1)
        positive_trend = round(this_month_ratio - last_month_ratio, 1) 

        avg_seconds = db.query(
            func.avg(func.timestampdiff(text("SECOND"), GoogleReviewModel.created_at, GoogleReviewModel.replied_at))
        ).filter(
            GoogleReviewModel.status == "replied",
            GoogleReviewModel.replied_at.isnot(None)
        ).scalar()

        if avg_seconds is not None:
            actual_minutes = float(avg_seconds) / 60
            avg_response_hours = round(actual_minutes / 60, 1)

            target_minutes = 162
            target_diff_minutes = int(round(actual_minutes - target_minutes))

    return ApiResponse.success(
        data=DashboardStatsResponse(
            total_reviews=total_reviews,
            rating_average=rating_average,
            positive_vibes_percentage=positive_vibes,
            positive_vibes_trend_percentage=positive_trend,         # Dinamik untuk teks bawah Kotak 1
            avg_response_hours=avg_response_hours,
            response_target_difference_minutes=target_diff_minutes, # Dinamik untuk teks bawah Kotak 2 (-18m)
            pending_count=pending_count
        ),
        message="Successfully synchronized metadata card constraints.",
        code=200
    )

@router.get("/reviews/sentiment-analysis", response_model=BaseResponse[SentimentAnalysisResponse])
def get_sentiment_and_keyword_analysis(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint terpadu untuk menyuplai grafik lingkaran, rincian bar sentimen, dan tren chip hashtag"""
    
    total_reviews = db.query(func.count(GoogleReviewModel.id)).scalar() or 0

    sentiment_groups = db.query(
        GoogleReviewModel.sentiment, 
        func.count(GoogleReviewModel.id)
    ).group_by(GoogleReviewModel.sentiment).all()
    
    counts_dict = {s: c for s, c in sentiment_groups}
    pos_count = counts_dict.get("POSITIVE", 0)
    neu_count = counts_dict.get("NEUTRAL", 0)
    neg_count = counts_dict.get("NEGATIVE", 0)

    pos_percentage = round((pos_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0
    neu_percentage = round((neu_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0
    neg_percentage = round((neg_count / total_reviews) * 100, 1) if total_reviews > 0 else 0.0

    summary_status = "Mid Vibe 😐"
    if pos_percentage >= 70:
        summary_status = "Safe Vibe 😎"
    elif pos_percentage >= 55:
        summary_status = "Mid Vibe 😐"
    elif neg_percentage >= 40:
        summary_status = "Bad Vibe 😨"

    keyword_ranking = db.query(
        ReviewKeywordModel.keyword, 
        func.count(ReviewKeywordModel.id).label("total")
    ).group_by(ReviewKeywordModel.keyword)\
     .order_by(text("total DESC"))\
     .limit(15)\
     .all()
    
    top_keywords_list = [
        KeywordTrendDetail(keyword=row[0], count=row[1]) for row in keyword_ranking
    ]

    analysis_data = SentimentAnalysisResponse(
        summary_status=summary_status,
        overall_positive_percentage=pos_percentage, # Nilai di dalam lingkaran chart (57%)
        positive=SentimentDetail(count=pos_count, percentage=pos_percentage),
        neutral=SentimentDetail(count=neu_count, percentage=neu_percentage),
        negative=SentimentDetail(count=neg_count, percentage=neg_percentage),
        top_keywords=top_keywords_list
    )

    return ApiResponse.success(
        data=analysis_data, 
        message="Sentiment and trend analysis data successfully compiled.", 
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
    ActivityLogger.log(
        db=db,
        username=current_user.username,
        action="REVIEW_TEMPLATE_CREATE",
        description=f"User '{current_user.username}' created an auto-reply template for {payload.rating}-star reviews."
    )
    
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
    ActivityLogger.log(
        db=db,
        username=current_user.username,
        action="REVIEW_TEMPLATE_UPDATE",
        description=f"User '{current_user.username}' updated the auto-reply template for {rating}-star reviews."
    )
    
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
    ActivityLogger.log(
        db=db,
        username=current_user.username,
        action="REVIEW_TEMPLATE_DELETE",
        description=f"User '{current_user.username}' deleted the auto-reply template for {rating}-star reviews."
    )

    return ApiResponse.success(
        data={"deleted_rating": rating},
        message=f"Template untuk ulasan bintang {rating} berhasil dihapus.",
        code=200
    )
