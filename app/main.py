# app/main.py
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text

from app.core.database import BaseMain, BasePSC, engine_main, engine_psc
from app.core.security import AuthException
from app.schemas.base import ApiResponse
from app.services.review_service import google_review_bot_worker
from app.routers import komplain, revenue, review, auth

BaseMain.metadata.create_all(bind=engine_main)
BasePSC.metadata.create_all(bind=engine_psc)

app = FastAPI(title="RSUD dr. Soebandi - Google Review Bot API")

replied_reviews_cache: set = set()


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(google_review_bot_worker(replied_reviews_cache))


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