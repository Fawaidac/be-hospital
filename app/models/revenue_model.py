from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.mysql import YEAR, TINYINT 
from sqlalchemy.sql import func
from app.core.database import BaseMain

class RevenueModel(BaseMain):
    __tablename__ = "revenues"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tahun = Column(YEAR, nullable=False)
    bulan = Column(TINYINT, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())