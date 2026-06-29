# app/routers/notifications.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.user import UserModel
from app.models.push_subscription import PushSubscriptionModel
from app.models.notification_log import NotificationLogModel
from app.schemas.notification import (
    PushSubscriptionCreate, PushSubscriptionResponse,
    UnsubscribeRequest, NotificationLogResponse
)
from app.schemas.base import BaseResponse, ApiResponse
from app.core.config import settings
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api/notifications", tags=["Notification"])


# ─────────────────────────────────────────────
#  VAPID & Subscription
# ─────────────────────────────────────────────

@router.get("/vapid-public-key", response_model=BaseResponse[dict])
def get_vapid_public_key():
    """
    Mengambil VAPID Public Key untuk keperluan registrasi Service Worker di frontend.
    """
    pub_key = settings.VAPID_PUBLIC_KEY
    if not pub_key:
        return ApiResponse.error(message="VAPID Public Key belum dikonfigurasi di server.", code=500)
    return ApiResponse.success(data={"public_key": pub_key}, message="VAPID Public Key berhasil diambil.")


@router.post("/subscribe", response_model=BaseResponse[PushSubscriptionResponse])
def subscribe_device(
    payload: PushSubscriptionCreate,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Mendaftarkan subscription push notification untuk user yang sedang aktif.
    """
    existing = db.query(PushSubscriptionModel).filter(PushSubscriptionModel.endpoint == payload.endpoint).first()

    if existing:
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        db.commit()
        db.refresh(existing)
        subscription = existing
        msg = "Subscription push notification berhasil diperbarui."
    else:
        new_sub = PushSubscriptionModel(
            user_id=current_user.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth
        )
        db.add(new_sub)
        db.commit()
        db.refresh(new_sub)
        subscription = new_sub
        msg = "Subscription push notification baru berhasil didaftarkan."

    ActivityLogger.log(
        username=current_user.username,
        action="PUSH_SUBSCRIBE",
        description=f"User '{current_user.username}' subscribed a device to push notifications."
    )

    return ApiResponse.success(data=subscription, message=msg, code=201)


@router.post("/unsubscribe", response_model=BaseResponse[dict])
def unsubscribe_device(
    payload: UnsubscribeRequest,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Menghapus subscription push notification.
    """
    sub = db.query(PushSubscriptionModel).filter(
        PushSubscriptionModel.endpoint == payload.endpoint,
        PushSubscriptionModel.user_id == current_user.id
    ).first()

    if not sub:
        return ApiResponse.error(message="Subscription tidak ditemukan atau bukan milik Anda.", code=404)

    db.delete(sub)
    db.commit()

    ActivityLogger.log(
        username=current_user.username,
        action="PUSH_UNSUBSCRIBE",
        description=f"User '{current_user.username}' unsubscribed a device from push notifications."
    )

    return ApiResponse.success(message="Subscription push notification berhasil dihapus.")


# ─────────────────────────────────────────────
#  Notification History (Log)
# ─────────────────────────────────────────────

@router.get("", response_model=BaseResponse[List[NotificationLogResponse]])
def get_notifications(
    limit: Optional[int] = Query(50, ge=1, le=200, description="Jumlah notifikasi yang diambil (default 50)"),
    unread_only: Optional[bool] = Query(False, description="Jika true, hanya tampilkan notifikasi yang belum dibaca"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Mengambil riwayat notifikasi review yang masuk, diurutkan dari terbaru.
    Mendukung filter hanya notifikasi belum dibaca dan pembatasan jumlah data.
    """
    query = db.query(NotificationLogModel)

    if unread_only:
        query = query.filter(NotificationLogModel.is_read == False)

    notifications = query.order_by(NotificationLogModel.created_at.desc()).limit(limit).all()

    return ApiResponse.success(
        data=notifications,
        message=f"Berhasil mengambil {len(notifications)} notifikasi."
    )


@router.get("/unread-count", response_model=BaseResponse[dict])
def get_unread_count(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Mengambil jumlah notifikasi yang belum dibaca.
    Berguna untuk menampilkan badge/angka di ikon notifikasi dashboard.
    """
    count = db.query(NotificationLogModel).filter(NotificationLogModel.is_read == False).count()
    return ApiResponse.success(data={"unread_count": count}, message="Jumlah notifikasi belum dibaca berhasil diambil.")


@router.patch("/{notification_id}/read", response_model=BaseResponse[dict])
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Menandai satu notifikasi sebagai sudah dibaca berdasarkan ID.
    """
    notif = db.query(NotificationLogModel).filter(NotificationLogModel.id == notification_id).first()
    if not notif:
        return ApiResponse.error(message="Notifikasi tidak ditemukan.", code=404)

    notif.is_read = True
    db.commit()

    return ApiResponse.success(data={"id": notification_id, "is_read": True}, message="Notifikasi ditandai sebagai sudah dibaca.")


@router.patch("/read-all", response_model=BaseResponse[dict])
def mark_all_notifications_as_read(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Menandai semua notifikasi yang belum dibaca sebagai sudah dibaca sekaligus.
    """
    updated = db.query(NotificationLogModel).filter(NotificationLogModel.is_read == False).update(
        {"is_read": True}, synchronize_session=False
    )
    db.commit()

    return ApiResponse.success(
        data={"updated_count": updated},
        message=f"{updated} notifikasi berhasil ditandai sebagai sudah dibaca."
    )


