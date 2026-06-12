from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db_main
from app.schemas.revenue_schema import RevenueStoreRequest
from app.services.revenue_service import RevenueService
from app.models import UserModel

from app.core.security import get_current_user, super_admin_only

router = APIRouter(prefix="/api/revenue", tags=["Revenue"])

@router.get("/")
def index(
    tahun: int = Query(..., description="Tahun wajib diisi"), 
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user) 
):
    try:
        data = RevenueService.get_dashboard(db, tahun)
        return {"status": "success", "message": "Get data berhasil", "data": data}
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
        return {"status": "success", "message": "Data target dan realisasi berhasil disimpan", "data": res}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/years")
def years(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only) # 🔒 Hanya Super Admin
):
    try:
        data = RevenueService.get_year_list(db)
        return {"status": "success", "message": "Get list tahun berhasil", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/detail")
def show_by_year(
    tahun: int = Query(...), 
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only) # 🔒 Hanya Super Admin
):
    try:
        data = RevenueService.get_by_year(db, tahun)
        return {"status": "success", "message": "Get detail data tahun berhasil", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/destroy")
def destroy(
    tahun: int = Query(...), 
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only) # 🔒 Hanya Super Admin
):
    try:
        RevenueService.delete_by_year(db, tahun)
        return {"status": "success", "message": "Data laporan tahunan berhasil dihapus", "data": None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))