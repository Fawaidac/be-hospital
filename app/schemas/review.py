# app/schemas/review.py
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, List
from datetime import datetime

T = TypeVar("T")


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
    bot_status: str      
    reply_text: str
