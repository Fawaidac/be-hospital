# app/schemas/notification.py
from pydantic import BaseModel
from typing import Optional


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

