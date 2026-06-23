# app/routers/revenue.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import get_current_user, super_admin_only
from app.models.user import UserModel
from app.schemas.base import ApiResponse
from app.schemas.revenue import RevenueStoreRequest
from app.services.revenue_service import RevenueService
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api", tags=["Revenue"])


@router.get("/revenue")
def index(
    tahun: int = Query(..., description="Year is required"),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        data = RevenueService.get_dashboard(db, tahun)
        return ApiResponse.success(data=data, message="Data retrieved successfully.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/revenue")
def store(
    payload: RevenueStoreRequest,
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)
):
    try:
        res = RevenueService.store_or_update(db, payload.dict())
        ActivityLogger.log(
            username=current_user.username,
            action="REVENUE_SAVE",
            description=f"User '{current_user.username}' saved target and realization data for year {payload.tahun}."
        )
        return ApiResponse.success(data=res, message="Target and realization data saved successfully.", code=200)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/revenue/years")
def years(
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        data = RevenueService.get_year_list(db)
        return ApiResponse.success(data=data, message="Year list retrieved successfully.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/revenue/detail")
def show_by_year(
    tahun: int = Query(...),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        data = RevenueService.get_by_year(db, tahun)
        return ApiResponse.success(data=data, message="Year detail data retrieved successfully.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/revenue/destroy")
def destroy(
    tahun: int = Query(...),
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)  
):
    try:
        RevenueService.delete_by_year(db, tahun)
        ActivityLogger.log(
            username=current_user.username,
            action="REVENUE_DELETE",
            description=f"User '{current_user.username}' deleted annual report data for year {tahun}."
        )
        return ApiResponse.success(data=None, message="Annual report data deleted successfully.", code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
