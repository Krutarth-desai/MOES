from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from backend.app.services.extremes.schemas import ExtremeWeatherGuidance


# =============================================================================
# Health & Status Schemas
# =============================================================================

class HealthResponse(BaseModel):
    """
    Operational system health check schema.
    """
    status: str = Field(default="healthy", description="Service operational status")
    service: str = Field(description="Name of the application service")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(default_factory=datetime.now, description="Current server time")
    uptime_seconds: float = Field(description="Uptime in seconds since process initialization")
    database: str = Field(default="operational", description="Verification and station database status")
    active_modules: List[str] = Field(description="Registered operational backend modules")
    active_models: List[str] = Field(description="Forecast models configured for blending")


# =============================================================================
# Forecast Schemas
# =============================================================================

class LocationContext(BaseModel):
    """
    Geographic location metadata.
    """
    latitude: float
    longitude: float
    region: str
    station_id: Optional[str] = None
    location_name: Optional[str] = None


class ForecastsResponse(BaseModel):
    """
    Individual forecast model outputs for a target point and lead time.
    """
    location: LocationContext
    variable: str = Field(description="Weather variable (rainfall, temperature, wind_speed, wind_direction)")
    unit: str = Field(description="Unit of measurement (°C, mm, km/h, degrees)")
    lead_time_hours: int = Field(description="Forecast lead time in hours")
    forecast_time: str = Field(description="Valid forecast timestamp")
    season: str = Field(description="Climatological season")
    weather_regime: str = Field(description="Diagnosed synoptic weather regime")
    individual_forecasts: Dict[str, float] = Field(description="Raw predictions from participating forecast models")
    model_metadata: Dict[str, Any] = Field(default_factory=dict, description="Model category and configuration")


class ModelSkillSnapshotSchema(BaseModel):
    model_name: str
    weight: float
    rmse: float
    mae: float
    bias: float
    correlation: float
    csi: Optional[float] = None
    sample_size: int
    composite_skill_score: float


class WeightingExplanationResponse(BaseModel):
    """
    Concise, machine-readable explanation of adaptive weighting decisions.
    """
    summary_text: str = Field(description="Concise human-readable narrative of the adaptive weighting decision")
    variable: str = Field(description="Target forecast variable")
    region: str = Field(description="Geographic region")
    lead_time_hours: int = Field(description="Forecast lead time in hours")
    season: str = Field(description="Climatological season")
    current_weather_regime: str = Field(description="Active synoptic weather regime")
    selected_weights: Dict[str, float] = Field(description="Normalized weights assigned to each model")
    dominant_model: str = Field(description="Forecast model receiving the highest adaptive weight")
    dominant_weight: float = Field(description="Weight of the dominant model")
    dominant_reason: str = Field(description="Factual reason why dominant model was chosen")
    historical_skill_used: Dict[str, ModelSkillSnapshotSchema] = Field(description="Verified historical metrics used")
    decision_factors: List[str] = Field(description="Key decision factors behind the weighting")
    non_technical_summary: str = Field(description="Plain-language explanation for non-technical evaluation judges")


class BlendedForecastResponse(BaseModel):
    """
    Intelligent adaptive multi-model blended forecast response.
    """
    location: LocationContext
    variable: str
    unit: str
    lead_time_hours: int
    forecast_time: str
    season: str
    weather_regime: str
    blended_value: float = Field(description="Final dynamically blended forecast value")
    individual_forecasts: Dict[str, float] = Field(description="Individual model inputs")
    model_weights: Dict[str, float] = Field(description="Adaptive weights assigned to each model (summing to 1.0)")
    weighted_contributions: Dict[str, float] = Field(description="Normalized physical contribution of each model")
    confidence_interval_10th: float = Field(description="10th percentile uncertainty bound")
    confidence_interval_90th: float = Field(description="90th percentile uncertainty bound")
    uncertainty_spread: float = Field(description="Spread (90th - 10th percentile) indicating forecast consensus")
    blending_method: str = Field(description="Blending technique applied (e.g. adaptive_weighted_linear or circular_vector)")
    explanation: Optional[WeightingExplanationResponse] = Field(default=None, description="Explainability metadata for adaptive weighting decision")


# =============================================================================
# Model Weight Schemas
# =============================================================================

