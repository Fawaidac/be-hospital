#app/core/security.py
import hashlib
import jwt
import re
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status, Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db_main
from app.models import UserModel

class AuthException(Exception):
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code

class CustomHTTPBearer(HTTPBearer):
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        authorization: str = request.headers.get("Authorization")
        
        if not authorization:
            raise AuthException(message="Unauthorized, No Token Provided", status_code=401)
            
        try:
            return await super().__call__(request)
        except Exception:
            raise AuthException(message="Unauthorized, Invalid Token Format", status_code=401)

security = CustomHTTPBearer()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
SHA256_HEX_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


def is_legacy_sha256_hash(hashed_value: str) -> bool:
    """Detect legacy MySQL SHA2(value, 256)-style hashes."""
    return bool(hashed_value and SHA256_HEX_PATTERN.fullmatch(hashed_value))


def needs_hash_upgrade(hashed_value: str) -> bool:
    return is_legacy_sha256_hash(hashed_value)


def verify_legacy_sha256(plain_value: str, hashed_value: str) -> bool:
    try:
        input_hash = hashlib.sha256(plain_value.encode("utf-8")).hexdigest()
        return input_hash == hashed_value
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Hash a password/PIN using Argon2 for new and upgraded credentials."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify Argon2 hashes while keeping legacy SHA-256 hashes compatible."""
    if not hashed_password:
        return False

    if is_legacy_sha256_hash(hashed_password):
        return verify_legacy_sha256(plain_password, hashed_password)

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Membuat JWT Access Token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_main)
) -> UserModel:
    """Dependency untuk memvalidasi token JWT."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise AuthException(message="Unauthorized, Invalid Token", status_code=401)
            
    except jwt.ExpiredSignatureError:
        raise AuthException(message="Unauthorized, Invalid Token", status_code=401)
        
    except jwt.PyJWTError:
        raise AuthException(message="Unauthorized, Invalid Token", status_code=401)
        
    user = db.query(UserModel).filter(UserModel.username == username).first()
    if user is None:
        raise AuthException(message="Unauthorized, User Not Found", status_code=401)
        
    return user


def super_admin_only(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """
    Middleware Dependency untuk membatasi hak akses hanya untuk role superadmin dan pde.
    """
    if current_user.role not in ["superadmin", "pde"]:
        raise AuthException(
            message="Forbidden, Super Admin Only", 
            status_code=status.HTTP_403_FORBIDDEN
        )
        
    return current_user

def global_admin_only(current_user: UserModel = Depends(get_current_user)):
    """Mengecek apakah user yang login memiliki kasta tertinggi (app_access == 0)"""
    if current_user.app_access != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses Ditolak! Endpoint ini khusus untuk Owner / System Administrator Utama."
        )
    return current_user