# app/models/review.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import BaseMain

from sqlalchemy.orm import relationship 

class GoogleReviewModel(BaseMain):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id = Column(String(255), unique=True, nullable=False, index=True)
    reviewer_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    reply_text = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    sentiment = Column(String(20), default="NEUTRAL")
    created_at = Column(DateTime, server_default=func.now())
    replied_at = Column(DateTime, nullable=True)

    keywords_rel = relationship("ReviewKeywordModel", cascade="all, delete-orphan", lazy="joined")

class ReviewKeywordModel(BaseMain):
    __tablename__ = "review_keywords"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id = Column(String(255), ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(50), nullable=False, index=True)