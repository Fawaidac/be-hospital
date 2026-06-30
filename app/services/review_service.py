# app/services/review_service.py
import asyncio
import random
from datetime import datetime

from app.core.database import SessionLocalMain
from app.models.review import GoogleReviewModel, ReviewKeywordModel
from app.services.review_bot import ReviewBotService
from app.services.logger_service import ActivityLogger
from app.services.push_notification_service import PushNotificationService


def _parse_google_datetime(raw_value: str, fallback: datetime) -> datetime:
    """Helper untuk parse timestamp ISO dari Google API, dengan fallback aman."""
    if not raw_value:
        return fallback
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return fallback


def save_already_replied_review_sync(rev: dict, ai_keywords: list, ai_sentiment: str):
    """
    Menyimpan review yang SUDAH punya balasan di Google (dibalas manual lewat
    Google My Business, atau oleh sesi worker sebelumnya) ke database utama,
    tanpa mengirim ulang reply ke Google.
    Dijalankan di threadpool agar tidak memblokir event loop asyncio.
    """
    db = SessionLocalMain()
    try:
        review_id = rev.get("reviewId")

        existing = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()
        if existing:
            return  # sudah ada, tidak perlu insert ulang

        rating = ReviewBotService.parse_rating(rev.get("starRating"))
        reviewer_name = rev.get("reviewer", {}).get("displayName", "Pasien")
        comment = rev.get("comment", "")

        now = datetime.now()
        created_at = _parse_google_datetime(rev.get("createTime"), now)

        reply_block = rev.get("reviewReply", {})
        reply_text = reply_block.get("comment", "")
        replied_at = _parse_google_datetime(reply_block.get("updateTime"), created_at)

        new_review = GoogleReviewModel(
            review_id=review_id,
            reviewer_name=reviewer_name,
            rating=rating,
            comment=comment,
            reply_text=reply_text,
            status="replied",
            sentiment=ai_sentiment,
            created_at=created_at,
            replied_at=replied_at
        )
        db.add(new_review)
        db.commit()

        for kw in ai_keywords:
            db.add(ReviewKeywordModel(review_id=review_id, keyword=kw))
        db.commit()

        print(f"💾 [ReviewBot] Review lama '{review_id}' (sudah dibalas sebelumnya) disinkronkan ke DB.")
    except Exception as db_err:
        db.rollback()
        print(f"❌ [ReviewBot] Gagal menyinkronkan review lama ke DB: {str(db_err)}")
    finally:
        db.close()


