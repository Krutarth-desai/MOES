from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.config.settings import SAMPLE_DIR
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.ingestion.schema import ForecastVariable
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.matcher import SpatialTemporalMatcher
from backend.app.services.verification.schemas import (
    LeadTimePerformanceResponse,
    OverallPerformanceResponse,
    RegimePerformanceResponse,
    RegionalPerformanceResponse,
    SeasonalPerformanceResponse,
)
from backend.app.services.verification.service import ForecastMetricsService

router = APIRouter()
metrics_service = ForecastMetricsService()
forecast_pipeline = IngestionPipeline()
obs_service = ObservationIngestionService()
matcher = SpatialTemporalMatcher()


def ensure_metrics_populated():
    """Helper to populate verification store if empty."""
    if not metrics_service.store.get_all_records():
        if not forecast_pipeline.get_all_records():
            forecast_pipeline.ingest_directory(SAMPLE_DIR)
        fcst_records = forecast_pipeline.get_all_records()
        obs_records, _ = obs_service.load_file(SAMPLE_DIR / "observations.csv")
        matched = matcher.match(fcst_records, obs_records)
        metrics_service.evaluate_and_store(matched)


@router.post("/recalculate")
def recalculate_verification_metrics():
    """
    Run full end-to-end verification across all ingested forecasts and observations.
    Computes and stores multi-dimensional metrics across Model, Variable, Region,
    Lead Time, Season, and Weather Regime.
    """
    if not forecast_pipeline.get_all_records():
        forecast_pipeline.ingest_directory(SAMPLE_DIR)
    fcst_records = forecast_pipeline.get_all_records()
    obs_records, _ = obs_service.load_file(SAMPLE_DIR / "observations.csv")

    matched = matcher.match(fcst_records, obs_records)
    records = metrics_service.evaluate_and_store(matched)

    return {
        "status": "success",
        "total_matched_pairs": len(matched),
        "total_skill_slices_computed": len(records),
        "persisted_store_path": str(metrics_service.store.storage_path),
    }


@router.get("/overall", response_model=OverallPerformanceResponse)
def get_overall_model_performance(
    variable: ForecastVariable = Query(ForecastVariable.RAINFALL, description="Forecast variable to evaluate"),
):
    """
    Retrieve overall comparative skill metrics (MAE, RMSE, Bias, Correlation, CSI)
    for all models on the requested weather variable.
    """
    ensure_metrics_populated()
    return metrics_service.get_overall_performance(variable=variable)


@router.get("/by-lead-time", response_model=LeadTimePerformanceResponse)
def get_performance_by_lead_time(
    variable: ForecastVariable = Query(ForecastVariable.RAINFALL),
    model_name: str = Query("NWP Model A", description="Model name substring (e.g. NWP Model A, ECMWF, GraphCast)"),
):
    """
    Retrieve error degradation curves across forecast lead times (24h, 48h, 72h, 96h, 120h, 144h, 168h).
    """
    ensure_metrics_populated()
    return metrics_service.get_performance_by_lead_time(variable=variable, model_name=model_name)


@router.get("/by-region", response_model=RegionalPerformanceResponse)
def get_performance_by_region(
    variable: ForecastVariable = Query(ForecastVariable.RAINFALL),
    model_name: str = Query("NWP Model A", description="Model name substring"),
):
    """
    Retrieve model skill metrics broken down by geographic agro-climatic region
    (Western Ghats, Indo-Gangetic Plains, Peninsular Plateau, etc.).
    """
    ensure_metrics_populated()
    return metrics_service.get_performance_by_region(variable=variable, model_name=model_name)


@router.get("/by-season", response_model=SeasonalPerformanceResponse)
def get_performance_by_season(
    variable: ForecastVariable = Query(ForecastVariable.RAINFALL),
    model_name: str = Query("NWP Model A", description="Model name substring"),
):
    """
    Retrieve model skill metrics broken down by climatological season (Monsoon, Post-Monsoon, Winter, Pre-Monsoon).
    """
    ensure_metrics_populated()
    return metrics_service.get_performance_by_season(variable=variable, model_name=model_name)


@router.get("/by-regime", response_model=RegimePerformanceResponse)
def get_performance_by_weather_regime(
    variable: ForecastVariable = Query(ForecastVariable.RAINFALL),
    model_name: str = Query("NWP Model A", description="Model name substring"),
):
    """
    Retrieve model skill metrics broken down by active synoptic weather regime
    (Active Monsoon Trough, Monsoon Break, Heatwave Synoptic, Western Disturbance, etc.).
    """
    ensure_metrics_populated()
    return metrics_service.get_performance_by_regime(variable=variable, model_name=model_name)
