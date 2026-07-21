import asyncio
import os
from fastapi import FastAPI, Request 
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse # Tambahkan FileResponse disini
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles # Tambahkan StaticFiles untuk folder build Flutter
from fastapi.templating import Jinja2Templates 
from fastapi.middleware.cors import CORSMiddleware 
from dotenv import load_dotenv

from app.core.database import BaseMain, BasePSC, engine_main, engine_psc
from app.core.security import AuthException
from app.schemas.base import ApiResponse
from app.services.review_service import google_review_bot_worker
from app.routers import komplain, laporan_kunjungan, log, pelayanan, revenue, review, auth, users, notifications, laporan_rawat_inap


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


# --- ROUTER API UTAMA (Wajib Dideklarasikan Duluan) ---
app.include_router(auth.router)
app.include_router(review.router)
app.include_router(komplain.router)
app.include_router(revenue.router)
app.include_router(log.router)
app.include_router(users.router)
app.include_router(notifications.router)
app.include_router(laporan_rawat_inap.router)
app.include_router(laporan_kunjungan.router)
app.include_router(pelayanan.router)


# =========================================================================
# 🚀 INTEGRASI FRONTEND FLUTTER WEB (DITARUH DI PALING BAWAH)
# =========================================================================

# =========================================================================
# 🚀 INTEGRASI FRONTEND FLUTTER WEB (DITARUH DI PALING BAWAH)
# =========================================================================

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_dist")

if os.path.exists(FRONTEND_DIR):
    # 1. Mount folder assets bawaan Flutter
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="flutter_assets")
    
    # 🌟 PENTING: Mount folder canvaskit bawaan Flutter agar rendering grafis aman
    if os.path.exists(os.path.join(FRONTEND_DIR, "canvaskit")):
        app.mount("/canvaskit", StaticFiles(directory=os.path.join(FRONTEND_DIR, "canvaskit")), name="flutter_canvaskit")

    # 2. Tangkap URL Root (/) untuk memunculkan dashboard Flutter
    @app.get("/")
    async def serve_flutter_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    # 3. Solusi Jaring Pengaman Router + Handler File Statis di Root
    @app.get("/{catchall:path}")
    async def walk_around_routing(catchall: str):
        # Jika user menembak API palsu/salah, lempar error JSON API asli
        if catchall.startswith("api/"):
            return JSONResponse(status_code=404, content={"success": False, "message": "API Endpoint Not Found"})
        
        # 🌟 VALIDASI FILE STATIS ROOT (Mencegah eror Unexpected token '<')
        # Cek apakah file yang diminta browser (seperti flutter_bootstrap.js, manifest.json, dll) ada di root frontend_dist
        file_path = os.path.join(FRONTEND_DIR, catchall)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Selain API dan file statis asli (misal user ngakses route /dashboard), oper kendali ke index.html Flutter
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    @app.get("/")
    async def frontend_fallback():
        return HTMLResponse("<h3>Backend RSUD dr. Soebandi Aktif. Folder 'frontend_dist' belum di-upload.</h3>")
    # Mode cadangan jika folder frontend belum di-upload ke server VPS
    @app.get("/")
    async def frontend_fallback():
        return HTMLResponse("<h3>Backend RSUD dr. Soebandi Aktif. Folder 'frontend_dist' belum di-upload.</h3>")