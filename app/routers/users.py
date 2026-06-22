# app/routers/users.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db_main
from app.core.security import global_admin_only, hash_password
from app.models.user import UserModel
from app.schemas.base import BaseResponse, ApiResponse
from app.schemas.users import UserResponse, GlobalCreateUserRequest, GlobalUpdateUserRequest
from app.services.logger_service import ActivityLogger

router = APIRouter(prefix="/api/manage/users", tags=["Global User Management"])

@router.post("", response_model=BaseResponse[UserResponse], status_code=201)
def global_create_user(
    payload: GlobalCreateUserRequest,
    db: Session = Depends(get_db_main),
    admin: UserModel = Depends(global_admin_only)
):
    """[Kasta 0 Only] Membuat user baru untuk aplikasi mana pun (0, 1, 2, 3)"""
    if db.query(UserModel).filter(UserModel.username == payload.username).first():
        return ApiResponse.error(message="Username sudah terdaftar.", code=400)
        
    if db.query(UserModel).filter(UserModel.email == payload.email).first():
        return ApiResponse.error(message="Email sudah terdaftar.", code=400)

    new_user = UserModel(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        password=hash_password(payload.password),
        role=payload.role.lower(),
        app_access=payload.app_access,
        phone=payload.phone,
        alamat=payload.alamat
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    ActivityLogger.log(
        db=db, username=admin.username, action="GLOBAL_USER_CREATE",
        description=f"Global Admin '{admin.username}' mendaftarkan user '{new_user.username}' ke app_access {new_user.app_access}."
    )
    return ApiResponse.success(data=UserResponse.model_validate(new_user), message="User berhasil dibuat.", code=201)

@router.get("", response_model=BaseResponse[List[UserResponse]])
def global_get_all_users(
    db: Session = Depends(get_db_main),
    admin: UserModel = Depends(global_admin_only)
):
    """[Kasta 0 Only] Menampilkan seluruh user dari ke-3 aplikasi tanpa terkecuali"""
    users = db.query(UserModel).order_by(UserModel.id.asc()).all()
    return ApiResponse.success(data=[UserResponse.model_validate(u) for u in users], message="Seluruh data user berhasil ditarik.", code=200)

@router.put("/{user_id}", response_model=BaseResponse[UserResponse])
def global_update_user(
    user_id: int,
    payload: GlobalUpdateUserRequest,
    db: Session = Depends(get_db_main),
    admin: UserModel = Depends(global_admin_only)
):
    """[Kasta 0 Only] Mengedit info user, memindah divisi aplikasi, atau menaikkan/menurunkan role dengan aman"""
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target_user:
        return ApiResponse.error(message="User tidak ditemukan.", code=404)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "role" and value:
            setattr(target_user, key, value.lower())
        elif key == "password" and value:
            setattr(target_user, key, hash_password(value))
        else:
            setattr(target_user, key, value)

    db.commit()
    db.refresh(target_user)

    ActivityLogger.log(
        db=db, username=admin.username, action="GLOBAL_USER_UPDATE",
        description=f"Global Admin '{admin.username}' memperbarui data/akses user ID {user_id}."
    )
    return ApiResponse.success(data=UserResponse.model_validate(target_user), message="Data user berhasil diperbarui.", code=200)
@router.delete("/{user_id}", response_model=BaseResponse[dict])
def global_delete_user(
    user_id: int,
    db: Session = Depends(get_db_main),
    admin: UserModel = Depends(global_admin_only)
):
    """[Kasta 0 Only] Menghapus akun staff dari database monolith secara permanen"""
    target_user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not target_user:
        return ApiResponse.error(message="User tidak ditemukan.", code=404)
        
    if target_user.id == admin.id:
        return ApiResponse.error(message="Anda tidak bisa menghapus akun Global Admin Anda sendiri!", code=400)

    username_deleted = target_user.username
    db.delete(target_user)
    db.commit()

    ActivityLogger.log(
        db=db, username=admin.username, action="GLOBAL_USER_DELETE",
        description=f"Global Admin '{admin.username}' MENGHAPUS PERMANEN akun '{username_deleted}'."
    )
    return ApiResponse.success(data={"deleted_id": user_id}, message=f"Akun {username_deleted} berhasil dihapus permanen.", code=200)