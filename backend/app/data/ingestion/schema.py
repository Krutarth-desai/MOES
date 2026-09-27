from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ForecastVariable(str, Enum):
    TEMPERATURE = "temperature"
    RAINFALL = "rainfall"
    WIND_SPEED = "wind_speed"
    WIND_DIRECTION = "wind_direction"


class ForecastSourceType(str, Enum):
    NWP = "nwp"
    ENSEMBLE = "ensemble"
    AI = "ai"
    OBSERVATION = "observation"


class Season(str, Enum):
    MONSOON = "monsoon"
    POST_MONSOON = "post_monsoon"
    WINTER = "winter"
    PRE_MONSOON = "pre_monsoon"


class WeatherRegime(str, Enum):
    MONSOON_ACTIVE = "monsoon_active"
    MONSOON_BREAK = "monsoon_break"
    CYCLONIC_CIRCULATION = "cyclonic_circulation"
    WESTERN_DISTURBANCE = "western_disturbance"
    HEATWAVE_SYNOPTIC = "heatwave_synoptic"
    CONVECTIVE_LOCAL = "convective_local"
    NEUTRAL = "neutral"


class QualityFlag(str, Enum):
    VALID = "VALID"
    IMPUTED = "IMPUTED"
    CLAMPED = "CLAMPED"
    REJECTED = "REJECTED"


class StandardForecastRecord(BaseModel):
    """
    Standardized, canonical forecast record for multi-model ingestion.
    All variables are normalized to standard SI / IMD reporting units:
      - temperature: Celsius (°C)
      - rainfall: Millimeters (mm)
      - wind_speed: Kilometers per hour (km/h)
      - wind_direction: Degrees clockwise from True North (0-360°)
    """
    timestamp: datetime = Field(description="Valid time of the forecast")
    latitude: float = Field(ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    forecast_variable: ForecastVariable = Field(description="Standardized variable type")
    forecast_value: float = Field(description="Forecast value in canonical units")
    initialization_time: datetime = Field(description="Model run initialization time")
    lead_time_hours: int = Field(ge=0, description="Forecast lead time in hours")
    source_name: str = Field(description="Originating model or forecast source name")
    region: str = Field(description="Geographic sub-region, e.g. Western Ghats, Indo-Gangetic Plains")
    season: Season = Field(description="Climatological season")
    weather_regime: Optional[WeatherRegime] = Field(
        default=WeatherRegime.NEUTRAL,
        description="Active synoptic weather regime if diagnosed"
    )

    # Ingestion provenance and audit flags
    raw_value: Optional[float] = Field(default=None, description="Original raw value before conversion")
    raw_unit: Optional[str] = Field(default=None, description="Original unit specified in source feed")
    quality_flag: QualityFlag = Field(default=QualityFlag.VALID, description="Data quality or imputation flag")
    station_id: Optional[str] = Field(default=None, description="Optional observatory station code")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata attributes")

    @field_validator("latitude")
    @classmethod
    def validate_latitude_precision(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_precision(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("forecast_value")
    @classmethod
    def validate_value_precision(cls, v: float) -> float:
        return round(v, 2)


class ValidationIssue(BaseModel):
    record_index: Optional[int] = None
    field: str
    issue_type: str  # e.g., "MISSING_VALUE", "OUT_OF_BOUNDS", "UNIT_CONVERSION", "INVALID_COORD"
    message: str
    action_taken: str  # e.g., "IMPUTED", "CLAMPED", "REJECTED", "CONVERTED"
    original_value: Optional[Any] = None
    resolved_value: Optional[Any] = None


class IngestionReport(BaseModel):
    source_name: str
    source_type: ForecastSourceType
    source_file: Optional[str] = None
    total_records_read: int = 0
    valid_records_count: int = 0
    imputed_records_count: int = 0
    rejected_records_count: int = 0
    issues: List[ValidationIssue] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0

    def mark_complete(self):
        self.completed_at = datetime.now()
        self.duration_ms = round((self.completed_at - self.started_at).total_seconds() * 1000.0, 2)
