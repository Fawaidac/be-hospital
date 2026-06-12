import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

def hash_password(password: str) -> str:
    """Mengubah plain password menjadi hash SHA-256 sesuai standar MySQL SHA2(str, 256)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Memverifikasi password dengan mengubah inputan user menjadi SHA-256 
    lalu dicocokkan dengan hash statis yang ada di DB."""
    try:
        input_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        
        return input_hash == hashed_password
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
    Middleware Dependency untuk membatasi hak akses hanya untuk role superadmin.
    Meniru cara kerja middleware SuperAdminOnly di Laravel.
    """
    if current_user.role != "superadmin":
        raise AuthException(
            message="Forbidden, Super Admin Only", 
            status_code=status.HTTP_403_FORBIDDEN
        )
        
    return current_user