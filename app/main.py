import asyncio
import os
from fastapi import FastAPI, Request 
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse # Tambahkan FileResponse disini
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles # Tambahkan StaticFiles untuk folder build Flutter
from fastapi.templating import Jinja2Templates 
from fastapi.middleware.cors import CORSMiddleware 
from dotenv import load_dotenv
import httpx # Tambahkan httpx untuk fitur proxy API

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
    allow_headers=["Content-Type", "Authorization", "x-token", "x-target-url"], # Diperbarui agar custom header proxy diizinkan
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


# ==========================================
# ENDPOINT CORS PROXY (Dinamis GET & POST)
# ==========================================
@app.api_route("/proxy", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def cors_proxy(request: Request):
    target_url = request.headers.get("x-target-url")
    if not target_url:
        return JSONResponse(
            status_code=400, 
            content={"success": False, "message": "Header 'x-target-url' wajib diisi"}
        )

    x_token = request.headers.get("x-token", "soebandi2507")
    body = await request.body()

    headers = {
        "x-token": x_token,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None
            )
            
            # Mendapatkan output JSON / raw response dari server target
            try:
                data = response.json()
                return JSONResponse(status_code=response.status_code, content=data)
            except Exception:
                return httpx.Response(
                    content=response.content,
                    status_code=response.status_code,
                    media_type=response.headers.get("content-type", "text/plain")
                )
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": f"Proxy Error: {str(exc)}"}
        )


# ==========================================
# 1. INTEGRASI FRONTEND UTAMA (frontend_dist)
# ==========================================
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_dist")

if os.path.exists(FRONTEND_DIR):
    # Mount folder statis frontend utama
    if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
        app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="flutter_assets")
    
    if os.path.exists(os.path.join(FRONTEND_DIR, "canvaskit")):
        app.mount("/canvaskit", StaticFiles(directory=os.path.join(FRONTEND_DIR, "canvaskit")), name="flutter_canvaskit")

    @app.get("/")
    async def serve_flutter_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

# ==========================================
# 2. INTEGRASI FRONTEND SOEBIS (/soebis)
# ==========================================
SOEBIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soebis")

if os.path.exists(SOEBIS_DIR):
    # Mount folder statis SOEBIS dengan prefix & name unik
    if os.path.exists(os.path.join(SOEBIS_DIR, "assets")):
        app.mount("/soebis/assets", StaticFiles(directory=os.path.join(SOEBIS_DIR, "assets")), name="soebis_assets")

    if os.path.exists(os.path.join(SOEBIS_DIR, "canvaskit")):
        app.mount("/soebis/canvaskit", StaticFiles(directory=os.path.join(SOEBIS_DIR, "canvaskit")), name="soebis_canvaskit")

    @app.get("/soebis")
    @app.get("/soebis/")
    async def serve_soebis_index():
        return FileResponse(os.path.join(SOEBIS_DIR, "index.html"))

    # Single-Page Application (SPA) Routing & Static Fallback Khusus SOEBIS
    @app.get("/soebis/{catchall:path}")
    async def serve_soebis_spa(catchall: str):
        file_path = os.path.join(SOEBIS_DIR, catchall)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(SOEBIS_DIR, "index.html"))

# ==========================================
# 3. INTEGRASI FRONTEND SOESIE (/soesie)
# ==========================================
SOESIE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "soesie")

if os.path.exists(SOESIE_DIR):
    # Mount folder statis SOESIE dengan prefix & name unik
    if os.path.exists(os.path.join(SOESIE_DIR, "assets")):
        app.mount("/soesie/assets", StaticFiles(directory=os.path.join(SOESIE_DIR, "assets")), name="soesie_assets")

    if os.path.exists(os.path.join(SOESIE_DIR, "canvaskit")):
        app.mount("/soesie/canvaskit", StaticFiles(directory=os.path.join(SOESIE_DIR, "canvaskit")), name="soesie_canvaskit")

    @app.get("/soesie")
    @app.get("/soesie/")
    async def serve_soesie_index():
        return FileResponse(os.path.join(SOESIE_DIR, "index.html"))

    # Single-Page Application (SPA) Routing & Static Fallback Khusus SOESIE
    @app.get("/soesie/{catchall:path}")
    async def serve_soesie_spa(catchall: str):
        file_path = os.path.join(SOESIE_DIR, catchall)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(SOESIE_DIR, "index.html"))
# ==========================================
# 4. GLOBAL SPA CATCHALL (Harus Paling Bawah)
# ==========================================
if os.path.exists(FRONTEND_DIR):
    @app.get("/{catchall:path}")
    async def walk_around_routing(catchall: str):
        # Jalur API yang tidak terdaftar tetap mengembalikan 404 JSON
        if catchall.startswith("api/") or catchall == "proxy":
            return JSONResponse(status_code=404, content={"success": False, "message": "API Endpoint Not Found"})
        
        # Validasi berkas statis di root frontend_dist
        file_path = os.path.join(FRONTEND_DIR, catchall)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback ke index.html frontend utama
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))