class ModelWeightsResponse(BaseModel):
    """
    Adaptive model weights breakdown for a target geographic and temporal context.
    """
    location: LocationContext
    variable: str
    lead_time_hours: int
    season: str
    weather_regime: str
    weights: Dict[str, float] = Field(description="Model weights strictly normalized to sum to 1.0")
    dominant_model: str = Field(description="Model receiving the highest weight in this context")
    dominant_weight: float = Field(description="Weight of the dominant model")
    distribution_entropy: float = Field(description="Normalized Shannon entropy (1.0 = equal consensus, 0.0 = single model monopoly)")
    model_reliabilities: Dict[str, float] = Field(description="Underlying verified historical skill scores")
    safeguards_applied: List[str] = Field(default_factory=list, description="Active operational safeguards triggered")
    explanation: str = Field(description="Transparent meteorological rationale for weight allocation")
    detailed_explanation: Optional[WeightingExplanationResponse] = Field(default=None, description="Structured explainability object")
    contextual_governance_notice: str = Field(
        default="Model reliability is strictly context-dependent. No model is labeled as globally 'best'."
    )


# =============================================================================
# Model Performance & Skill Comparison Schemas
# =============================================================================

class ModelPerformanceItem(BaseModel):
    """
    Historical verification metrics record for a single model and slice.
    """
    model_name: str
    variable: str
    lead_time_hours: Optional[int] = None
    region: Optional[str] = None
    season: Optional[str] = None
    weather_regime: Optional[str] = None
    sample_size: int = Field(ge=0)
    mae: float
    rmse: float
    bias: float
    correlation: float
    composite_skill_score: float
    csi: Optional[float] = None
    pod: Optional[float] = None
    far: Optional[float] = None


class ModelPerformanceResponse(BaseModel):
    """
    Query response for historical model performance.
    """
    variable: str
    records_count: int
    performance: List[ModelPerformanceItem]


class SkillComparisonItem(BaseModel):
    """
    Comparative performance record comparing an individual model or blended forecast.
    """
    model_name: str
    mae: float
    rmse: float
    bias: float
    correlation: float
    composite_skill_score: float
    is_hybrid_blend: bool = False
    improvement_vs_model_pct: Optional[float] = Field(
        default=None,
        description="Percentage error reduction achieved by hybrid blend relative to this model"
    )


class SkillComparisonResponse(BaseModel):
    """
    Objective comparison between individual models and the blended forecast.
    """
    variable: str
    lead_time_hours: int
    region: Optional[str] = None
    season: Optional[str] = None
    weather_regime: Optional[str] = None
    models_compared: List[SkillComparisonItem]
    hybrid_forecast_rmse: float
    best_individual_model_name: str
    best_individual_model_rmse: float
    relative_improvement_pct: float
    summary_statement: str = Field(
        description="Standard statement format: 'Hybrid forecast RMSE: X, Best individual model RMSE: Y, Relative improvement: Z%'"
    )


# =============================================================================
# Extreme Events Schemas
# =============================================================================

class ExtremeEventsResponse(BaseModel):
    """
    Structured Extreme Weather Guidance response container.
    """
    total_events: int
    lead_time_hours: int
    advisories_count_by_severity: Dict[str, int]
    guidance: List[ExtremeWeatherGuidance]


# =============================================================================
# Weather Regime Schemas
# =============================================================================

class WeatherRegimeResponse(BaseModel):
    """
    Diagnosed atmospheric weather regime and supporting physical indicators.
    """
    location: LocationContext
    lead_time_hours: int
    diagnosed_regime: str = Field(description="Normal, Heavy Rain, Convective/Storm, Heat Wave, High Wind, Cold Spell, Dry")
    confidence: float = Field(ge=0.0, le=1.0, description="Regime classification confidence")
    regime_description: str
    supporting_indicators: Union[List[str], Dict[str, Any]]
    atmospheric_situation: str


# =============================================================================
# Regions Schemas
# =============================================================================

class RegionItem(BaseModel):
    """
    Meteorological macro-region definition.
    """
    id: str
    name: str
    center_latitude: float
    center_longitude: float
    elevation_m: float
    coastal: bool
    description: str
    key_strengths: Dict[str, str]


class RegionsResponse(BaseModel):
    """
    List of registered Indian meteorological regions.
    """
    total_regions: int
    regions: List[RegionItem]


# =============================================================================
# Operational Pipeline Requests / Responses
# =============================================================================

class RunForecastRequest(BaseModel):
    """
    Payload for on-demand execution of the full operational forecast blending pipeline.
    """
    latitude: float = Field(default=19.0760, ge=-90.0, le=90.0, description="Latitude in degrees North")
    longitude: float = Field(default=72.8777, ge=-180.0, le=180.0, description="Longitude in degrees East")
    variable: str = Field(default="rainfall", description="Forecast variable: rainfall, temperature, wind_speed, wind_direction")
    lead_time: int = Field(default=24, ge=0, le=168, description="Forecast lead time in hours")
    season: Optional[str] = Field(default=None, description="Season (e.g. monsoon, winter)")
    weather_regime: Optional[str] = Field(default=None, description="Regime (e.g. normal, heavy_rain, heat_wave)")
    custom_model_inputs: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional explicit predictions from participating models"
    )


