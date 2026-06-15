#app/models/category_model.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from app.core.database import BaseMain

class CategoryModel(BaseMain):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    code = Column(String(225), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())