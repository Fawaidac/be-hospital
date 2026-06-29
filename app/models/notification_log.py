# app/models/notification_log.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.core.database import BaseMain


class NotificationLogModel(BaseMain):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(50), nullable=True)          
    reviewer_name = Column(String(255), nullable=True)
    rating = Column(Integer, nullable=True)
    url = Column(String(255), nullable=True, default="/dashboard/reviews")
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
