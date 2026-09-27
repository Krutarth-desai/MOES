from fastapi import APIRouter
from backend.app.api.v1.endpoints import (
    forecast,
    weights,
    extremes,
    metrics,
    regimes,
    ingestion,
    observations,
    verification,
    backtest,
)

api_router = APIRouter()

api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecasts"])
api_router.include_router(weights.router, prefix="/weights", tags=["Adaptive Weights"])
api_router.include_router(extremes.router, prefix="/extremes", tags=["Extreme Weather Alerts"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Skill & Verification"])
api_router.include_router(regimes.router, prefix="/regimes", tags=["Synoptic Regimes"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Data Ingestion"])
api_router.include_router(observations.router, prefix="/observations", tags=["Observations & Ground Truth"])
api_router.include_router(verification.router, prefix="/verification", tags=["Forecast Verification Engine"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["Forecast Skill Comparison & Backtesting"])

