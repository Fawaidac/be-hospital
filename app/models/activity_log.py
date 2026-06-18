from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import BaseMain

class ActivityLogModel(BaseMain):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False, default="System/Bot", index=True)
    action = Column(String(100), nullable=False) 
    description = Column(Text, nullable=False)    
    created_at = Column(DateTime, server_default=func.now())