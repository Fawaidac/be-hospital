# app/schemas/notification.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class PushSubscriptionResponse(BaseModel):
    id: int
    endpoint: str
    user_id: Optional[int]

    class Config:
        from_attributes = True


class UnsubscribeRequest(BaseModel):
    endpoint: str


class NotificationLogResponse(BaseModel):
    id: int
    title: str
    body: str
    status: Optional[str]
    reviewer_name: Optional[str]
    rating: Optional[int]
    url: Optional[str]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


