from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PipelineConfig(BaseModel):
    """Configuration options for the automated forecast processing pipeline."""
    stations: Optional[List[str]] = Field(
        default=None,
        description="List of station IDs to process (e.g. ['BOM', 'DEL', 'BLR']). If None, processes all reference stations."
    )
    variables: List[str] = Field(
        default=["rainfall", "temperature", "wind_speed", "wind_direction"],
        description="Meteorological variables to blend and evaluate."
    )
    lead_times: List[int] = Field(
        default=[6, 12, 24, 48],
        description="Forecast lead times in hours."
    )
    season: Optional[str] = Field(
        default="monsoon",
        description="Climatological season context (monsoon, post_monsoon, winter, pre_monsoon)."
    )
    data_dir: Optional[str] = Field(
        default="data/sample",
        description="Path to local data directory containing raw/sample CSV and JSON files."
    )
    dry_run: bool = Field(
        default=False,
        description="If True, executes all calculations without persisting to disk."
    )
    persist_results: bool = Field(
        default=True,
        description="Whether to persist blended forecasts and telemetry to disk."
    )
    notify_dashboard: bool = Field(
        default=True,
        description="Whether to update dashboard status files."
    )


class StepResult(BaseModel):
    """Execution telemetry for an individual pipeline step."""
    step_number: int = Field(..., description="Pipeline step index (1-12)")
    step_name: str = Field(..., description="Descriptive name of the step")
    status: str = Field(default="SUCCESS", description="SUCCESS, WARNING, FAILED, or SKIPPED")
    execution_time_ms: float = Field(default=0.0, description="Step duration in milliseconds")
    records_in: int = Field(default=0, description="Number of input records received")
    records_out: int = Field(default=0, description="Number of output records produced")
    details: Dict[str, Any] = Field(default_factory=dict, description="Step-specific metadata and diagnostics")
    errors: List[str] = Field(default_factory=list, description="Errors or warnings recorded during this step")


class PipelineTelemetry(BaseModel):
    """
    Standardized telemetry metrics logged by the automated pipeline:
    - execution time
    - data sources
    - records processed
    - errors
    - models used
    - generated forecasts
    """
    execution_id: str = Field(..., description="Unique execution identifier")
    start_time: datetime = Field(..., description="Pipeline execution start timestamp")
    end_time: datetime = Field(..., description="Pipeline execution completion timestamp")
    execution_time_seconds: float = Field(..., description="Total wall-clock duration in seconds")
    execution_time_ms: float = Field(..., description="Total wall-clock duration in milliseconds")
    
    # 1. Data sources
    data_sources: List[str] = Field(
        default_factory=list,
        description="List of all forecast and observation data sources ingested"
    )
    
    # 2. Records processed
    records_processed: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of records processed across pipeline stages"
    )
    
    # 3. Errors
    errors: List[str] = Field(
        default_factory=list,
        description="List of non-fatal errors or validation warnings encountered"
    )
    error_count: int = Field(
        default=0,
        description="Total count of errors encountered"
    )
    
    # 4. Models used
    models_used: List[str] = Field(
        default_factory=list,
        description="List of forecast models evaluated and blended"
    )
    
    # 5. Generated forecasts
    generated_forecasts: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of blended consensus forecasts and extreme event advisories generated"
    )


class PipelineExecutionReport(BaseModel):
    """Complete summary report of an automated pipeline execution."""
    execution_id: str
    status: str = Field(default="SUCCESS", description="SUCCESS, PARTIAL, or FAILED")
    telemetry: PipelineTelemetry
    step_results: List[StepResult] = Field(default_factory=list)
    summary: str = Field(default="", description="Human and machine-readable execution summary")
    generated_at: datetime = Field(default_factory=datetime.now)
