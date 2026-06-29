# app/services/push_notification_service.py
import json
import os
import logging
import asyncio
from sqlalchemy.orm import Session
from pywebpush import webpush, WebPushException

from app.core.config import settings
from app.models.push_subscription import PushSubscriptionModel
from app.models.notification_log import NotificationLogModel

logger = logging.getLogger("PushNotificationService")


class PushNotificationService:

    @staticmethod
    def send_push_sync(endpoint: str, p256dh: str, auth: str, payload_data: dict) -> bool:
        """
        Fungsi sinkron untuk mengirimkan push notification menggunakan pywebpush.
        Mengembalikan True jika sukses/diterima, False jika subscription tidak valid (expired/410/404).
        """
        private_key = settings.VAPID_PRIVATE_KEY
        if private_key and not os.path.isabs(private_key) and not private_key.startswith("-----"):
            from app.core.config import BASE_DIR
            candidate = BASE_DIR / private_key
            if candidate.exists():
                private_key = str(candidate)

        subscription_info = {
            "endpoint": endpoint,
            "keys": {
                "p256dh": p256dh,
                "auth": auth
            }
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps(payload_data),
                vapid_private_key=private_key,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"
                }
            )
            return True
        except WebPushException as ex:
            status_code = ex.response.status_code if ex.response is not None else 0
            logger.error(f"Error sending web push: status {status_code}, error {repr(ex)}")
            # 404 and 410 indicate the subscription has expired or is unsubscribed
            if status_code in [404, 410]:
                return False
            # Keep other subscriptions on transient network errors
            return True

    @staticmethod
    async def broadcast_notification(payload_data: dict, db: Session):
        """
        Mengirimkan notifikasi ke semua subscription yang terdaftar di database.
        """
        subscriptions = db.query(PushSubscriptionModel).all()
        if not subscriptions:
            return

        loop = asyncio.get_running_loop()
        to_delete = []

        for sub in subscriptions:
            # Jalankan di executor agar tidak memblokir event loop utama
            success = await loop.run_in_executor(
                None,
                PushNotificationService.send_push_sync,
                sub.endpoint,
                sub.p256dh,
                sub.auth,
                payload_data
            )
            if not success:
                to_delete.append(sub.id)

        if to_delete:
            try:
                db.query(PushSubscriptionModel).filter(PushSubscriptionModel.id.in_(to_delete)).delete(synchronize_session=False)
                db.commit()
                logger.info(f"Berhasil menghapus {len(to_delete)} push subscription yang kedaluwarsa.")
            except Exception as err:
                db.rollback()
                logger.error(f"Gagal menghapus subscription kedaluwarsa: {str(err)}")

    @staticmethod
    def save_notification_log(
        db: Session,
        title: str,
        body: str,
        status: str,
        reviewer_name: str,
        rating: int,
        url: str = "/dashboard/reviews"
    ):
        """
        Menyimpan log notifikasi ke database agar bisa diambil via endpoint GET.
        """
        try:
            log_entry = NotificationLogModel(
                title=title,
                body=body,
                status=status,
                reviewer_name=reviewer_name,
                rating=rating,
                url=url,
                is_read=False
            )
            db.add(log_entry)
            db.commit()
        except Exception as err:
            db.rollback()
            logger.error(f"Gagal menyimpan log notifikasi: {str(err)}")

    @staticmethod
    async def trigger_review_notification(
        reviewer_name: str,
        rating: int,
        comment: str,
        status: str,
        reply_text: str = None,
        db: Session = None
    ):
        """
        Membuat payload notifikasi ulasan baru, menyimpan log ke DB,
        lalu membroadcastnya ke semua subscriber.
        """
        if not db:
            return

        clean_comment = comment if comment else "(Tidak ada komentar)"
        short_comment = clean_comment if len(clean_comment) <= 60 else f"{clean_comment[:60]}..."

        if status == "pending":
            title = "Ulasan Baru Perlu Tindakan! ⚠️"
            body = f"Ulasan bintang {rating} dari {reviewer_name} masuk antrean pending.\nKomentar: \"{short_comment}\""
        elif status == "replied" and reply_text:
            title = "Ulasan Baru Dibalas Otomatis! 🤖"
            short_reply = reply_text if len(reply_text) <= 60 else f"{reply_text[:60]}..."
            body = f"Bot membalas ulasan bintang {rating} dari {reviewer_name}.\nBalasan: \"{short_reply}\""
        else:
            title = "Ulasan Baru Diterima!"
            body = f"Ulasan bintang {rating} dari {reviewer_name}.\nKomentar: \"{short_comment}\""

        # Simpan log notifikasi ke database
        PushNotificationService.save_notification_log(
            db=db,
            title=title,
            body=body,
            status=status,
            reviewer_name=reviewer_name,
            rating=rating
        )

        payload = {
            "notification": {
                "title": title,
                "body": body,
                "icon": "/static/logo.png",
                "badge": "/static/badge.png",
                "data": {
                    "url": "/dashboard/reviews",
                    "status": status
                }
            }
        }

        await PushNotificationService.broadcast_notification(payload, db)

