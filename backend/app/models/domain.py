from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.models.regime import RegimeClassificationResult


class WeatherVariable(str, Enum):
    PRECIPITATION = "precipitation"
    TEMPERATURE_2M = "temperature_2m"
    WIND_SPEED_10M = "wind_speed_10m"


class ForecastModelSource(str, Enum):
    GFS = "gfs"
    ECMWF = "ecmwf"
    GRAPHCAST = "graphcast"
    PANGU = "pangu"
    BLENDED = "blended"


class WeatherRegime(str, Enum):
    MONSOON_ACTIVE = "monsoon_active"
    MONSOON_BREAK = "monsoon_break"
    POST_MONSOON_CYCLONE = "post_monsoon_cyclone"
    WESTERN_DISTURBANCE = "western_disturbance"
    HEATWAVE_SYNOPTIC = "heatwave_synoptic"
    PRE_MONSOON_CONVECTIVE = "pre_monsoon_convective"
    NEUTRAL = "neutral"


class AlertSeverity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"


class HazardType(str, Enum):
    HEAVY_RAIN = "heavy_rain"
    VERY_HEAVY_RAIN = "very_heavy_rain"
    EXTREMELY_HEAVY_RAIN = "extremely_heavy_rain"
    HEATWAVE = "heatwave"
    GALE_WIND = "gale_wind"


class GeoPoint(BaseModel):
    lat: float
    lon: float
    name: Optional[str] = None
    elevation_m: Optional[float] = None
    region_type: Optional[str] = None  # e.g., coastal, plains, hills, peninsular


class PointForecastItem(BaseModel):
    valid_time: str
    lead_time_hours: int
    raw_predictions: Dict[str, float] = Field(
        description="Predictions from individual models (gfs, ecmwf, graphcast, pangu)"
    )
    blended_value: float
    confidence_interval_10th: float
    confidence_interval_90th: float


class PointForecastResponse(BaseModel):
    station_id: str
    station_name: str
    lat: float
    lon: float
    variable: WeatherVariable
    unit: str
    generated_at: str
    time_series: List[PointForecastItem]
    regime_context: Optional[RegimeClassificationResult] = Field(
        default=None,
        description="Diagnosed weather regime, confidence, and supporting indicators for the forecast context"
    )


class GridCell(BaseModel):
    lat: float
    lon: float
    value: float


class GriddedForecastResponse(BaseModel):
    variable: WeatherVariable
    unit: str
    lead_time_hours: int
    model_id: str
    valid_time: str
    min_value: float
    max_value: float
    mean_value: float
    grid_cells: List[GridCell]


class ModelWeightItem(BaseModel):
    model_id: str
    model_name: str
    weight: float
    historical_skill_score: float  # e.g., 1 - normalized RMSE


class RegionalWeightSummary(BaseModel):
    region_name: str
    lead_time_hours: int
    dominant_model: str
    weights: List[ModelWeightItem]


class SpatialWeightMapResponse(BaseModel):
    variable: WeatherVariable
    lead_time_hours: int
    detected_regime: WeatherRegime
    regional_weights: List[RegionalWeightSummary]


class HazardAlert(BaseModel):
    id: str
    hazard_type: HazardType
    severity: AlertSeverity
    title: str
    description: str
    location_name: str
    state: str
    lat: float
    lon: float
    valid_from: str
    valid_to: str
    exceedance_probability: float
    recommended_action: str


class ModelSkillScore(BaseModel):
    model_id: str
    model_name: str
    mae: float
    rmse: float
    correlation: float
    csi_score: Optional[float] = None  # Critical Success Index for extremes


class ComparativeMetricsResponse(BaseModel):
    variable: WeatherVariable
    lead_time_hours: int
    evaluation_window_days: int
    models: List[ModelSkillScore]
    blended_model: ModelSkillScore
    mae_improvement_pct: float
    rmse_improvement_pct: float


class RegimeClassificationResponse(BaseModel):
    active_regime: WeatherRegime
    regime_name: str
    confidence: float
    synoptic_summary: str
    dominant_features: List[str]
    valid_date: str
