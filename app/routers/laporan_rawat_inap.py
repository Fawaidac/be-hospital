from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db_main
from app.core.security import get_current_user, super_admin_only
from app.models.user import UserModel
from app.schemas.base import ApiResponse
from app.schemas.laporan_rawat_inap import (
    LaporanRawatInapBulkCreate,
    LaporanRawatInapListResponse,
    LaporanRawatInapUpdate,
    NDRGDRListResponse,
    SensusRanapLengkapResponse
)
from app.services.laporan_rawat_inap_service import LaporanRawatInapService
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api", tags=["Laporan Rawat Inap"])


@router.get("/indikator-dinkes-bbj")
def index(
    tahun: int = Query(..., description="Filter by year"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        result = LaporanRawatInapService.get_all(db, tahun)
        response = LaporanRawatInapListResponse.model_validate(result)
        return ApiResponse.success(data=response, message="Data laporan rawat inap berhasil didapatkan.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# @router.post("/laporan-rawat-inap", status_code=201)
# def store(
#     payload: LaporanRawatInapBulkCreate,
#     db: Session = Depends(get_db_main),
#     current_user: UserModel = Depends(super_admin_only)
# ):
#     try:
#         data = LaporanRawatInapService.create_bulk(db, payload)
#         ActivityLogger.log(
#             username=current_user.username,
#             action="RAWAT_INAP_CREATE",
#             description=f"User '{current_user.username}' created inpatient report for year {payload.tahun}, months {[i.bulan for i in payload.data]}."
#         )
#         return ApiResponse.success(data=data, message="Laporan rawat inap berhasil ditambahkan.", code=201)
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.put("/laporan-rawat-inap/{id}")
# def update(
#     id: int,
#     payload: LaporanRawatInapUpdate,
#     db: Session = Depends(get_db_main),
#     current_user: UserModel = Depends(super_admin_only)
# ):
#     try:
#         data = LaporanRawatInapService.update(db, id, payload)
#         ActivityLogger.log(
#             username=current_user.username,
#             action="RAWAT_INAP_UPDATE",
#             description=f"User '{current_user.username}' updated inpatient report ID {id}."
#         )
#         return ApiResponse.success(data=data, message="Laporan rawat inap berhasil diupdate.", code=200)
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


# @router.delete("/laporan-rawat-inap/{id}")
# def destroy(
#     id: int,
#     db: Session = Depends(get_db_main),
#     current_user: UserModel = Depends(super_admin_only)
# ):
#     try:
#         LaporanRawatInapService.delete(db, id)
#         ActivityLogger.log(
#             username=current_user.username,
#             action="RAWAT_INAP_DELETE",
#             description=f"User '{current_user.username}' deleted inpatient report ID {id}."
#         )
#         return ApiResponse.success(data=None, message="Laporan rawat inap berhasil dihapus.", code=200)
#     except HTTPException as he:
#         raise he
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

@router.get("/ndr-gdr")
def get_ndr_gdr_report(
    tahun: int = Query(..., description="Filter by year"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        result = LaporanRawatInapService.get_ndr_gdr(db, tahun)
        response = NDRGDRListResponse.model_validate(result)
        return ApiResponse.success(data=response, message="Data laporan NDR & GDR berhasil didapatkan.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Tambahkan SensusRanapLengkapResponse pada list import dari app.schemas.laporan_rawat_inap

@router.get("/kunjungan-total")
def get_sensus_ranap_lengkap(
    tahun: int = Query(..., description="Filter berdasarkan tahun"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        result = LaporanRawatInapService.get_sensus_lengkap(db, tahun)
        response = SensusRanapLengkapResponse.model_validate(result)
        return ApiResponse.success(data=response, message="Data grand total kunjungan sensus ranap lengkap didapatkan.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))