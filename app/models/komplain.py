# app/models/komplain.py
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Column, Integer, String, Text, DateTime
from app.core.database import BasePSC


class KomplainModel(BasePSC):
    __tablename__ = "data_komplain"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    nama = Column(String(255), nullable=True)
    nama_pelapor = Column(String(255), nullable=True)
    ruangan = Column(String(255), nullable=True)
    permasalahan = Column(Text, nullable=True)
    nomor_wa = Column(String(50), nullable=True)
    nomor_act = Column(String(50), nullable=True, index=True)
    tanggal = Column(DateTime, nullable=False, server_default=func.now())

    pde = relationship(
        "PDEModel",
        primaryjoin="KomplainModel.nomor_act == PDEModel.telp",
        foreign_keys=[nomor_act],
        uselist=False
    )
