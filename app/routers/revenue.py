# app/routers/revenue.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import get_current_user, super_admin_only
from app.models.user import UserModel
from app.schemas.base import ApiResponse
from app.schemas.revenue import RevenueStoreRequest
from app.services.revenue_service import RevenueService

router = APIRouter(prefix="/api/revenue", tags=["Revenue"])


@router.get("/")
def index(
    tahun: int = Query(..., description="Tahun wajib diisi"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        data = RevenueService.get_dashboard(db, tahun)
        return ApiResponse.success(data=data, message="Get data berhasil", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/")
def store(
    payload: RevenueStoreRequest,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)
):
    try:
        res = RevenueService.store_or_update(db, payload.dict())
        return ApiResponse.success(data=res, message="Data target dan realisasi berhasil disimpan", code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/years")
def years(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        data = RevenueService.get_year_list(db)
        return ApiResponse.success(data=data, message="Get list tahun berhasil", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/detail")
def show_by_year(
    tahun: int = Query(...),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        data = RevenueService.get_by_year(db, tahun)
        return ApiResponse.success(data=data, message="Get detail data tahun berhasil", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/destroy")
def destroy(
    tahun: int = Query(...),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        RevenueService.delete_by_year(db, tahun)
        return ApiResponse.success(data=None, message="Data laporan tahunan berhasil dihapus", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))