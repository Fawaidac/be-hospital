from sqlalchemy import Column, Integer, BigInteger, Numeric, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import BaseMain

class RevenueDetailModel(BaseMain):
    __tablename__ = "revenue_details"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    revenue_id = Column(Integer, ForeignKey("revenues.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    amount = Column(BigInteger, server_default="0", nullable=False)
    percentage = Column(Numeric(precision=5, scale=2), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())