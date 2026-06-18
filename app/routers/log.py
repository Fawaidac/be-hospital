# app/routers/log.py
from typing import List  #  BENAR: Diambil dari typing, bukan ast
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.activity_log import ActivityLogModel
from app.models.user import UserModel
from app.schemas.base import BaseResponse, ApiResponse

router = APIRouter(prefix="/api", tags=["Logs Activity"])

@router.get("/logs", response_model=BaseResponse[List[dict]])
def get_activity_logs(
    limit: int = 100,  
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint untuk menyuplai data fitur Log Aktivitas di Frontend Dashboard"""
    logs = db.query(ActivityLogModel).order_by(ActivityLogModel.created_at.desc()).limit(limit).all()
    
    data_list = [
        {
            "id": l.id,
            "username": l.username,
            "action": l.action,
            "description": l.description,
            "created_at": l.created_at
        }
        for l in logs
    ]
    
    return ApiResponse.success(
        data=data_list,
        message="Activity logs retrieved successfully.",
        code=200
    )
