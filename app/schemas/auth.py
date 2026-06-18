# app/schemas/auth.py
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class LoginRequest(BaseModel):
    """Schema input untuk request login."""
    username: str
    password: str


class LoginData(BaseModel):
    """Schema data untuk output token setelah login sukses."""
    token: str


class UserData(BaseModel):
    """Schema data profil user yang sedang login."""
    id: int
    name: str
    username: str
    email: str
    role: str
    pin: str
    phone: Optional[str] = None
    alamat: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("pin", mode="before")
    @classmethod
    def mask_pin(cls, value):
        return "****" if value else ""


class CheckPinRequest(BaseModel):
    """Schema input untuk validasi PIN 6 digit."""
    pin: str
