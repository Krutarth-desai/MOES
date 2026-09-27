from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.data.ingestion.schema import ForecastVariable
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.observation.schema import ObservationIngestionReport, ObservationRecord
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.matcher import MatchedPair, MatchingConfig, SpatialTemporalMatcher
from backend.app.data.observation.evaluator import ForecastErrorCalculator, ModelComparisonSummary
from backend.app.config.settings import SAMPLE_DIR

router = APIRouter()
obs_service = ObservationIngestionService()
matcher = SpatialTemporalMatcher()
forecast_pipeline = IngestionPipeline()

OBS_CSV = SAMPLE_DIR / "observations.csv"


@router.get("/records", response_model=List[ObservationRecord])
def get_observations(
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Retrieve standardized ground-truth observation records.
    """
    records, _ = obs_service.load_file(OBS_CSV)
    if station_id:
        records = [r for r in records if r.station_id and r.station_id.upper() == station_id.upper()]
    return records[:limit]


@router.post("/match", response_model=List[MatchedPair])
def match_forecasts_with_observations(
    variable: Optional[ForecastVariable] = Query(None, description="Filter by variable"),
    model_name: Optional[str] = Query(None, description="Filter by model name substring"),
    max_distance_km: float = Query(40.0, description="Spatial tolerance radius in km"),
    max_time_offset_min: int = Query(60, description="Temporal tolerance window in minutes"),
    limit: int = Query(100, ge=1, le=2000),
):
    """
    Perform spatial-temporal matching between all ingested forecast predictions
    and ground-truth observations. Calculates per-sample signed and absolute errors.
    """
    # 1. Ingest forecasts if needed
    if not forecast_pipeline.get_all_records():
        forecast_pipeline.ingest_directory(SAMPLE_DIR)

    fcst_records = forecast_pipeline.query_records(variable=variable, source_name=model_name)
    obs_records, _ = obs_service.load_file(OBS_CSV)

    custom_matcher = SpatialTemporalMatcher(
        config=MatchingConfig(
            max_spatial_distance_km=max_distance_km,
            max_temporal_offset_minutes=max_time_offset_min,
        )
    )

    matched = custom_matcher.match(fcst_records, obs_records)
    return matched[:limit]


@router.get("/errors", response_model=Dict[str, Dict[str, ModelComparisonSummary]])
def calculate_forecast_errors():
    """
    Calculate statistical verification metrics (MAE, RMSE, Bias, Correlation, Lead-time profile)
    for every forecast model evaluated against ground-truth observations.
    """
    if not forecast_pipeline.get_all_records():
        forecast_pipeline.ingest_directory(SAMPLE_DIR)

    fcst_records = forecast_pipeline.get_all_records()
    obs_records, _ = obs_service.load_file(OBS_CSV)

    matched = matcher.match(fcst_records, obs_records)
    summary = ForecastErrorCalculator.evaluate_by_model_and_variable(matched)
    return summary
