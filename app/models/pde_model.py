# app/models/pde_model.py
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, Text
from app.core.database import BasePSC

class PDEModel(BasePSC):
    __tablename__ = "data_pde"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nama = Column(String(255), nullable=False)
    telp = Column(String(20), nullable=True)
    alamat = Column(Text, nullable=True)