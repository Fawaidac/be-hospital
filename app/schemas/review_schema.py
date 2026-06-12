# app/schemas/review_schema.py
from pydantic import BaseModel
from typing import Optional, Generic, TypeVar, List
from datetime import datetime
from pydantic import Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Format response standar untuk semua endpoint."""
    status: str          # "success" | "error"
    code: int            # HTTP status code
    message: str         # Pesan deskriptif
    data: Optional[T] = None


class GoogleReviewWebhook(BaseModel):
    review_id: str
    reviewer_name: str
    rating: int = Field(..., ge=1, le=5)  
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: int
    review_id: str
    reviewer_name: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str]
    reply_text: Optional[str]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookData(BaseModel):
    """Data yang dikembalikan setelah webhook diproses."""
    review_id: str
    reviewer_name: str
    rating: int = Field(..., ge=1, le=5)
    bot_status: str       # "replied" | "failed"
    reply_text: str 