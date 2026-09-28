import logging
import time
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.core_router import router as core_api_router
from backend.app.api.v1.router import api_router
from backend.app.config.settings import settings

# Configure application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("moes.app")

# API Tags Metadata for OpenAPI Documentation
tags_metadata = [
    {
        "name": "System Health",
        "description": "Liveness probes, health checks, and runtime environment status.",
    },
    {
        "name": "Forecasts",
        "description": "Multi-model individual forecasts and adaptive dynamically blended predictions.",
    },
    {
        "name": "Adaptive Weights",
        "description": "Historical skill-based model weight allocation, spatial grids, and distribution entropy.",
    },
    {
        "name": "Verification & Performance",
        "description": "Historical skill scores, continuous/categorical error metrics, and model comparison.",
    },
    {
        "name": "Extreme Weather",
        "description": "Extreme weather guidance engine for heavy rain, heat waves, and high wind advisories.",
    },
    {
        "name": "Weather Regimes",
        "description": "Synoptic weather situation diagnosis and atmospheric pattern classification.",
    },
    {
        "name": "Regions & Spatial Data",
        "description": "Indian meteorological macro-regions, topography, and climatological boundaries.",
    },
    {
        "name": "Operational Pipeline",
        "description": "End-to-end on-demand forecast blending and train/test time-series backtesting.",
    },
]

# Initialize FastAPI Application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Hybrid AI–NWP Multi-Model Forecast Blending System
### Smart India Hackathon Operational Backend

An intelligent meteorological forecast blending engine that combines physical NWP models
(NOAA GFS, ECMWF IFS), ensemble systems, and neural AI models (DeepMind GraphCast, Pangu-Weather).

### Core Features:
- **Dynamic Adaptive Blending**: Assigns weights by historical skill, lead time, region, season, and weather regime.
- **Strict Simplex Guarantee**: All assigned model weights strictly sum to 1.0000.
- **Circular Wind Averaging**: Vector component averaging for angular wind direction.
- **Extreme Weather Guidance**: Probabilistic risk scores and IMD standard color-coded advisories (Red, Orange, Yellow).
- **Model Weight Mapping**: Geographic grid visualization of dominant model coverage without declaring a global winner.
- **Data Leakage Safeguards**: Strict rolling-origin historical partitions for objective model backtesting.
""",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

# -----------------------------------------------------------------------------
# CORS Middleware Configuration
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------------------------------------------
# Request Timing & Access Logging Middleware
# -----------------------------------------------------------------------------
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    path = request.url.path
    method = request.method

    try:
        response = await call_next(request)
        process_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Process-Time-Ms"] = str(process_time_ms)
        logger.info(f"{method} {path} - {response.status_code} ({process_time_ms}ms)")
        return response
    except Exception as exc:
        process_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        logger.exception(f"Unhandled error processing {method} {path} after {process_time_ms}ms: {exc}")
        raise


# -----------------------------------------------------------------------------
# Structured Error Handling
# -----------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Uniform JSON error structure for standard HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Uniform JSON error structure for Pydantic request validation failures."""
    errors = exc.errors()
    simplified_errors = [
        {"field": " -> ".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in errors
    ]
    logger.warning(f"Validation failure on {request.method} {request.url.path}: {simplified_errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": simplified_errors,
            "error_code": "VALIDATION_ERROR",
            "message": "Request parameter validation failed.",
            "status_code": 422,
            "details": simplified_errors,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Uniform JSON error structure for unexpected server-side exceptions."""
    logger.exception(f"Unhandled 500 error on {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": str(exc),
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while processing the meteorological request.",
            "status_code": 500,
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


# -----------------------------------------------------------------------------
# Root & Legacy Health Endpoints
# -----------------------------------------------------------------------------
@app.get("/", tags=["System Health"])
def root():
    return {
        "status": "online",
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api_v1": settings.api_prefix,
        "core_api": "/api",
    }


@app.get("/health", tags=["System Health"])
def health_check():
    """Simple root health check endpoint."""
    return {
        "status": "healthy",
        "provider": settings.forecast_provider,
        "domain": settings.domain.name,
        "active_models": [m.name for m in settings.active_models],
    }


# -----------------------------------------------------------------------------
# Router Registrations
# -----------------------------------------------------------------------------
# 1. Primary Core APIs (/api/...) as specified
app.include_router(core_api_router, prefix="/api")

# 2. Modular v1 APIs (/api/v1/...) for backwards compatibility
app.include_router(api_router, prefix=settings.api_prefix)

# -----------------------------------------------------------------------------
# Static Frontend Serving (if built in frontend/dist)
# -----------------------------------------------------------------------------
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/dashboard", include_in_schema=False)
    @app.get("/demo", include_in_schema=False)
    def serve_dashboard():
        return FileResponse(str(frontend_dist / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

