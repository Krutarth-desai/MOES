from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from backend.app.data.ingestion.schema import (
    ForecastVariable,
    IngestionReport,
    StandardForecastRecord,
)
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.config.settings import SAMPLE_DIR

router = APIRouter()
pipeline = IngestionPipeline()


@router.post("/load-samples", response_model=List[IngestionReport])
def load_sample_datasets():
    """
    Trigger ingestion of all multi-model sample datasets (NWP Model A, NWP Model B,
    Ensemble, AI Forecast, and Ground Truth).
    Executes unit normalization, physical bounds validation, and missing value repair.
    """
    if not SAMPLE_DIR.exists():
        raise HTTPException(status_code=404, detail="Sample datasets directory not found.")

    pipeline.clear()
    reports = pipeline.ingest_directory(SAMPLE_DIR)
    return reports


@router.get("/reports", response_model=List[IngestionReport])
def get_ingestion_reports():
    """
    Retrieve operational audit logs and data quality reports for all ingested sources.
    """
    return pipeline._reports_history


@router.get("/records", response_model=List[StandardForecastRecord])
def query_records(
    variable: Optional[ForecastVariable] = Query(None, description="Filter by variable"),
    lead_time_hours: Optional[int] = Query(None, description="Filter by lead time (24, 48, ...)"),
    source_name: Optional[str] = Query(None, description="Filter by source / model name substring"),
    region: Optional[str] = Query(None, description="Filter by region substring"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
):
    """
    Query canonical standardized forecast records stored in the ingestion layer.
    """
    if not pipeline.get_all_records():
        # Auto-load samples if empty
        pipeline.ingest_directory(SAMPLE_DIR)

    results = pipeline.query_records(
        variable=variable,
        lead_time_hours=lead_time_hours,
        source_name=source_name,
        region=region,
    )
    return results[:limit]
