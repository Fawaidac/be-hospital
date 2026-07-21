from sqlalchemy.orm import Session
from typing import Optional
from app.models.pelayanan import VStatistikRawatInap, VRekapPelayanan

class PelayananService:
    @staticmethod
    def get_laporan_detail(db: Session, bulan: Optional[int] = None, tahun: Optional[int] = None, type: Optional[str] = None):
        """Mengambil data detail ruangan (v_statistik_rawat_inap) dengan filter periode"""
        query = db.query(VStatistikRawatInap)
        
        if bulan is not None:
            query = query.filter(VStatistikRawatInap.bulan == bulan)
        if tahun is not None:
            query = query.filter(VStatistikRawatInap.tahun == tahun)
        if type is not None:
            query = query.filter(VStatistikRawatInap.type == type)
        return query.all()

    @staticmethod
    def get_laporan_rekap(db: Session, bulan: Optional[int] = None, tahun: Optional[int] = None, type: Optional[str] = None):
        """Mengambil data rekap kelompok pelayanan (v_rekap_pelayanan) dengan filter periode"""
        query = db.query(VRekapPelayanan)
        
        if bulan is not None:
            query = query.filter(VRekapPelayanan.bulan == bulan)
        if tahun is not None:
            query = query.filter(VRekapPelayanan.tahun == tahun)
        if type is not None:
            query = query.filter(VRekapPelayanan.type == type)
            
        return query.all()