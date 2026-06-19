# app/schemas/review.py
from pydantic import BaseModel, Field
from typing import Optional, TypeVar, List
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
    sentiment: str 
    created_at: datetime
    keywords: List[str] = []

    model_config = {"from_attributes": True}

class WebhookData(BaseModel):
    review_id: str
    reviewer_name: str
    rating: int = Field(..., ge=1, le=5)
    bot_status: str      
    reply_text: str

class UpdateTemplateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    template_text: str

class DashboardStatsResponse(BaseModel):
    total_reviews: int
    rating_average: float
    positive_vibes_percentage: float
    response_rate_percentage: float

class SentimentDetail(BaseModel):
    count: int
    percentage: float

class KeywordTrendDetail(BaseModel):
    keyword: str
    count: int

class SentimentAnalysisResponse(BaseModel):
    summary_status: str         
    overall_positive_percentage: float  
    positive: SentimentDetail    
    neutral: SentimentDetail     
    negative: SentimentDetail    
    top_keywords: List[KeywordTrendDetail] 
