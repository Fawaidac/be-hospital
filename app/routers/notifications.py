# app/routers/notifications.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.user import UserModel
from app.models.push_subscription import PushSubscriptionModel
from app.schemas.notification import PushSubscriptionCreate, PushSubscriptionResponse, UnsubscribeRequest
from app.schemas.base import BaseResponse, ApiResponse
from app.core.config import settings
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api/notifications", tags=["Notification"])


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
    # Cari apakah subscription dengan endpoint yang sama sudah terdaftar
    existing = db.query(PushSubscriptionModel).filter(PushSubscriptionModel.endpoint == payload.endpoint).first()

    if existing:
        # Update data yang ada
        existing.user_id = current_user.id
        existing.p256dh = payload.keys.p256dh
        existing.auth = payload.keys.auth
        db.commit()
        db.refresh(existing)
        subscription = existing
        msg = "Subscription push notification berhasil diperbarui."
    else:
        # Tambah baru
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
