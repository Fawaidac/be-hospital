# app/schemas/users.py
from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional, List

class UserResponse(BaseModel):
    id: int
    name: str
    username: str
    email: str
    role: str
    app_access: int
    phone: Optional[str] = None
    alamat: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class GlobalCreateUserRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = Field(..., description="superadmin, admin, atau user")
    app_access: int = Field(..., ge=0, le=3, description="0: global, 1: soetic, 2: soebis, 3: soeview")
    phone: Optional[str] = None
    alamat: Optional[str] = None

class GlobalUpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    app_access: Optional[int] = Field(None, ge=0, le=3)
    phone: Optional[str] = None
    alamat: Optional[str] = None