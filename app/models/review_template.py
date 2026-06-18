from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import BaseMain

class ReviewTemplateModel(BaseMain):
    __tablename__ = "review_templates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    rating = Column(Integer, unique=True, nullable=False, index=True)
    template_text = Column(Text, nullable=False) 
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())