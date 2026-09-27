from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config.settings import settings
from backend.app.api.v1.router import api_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Operational Multi-Model Weather Forecast Blending & Hazard Warning System (SIH Prototype)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for modern frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "provider": settings.forecast_provider,
        "domain": settings.domain.name,
        "active_models": [m.name for m in settings.active_models],
    }


# Register main API router
app.include_router(api_router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