def save_auto_replied_review_sync(
    review_id: str,
    reviewer_name: str,
    rating: str,
    comment: str,
    reply_text: str,
    ai_keywords: list,
    ai_sentiment: str
):
    """
    Menyimpan log balasan review yang BARU SAJA dibalas otomatis oleh bot ke database utama.
    Dijalankan di threadpool agar tidak memblokir event loop asyncio.
    """
    db = SessionLocalMain()
    try:
        existing = db.query(GoogleReviewModel).filter(GoogleReviewModel.review_id == review_id).first()
        if existing:
            return

        rating_int = ReviewBotService.parse_rating(rating)
        now = datetime.now()

        new_review = GoogleReviewModel(
            review_id=review_id,
            reviewer_name=reviewer_name,
            rating=rating_int,
            comment=comment,
            reply_text=reply_text,
            status="replied",
            sentiment=ai_sentiment,
            created_at=now,
            replied_at=now
        )
        db.add(new_review)
        db.commit()

        for kw in ai_keywords:
            db.add(ReviewKeywordModel(review_id=review_id, keyword=kw))
        db.commit()

        ActivityLogger.log(
            action="REVIEW_BOT_REPLY",
            description=f"Bot automatically replied to review '{review_id}' with rating {rating_int}."
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
    - Review yang SUDAH punya balasan di Google tapi belum ada di DB lokal -> disinkronkan
      sebagai histori (tanpa kirim ulang reply).
    - Review yang BELUM punya balasan dan rating 3-5 (dan bukan pertanyaan) -> dibalas otomatis.
    - Review yang BELUM punya balasan dan rating 1-2 atau mengandung pertanyaan -> dilewati,
      menunggu balasan manual via dashboard Humas (akan masuk ke DB lewat endpoint /reviews/sync
      atau webhook, bukan lewat worker ini).
    """
    print("🤖 [ReviewBot] Worker otomatis telah aktif di latar belakang...")

    while True:
        try:
            print("🔄 [ReviewBot] Melakukan pengecekan review terbaru ke Google API...")
            reviews = await ReviewBotService.fetch_latest_reviews()
            loop = asyncio.get_running_loop()

            for r in reviews:
                review_id = r.get("reviewId")
                rating = r.get("starRating")
                existing_reply = r.get("reviewReply")
                comment = r.get("comment", "")
                rating_int = ReviewBotService.parse_rating(rating)

                # === Kasus 1: review sudah punya balasan di Google, sinkronkan ke DB jika belum ada ===
                if existing_reply:
                    if review_id in replied_reviews_cache:
                        continue

                    ai_analysis = await ReviewBotService.analyze_review_intent_and_sentiment(comment, rating_int)
                    await loop.run_in_executor(
                        None,
                        save_already_replied_review_sync,
                        r,
                        ai_analysis["keywords"],
                        ai_analysis["sentiment"]
                    )
                    replied_reviews_cache.add(review_id)
                    await asyncio.sleep(random.randint(1, 3))
                    continue

                # === Kasus 2: review belum punya balasan sama sekali ===
                if review_id in replied_reviews_cache:
                    continue

                print(f"📌 [ReviewBot] Menemukan review baru (ID: {review_id}) dengan Rating: {rating}")
                reviewer_name = r.get("reviewer", {}).get("displayName", "Pasien")

                if rating_int in [1, 2]:
                    # Rating rendah: jangan auto-reply, biarkan masuk antrean manual Humas.
                    print(f"⚠️ [ReviewBot] Review {review_id} rating rendah ({rating_int}). Dilewati, tunggu balasan manual via dashboard.")
                    await asyncio.sleep(random.randint(1, 3))
                    continue

                ai_analysis = await ReviewBotService.analyze_review_intent_and_sentiment(comment, rating_int)
                if ai_analysis["is_asking"]:
                    print(f"⚠️ [ReviewBot] Review {review_id} terdeteksi mengandung pertanyaan. Dilewati, tunggu balasan manual via dashboard.")
                    await asyncio.sleep(random.randint(1, 3))
                    continue

                db_session = SessionLocalMain()
                try:
                    bot_reply = await ReviewBotService.generate_reply_template(rating, reviewer_name, db_session)
                finally:
                    db_session.close()

                success = await ReviewBotService.send_reply_to_google(review_id, bot_reply)

                if success:
                    replied_reviews_cache.add(review_id)

                    await loop.run_in_executor(
                        None,
                        save_auto_replied_review_sync,
                        review_id,
                        reviewer_name,
                        rating,
                        comment,
                        bot_reply,
                        ai_analysis["keywords"],
                        ai_analysis["sentiment"]
                    )

                    db_session = SessionLocalMain()
                    try:
                        await PushNotificationService.trigger_review_notification(
                            reviewer_name=reviewer_name,
                            rating=rating_int,
                            comment=comment,
                            status="replied",
                            reply_text=bot_reply,
                            db=db_session
                        )
                    except Exception as push_err:
                        print(f"❌ [ReviewBot] Gagal mengirim push notification: {str(push_err)}")
                    finally:
                        db_session.close()

                    await asyncio.sleep(random.randint(3, 7))

        except Exception as e:
            print(f"❌ [ReviewBot] Terjadi kendala pada background worker: {str(e)}")

        await asyncio.sleep(300)