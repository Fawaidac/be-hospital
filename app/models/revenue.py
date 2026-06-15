# app/models/revenue.py
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.dialects.mysql import YEAR, TINYINT
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import BaseMain


class RevenueModel(BaseMain):
    __tablename__ = "revenues"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tahun = Column(YEAR, nullable=False)
    bulan = Column(TINYINT, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # RELASI: 1 Revenue punya banyak Details
    details = relationship("RevenueDetailModel", back_populates="revenue", cascade="all, delete-orphan")
