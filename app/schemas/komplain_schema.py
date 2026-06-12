# app/schemas/komplain_schema.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PdeResponse(BaseModel):
    id: Optional[int] = None
    nama: str
    alamat: Optional[str] = None
    telp: Optional[str] = None

    class Config:
        from_attributes = True

class KomplainResponse(BaseModel):
    id: int
    nama: Optional[str] = None
    nama_pelapor: Optional[str] = None
    ruangan: Optional[str] = None
    permasalahan: Optional[str] = None
    nomor_wa: Optional[str] = None
    nomor_act: Optional[str] = None
    tanggal: datetime
    status: str
    pde: Optional[PdeResponse] = None

    class Config:
        from_attributes = True

class PaginatedKomplain(BaseModel):
    current_page: int
    data: List[KomplainResponse]
    total: int

class PdePerformanceItem(BaseModel):
    id: Optional[int] = None
    nama: str
    alamat: Optional[str] = None
    telp: Optional[str] = None
    total: int

class DashboardKomplainResponse(BaseModel):
    ticket_open: int
    ticket_done: int
    simrs_masuk: int
    simrs_done: int
    maintenance_masuk: int
    maintenance_done: int
    pde_performance: List[PdePerformanceItem]