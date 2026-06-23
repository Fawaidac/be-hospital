# app/routers/log.py
import os
import json
from typing import List
from collections import deque
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import get_current_user
from app.models.user import UserModel
from app.schemas.base import BaseResponse, ApiResponse

router = APIRouter(prefix="/api", tags=["Logs Activity"])
@router.get("/logs", response_model=BaseResponse[List[dict]])
def get_activity_logs(
    limit: int = 100,  
    current_user: UserModel = Depends(get_current_user)
):
    """Endpoint untuk menyuplai data fitur Log Aktivitas di Frontend Dashboard"""
    log_file_path = os.path.join("logs", "activity_logs.txt")
    data_list = []
    
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                last_lines = deque(f, maxlen=limit)
                
                for line in reversed(last_lines):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log_data = json.loads(line)
                        data_list.append({
                            "id": log_data.get("id"), 
                            "username": log_data.get("username", "System/Bot"),
                            "action": log_data.get("action", ""),
                            "description": log_data.get("description", ""),
                            "created_at": log_data.get("created_at", "")
                        })
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"❌ Gagal membaca file log aktivitas: {str(e)}")
            
    return ApiResponse.success(
        data=data_list,
        message="Activity logs retrieved successfully.",
        code=200
    )