# app/models/user.py
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import BaseMain


class UserModel(BaseMain):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    alamat = Column(Text, nullable=True)
    role = Column(String(50), nullable=False)
    pin = Column(String(225), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
