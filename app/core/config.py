# app/core/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    DATABASE_MAIN: str = os.getenv("DATABASE_MAIN", "")
    DATABASE_PSC: str = os.getenv("DATABASE_PSC", "")
    GOOGLE_ACCOUNT_ID: str = os.getenv("GOOGLE_ACCOUNT_ID", "")
    GOOGLE_LOCATION_ID: str = os.getenv("GOOGLE_LOCATION_ID", "")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REFRESH_TOKEN: str = os.getenv("GOOGLE_REFRESH_TOKEN", "")
    # JWT & Security Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) 
    
settings = Settings()

if not settings.JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY harus diisi di .env")