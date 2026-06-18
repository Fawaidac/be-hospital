# app/routers/komplain.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db_psc
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.base import BaseResponse, ApiResponse
from app.schemas.komplain import PaginatedKomplain, DashboardKomplainResponse, PdeResponse
from app.services.komplain_service import KomplainService

router = APIRouter(prefix="/api", tags=["Data Komplain"])


@router.get(
    "/komplain",
    responses={200: {"model": BaseResponse[PaginatedKomplain]}},
    summary="Get List Data Komplain (Paginated)"
)
def get_komplain(
    search: Optional[str] = Query(None),
    kategori: Optional[str] = Query(None),
    is_done: Optional[bool] = Query(None),
    recent: Optional[bool] = Query(None),
    nomor_act: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db_psc),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        data = KomplainService.get_all(
            db=db,
            search=search,
            kategori=kategori,
            is_done=is_done,
            recent=recent,
            nomor_act=nomor_act,
            page=page
        )
        return ApiResponse.success(data=data, message="Complaint data retrieved successfully.", code=200)
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500)


@router.get(
    "/komplain/dashboard",
    responses={200: {"model": BaseResponse[DashboardKomplainResponse]}},
    summary="Get Counter Statistik Dashboard"
)
def get_komplain_dashboard(
    db: Session = Depends(get_db_psc),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        data = KomplainService.get_dashboard_count(db=db)
        return ApiResponse.success(data=data, message="Dashboard data retrieved successfully.", code=200)
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500)


@router.get(
    "/pde",
    responses={200: {"model": BaseResponse[list[PdeResponse]]}},
    summary="Get Distinct Team PDE Data"
)
def get_pde_teams(
    db: Session = Depends(get_db_psc),
    current_user: UserModel = Depends(get_current_user)
):
    try:
        data = KomplainService.get_data_team_pde(db=db)
        return ApiResponse.success(data=data, message="PDE team data retrieved successfully.", code=200)
    except Exception as e:
        return ApiResponse.error(message=str(e), code=500)
