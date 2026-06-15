#app/models/target_model.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey 
from sqlalchemy.dialects.mysql import YEAR
from sqlalchemy.sql import func
from app.core.database import BaseMain

class TargetModel(BaseMain):
    __tablename__ = "targets" 
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tahun = Column(YEAR, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, nullable=False)
    type = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())