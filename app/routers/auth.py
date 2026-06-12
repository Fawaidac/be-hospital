# app/routers/auth.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import hashlib
from app.core.database import get_db_main
from app.core.security import super_admin_only, verify_password, create_access_token, get_current_user
from app.models import UserModel
from app.schemas.base_schema import BaseResponse, ApiResponse
from app.schemas.auth_schema import CheckPinRequest, LoginRequest, LoginData, UserData

router = APIRouter(prefix="/api", tags=["Auth"])


@router.post(
    "/login",
    responses={200: {"model": BaseResponse[LoginData]}},
    summary="User login to retrieve access token",
)
async def login(payload: LoginRequest, db: Session = Depends(get_db_main)):
    """
    Endpoint untuk autentikasi user.
    """
    user = db.query(UserModel).filter(UserModel.username == payload.username).first()
    
    if not user or not verify_password(payload.password, user.password):
        return ApiResponse.error(
            message="Username atau password salah.",
            code=status.HTTP_401_UNAUTHORIZED
        )

    access_token = create_access_token(data={"sub": user.username})
    
    data_token = {"token": access_token}

    # 4. Kembalikan dengan ApiResponse.success
    return ApiResponse.success(
        data=data_token,
        message="Login berhasil.",
        code=status.HTTP_200_OK
    )


@router.get(
    "/me",
    responses={200: {"model": BaseResponse[UserData]}},
    summary="Get current logged-in user profile",
)
def get_me(current_user: UserModel = Depends(get_current_user)):
    """
    Endpoint untuk mengambil profil user yang sedang login.
    """
    
    user_data = UserData.model_validate(current_user)
    
    return ApiResponse.success(
        data=user_data,
        message="User profile retrieved successfully.",
        code=status.HTTP_200_OK
    )

@router.post(
    "/check-pin",
    responses={200: {"model": BaseResponse[bool]}},
    summary="Validasi PIN User (Khusus Superadmin)",
)
async def check_pin(
    payload: CheckPinRequest, 
    current_user: UserModel = Depends(super_admin_only)
):
    """
    Endpoint untuk mencocokkan input PIN 6 digit (Gaya Laravel Service/Controller).
    Mengecek kecocokan menggunakan arsitektur hash SHA-256.
    """
    if not current_user.pin:
        return ApiResponse.error(
            message="User tidak memiliki PIN.",
            code=status.HTTP_400_BAD_REQUEST
        )

    input_pin_hash = hashlib.sha256(payload.pin.encode("utf-8")).hexdigest()

    if input_pin_hash != current_user.pin:
        return ApiResponse.error(
            message="PIN salah.",
            code=status.HTTP_403_FORBIDDEN
        )

    return ApiResponse.success(
        data=True,
        message="PIN valid.",
        code=status.HTTP_200_OK
    )