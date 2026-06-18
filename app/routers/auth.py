# app/routers/auth.py
import hashlib
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db_main
from app.core.security import super_admin_only, verify_password, create_access_token, get_current_user
from app.models.user import UserModel
from app.schemas.base import BaseResponse, ApiResponse
from app.schemas.auth import CheckPinRequest, LoginRequest, LoginData, UserData
from app.services.auth_service import AuthService
from app.services.logger_service import ActivityLogger

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
        ActivityLogger.log(
            db=db,
            username=payload.username,
            action="LOGIN_FAILED",
            description=f"Failed login attempt for username '{payload.username}'."
        )
        return ApiResponse.error(
            message="Invalid username or password.",
            code=status.HTTP_401_UNAUTHORIZED
        )

    access_token = create_access_token(data={"sub": user.username})
    ActivityLogger.log(
        db=db,
        username=user.username,
        action="LOGIN_SUCCESS",
        description=f"User '{user.username}' logged in successfully."
    )

    return ApiResponse.success(
        data={"token": access_token},
        message="Login successful.",
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
    db: Session = Depends(get_db_main),
    current_user: UserModel = Depends(super_admin_only)
):
    """
    Endpoint untuk mencocokkan input PIN 6 digit (hanya Superadmin).
    Menggunakan hash SHA-256 untuk verifikasi.
    """
    is_valid, error_message = AuthService.verify_pin(current_user, payload.pin)

    if not is_valid:
        code = status.HTTP_400_BAD_REQUEST if "does not have a PIN" in error_message else status.HTTP_403_FORBIDDEN
        ActivityLogger.log(
            db=db,
            username=current_user.username,
            action="PIN_CHECK_FAILED",
            description=f"User '{current_user.username}' failed PIN verification."
        )
        return ApiResponse.error(message=error_message, code=code)

    ActivityLogger.log(
        db=db,
        username=current_user.username,
        action="PIN_CHECK_SUCCESS",
        description=f"User '{current_user.username}' verified their PIN successfully."
    )

    return ApiResponse.success(
        data=True,
        message="PIN is valid.",
        code=status.HTTP_200_OK
    )
