import asyncio
import os
from fastapi import FastAPI, Request 
from fastapi.responses import JSONResponse, HTMLResponse 
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates 
from fastapi.middleware.cors import CORSMiddleware 
from dotenv import load_dotenv

from app.core.database import BaseMain, BasePSC, engine_main, engine_psc
from app.core.security import AuthException
from app.schemas.base import ApiResponse
from app.services.review_service import google_review_bot_worker
from app.routers import komplain, log, revenue, review, auth, users, notifications


load_dotenv()

BaseMain.metadata.create_all(bind=engine_main)
BasePSC.metadata.create_all(bind=engine_psc)

ENV = os.getenv("ENVIRONMENT", "development")

if ENV.lower() == "production":
    app = FastAPI(
        title="RSUD dr. Soebandi - Backend API",
        docs_url=None,       
        redoc_url=None,      
        openapi_url=None     
    )
else:
    app = FastAPI(
        title="RSUD dr. Soebandi - Backend API",
        description="Backend terpadu untuk sistem Google Review Bot, Manajemen Komplain (PSC), Laporan Pendapatan (Revenue)."
    )

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "*", 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

templates = Jinja2Templates(directory="templates")

replied_reviews_cache: set = set()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(google_review_bot_worker(replied_reviews_cache))


@app.get("/privacy-policy", response_class=HTMLResponse, include_in_schema=False)
async def get_privacy_policy(request: Request):
    return templates.TemplateResponse(request=request, name="privacy-policy.html")


@app.exception_handler(AuthException)
async def auth_exception_handler(request, exc: AuthException):
    return ApiResponse.error(message=exc.message, code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "code": 422,
            "data": exc.errors(),
        },
    )


app.include_router(auth.router)
app.include_router(review.router)
app.include_router(komplain.router)
app.include_router(revenue.router)
app.include_router(log.router)
app.include_router(users.router)
app.include_router(notifications.router)