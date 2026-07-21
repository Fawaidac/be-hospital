from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.user import UserModel
from app.services.pelayanan import PelayananService 
from app.schemas.base import ApiResponse


router = APIRouter(prefix="/api", tags=["Pelayanan"])

@router.get("/kunjungan/bbj")
def read_laporan_terpadu(
    bulan: Optional[int] = Query(None, description="Filter Bulan (1-12)", ge=1, le=12),
    tahun: Optional[int] = Query(None, description="Filter Tahun"),
    type: Optional[str] = Query(None, description="Filter Type (BARBER_JOHNSON / BARBER_JOHNSON_PER_KELAS)"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Endpoint untuk mengambil satu laporan utuh berisi data detail ruangan 
    dan data rekap total kelompok pelayanannya sekaligus.
    """
    try:
        # TAMBAHKAN type=type DI SINI AGAR NILAI DARI SWAGGER DIOPER KE SERVICE
        data_detail = PelayananService.get_laporan_detail(db=db, bulan=bulan, tahun=tahun, type=type)
        
        data_rekap = PelayananService.get_laporan_rekap(db=db, bulan=bulan, tahun=tahun, type=type)
        
        return ApiResponse.success(
            data={
                "detail": data_detail,
                "rekap": data_rekap
            },
            message="Laporan terpadu berhasil diambil.",
            code=200
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))