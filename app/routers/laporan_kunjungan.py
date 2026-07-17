from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.base import ApiResponse
from app.schemas.laporan_kunjungan import GrandTotalKunjunganResponse
from app.services.laporan_kunjungan_service import LaporanKunjunganService

router = APIRouter(prefix="/api", tags=["Laporan Kunjungan"])

@router.get("/laporan-all-kunjungan")
def get_grand_total_report(
    tahun: int = Query(..., description="Filter berdasarkan tahun"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        result = LaporanKunjunganService.get_grand_total_kunjungan(db, tahun)
        response = GrandTotalKunjunganResponse.model_validate(result)
        return ApiResponse.success(data=response, message="Data grand total kunjungan seluruh RS berhasil didapatkan.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))