# app/models/review_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import BaseMain


class GoogleReviewModel(BaseMain):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    review_id = Column(String(255), unique=True, nullable=False, index=True)
    reviewer_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    reply_text = Column(Text, nullable=True)
    status = Column(String(50), default="pending") 
    created_at = Column(DateTime, server_default=func.now())