class RunForecastResponse(BaseModel):
    """
    Full operational forecast run response combining regime, weights, blend, and hazard detection.
    """
    execution_id: str
    timestamp: datetime
    location: LocationContext
    variable: str
    lead_time_hours: int
    diagnosed_regime: Dict[str, Any]
    model_inputs: Dict[str, float]
    adaptive_weights: Dict[str, float]
    blended_forecast: float
    unit: str
    uncertainty_bounds: Dict[str, float]
    extreme_weather_advisory: Optional[ExtremeWeatherGuidance] = None
    explanation: Optional[WeightingExplanationResponse] = None
    execution_time_ms: float


class RunBacktestRequest(BaseModel):
    """
    Payload for executing rolling-origin time-series backtest evaluation.
    """
    variable: str = Field(default="rainfall", description="Target variable to backtest")
    lead_time_hours: int = Field(default=24, ge=0, le=168, description="Lead time horizon in hours")
    region: Optional[str] = Field(default=None, description="Optional regional filter")
    test_split_ratio: float = Field(default=0.30, ge=0.1, le=0.5, description="Fraction reserved for test partition")


class RunBacktestResponse(BaseModel):
    """
    Backtesting report verifying hybrid forecast improvement without data leakage.
    """
    backtest_id: str
    variable: str
    lead_time_hours: int
    test_split_ratio: float
    train_sample_size: int
    test_sample_size: int
    model_comparison: List[SkillComparisonItem]
    hybrid_forecast_rmse: float
    best_individual_model: str
    best_individual_model_rmse: float
    relative_improvement_pct: float
    summary_statement: str
    data_leakage_safeguard: str = "Weights and metrics calibrated strictly on historical train partition"
    executed_at: datetime


# =============================================================================
# Structured Error Response Schema
# =============================================================================

class ErrorResponse(BaseModel):
    """
    Uniform structured error payload.
    """
    error_code: str = Field(description="Machine-readable error identifier")
    message: str = Field(description="Human-readable error description")
    details: Optional[Any] = Field(default=None, description="Detailed validation or exception info")
    timestamp: str = Field(description="ISO timestamp of error occurrence")
    path: str = Field(description="Request URL path")


# =============================================================================
# Automated Forecast Pipeline Schemas
# =============================================================================

from backend.app.pipeline.schemas import PipelineExecutionReport, PipelineTelemetry


class RunPipelineRequest(BaseModel):
    """
    Request payload to trigger an automated forecast processing pipeline run.
    """
    stations: Optional[List[str]] = Field(default=None, description="Station codes (e.g. ['BOM', 'DEL']). None for all.")
    variables: Optional[List[str]] = Field(default=None, description="Variables to blend (rainfall, temperature, wind_speed, wind_direction)")
    lead_times: Optional[List[int]] = Field(default=None, description="Lead times in hours (e.g. [6, 12, 24, 48])")
    season: Optional[str] = Field(default="monsoon", description="Climatological season")
    dry_run: bool = Field(default=False, description="Whether to execute without disk persistence")


class PipelineStatusResponse(BaseModel):
    """
    Status report of the automated forecast processing pipeline.
    """
    status: str = Field(default="operational", description="Pipeline status: operational, running, degraded")
    latest_run: Optional[PipelineExecutionReport] = Field(default=None, description="Most recent execution report")
    total_runs_recorded: int = Field(default=0, description="Total pipeline executions tracked")
    server_time: datetime = Field(default_factory=datetime.now)


# =============================================================================
# Data Sources & Formats Schemas
# =============================================================================

class DataSourceItem(BaseModel):
    name: str
    category: str  # "REAL DATA", "SIMULATED DATA", "DEMO DATA"
    source_type: str  # "netcdf", "csv", "json", "api", "simulated", "demo"
    description: str
    disclaimer: Optional[str] = None
    is_real: bool
    is_simulated: bool
    is_demo: bool
    supported_formats: List[str]


class DataSourcesConfigResponse(BaseModel):
    active_forecast_source: DataSourceItem
    active_observation_source: DataSourceItem
    supported_formats: List[str]
    plug_in_interfaces: Dict[str, str]
    disclaimer_notice: str


# =============================================================================
# SIH Demo Mode Schemas
# =============================================================================

class RunDemoRequest(BaseModel):
    """
    Request payload to trigger a deterministic SIH presentation demo scenario.
    """
    scenario_id: Optional[str] = Field(
        default="monsoon_convective_storm",
        description="Scenario identifier: 'monsoon_convective_storm' or 'severe_heatwave_plains'",
    )


class DemoScenariosListResponse(BaseModel):
    """
    List of pre-configured deterministic scenarios for jury presentation.
    """
    scenarios: List[Dict[str, Any]]
    total_count: int
    note: str = "Deterministic meteorological scenarios for SIH presentation. Zero fabricated metrics."



