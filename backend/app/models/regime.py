from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class RegimeType(str, Enum):
    NORMAL = "Normal"
    HEAVY_RAIN = "Heavy Rain"
    CONVECTIVE_STORM = "Convective/Storm"
    HEAT_WAVE = "Heat Wave"
    HIGH_WIND = "High Wind"
    COLD_SPELL = "Cold Spell"
    DRY_EXTREME_DRY = "Dry/Extreme Dry"


class WeatherContext(BaseModel):
    """
    Comprehensive atmospheric context supplied to the Weather Regime Classifier.
    """
    temperature: float = Field(description="Current or forecast surface temperature (°C)")
    rainfall: float = Field(ge=0.0, default=0.0, description="Current or 24h cumulative rainfall (mm)")
    wind_speed: float = Field(ge=0.0, default=0.0, description="Surface wind speed (km/h)")
    wind_direction: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Wind direction (0-360°)")
    humidity: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Relative humidity (%)")
    pressure: Optional[float] = Field(default=None, ge=800.0, le=1100.0, description="Mean Sea Level Pressure (hPa)")
    recent_rainfall: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        description="Antecedent cumulative rainfall over past 3 to 7 days (mm)"
    )
    forecast_trends: Dict[str, float] = Field(
        default_factory=dict,
        description="Atmospheric tendencies, e.g. {'temp_trend_24h': +4.2, 'pressure_tendency_12h': -3.5}"
    )

    # Geographic and local metadata
    station_id: Optional[str] = Field(default=None, description="Observatory ID, e.g. BOM, DEL")
    region: Optional[str] = Field(default="Indian Subcontinent", description="Geographic or agro-climatic region")
    elevation_m: Optional[float] = Field(default=100.0, description="Elevation above mean sea level in meters")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now, description="Valid evaluation timestamp")

    @field_validator("temperature", "rainfall", "wind_speed")
    @classmethod
    def round_precision(cls, v: float) -> float:
        return round(v, 2)


class RegimeClassificationResult(BaseModel):
    """
    Diagnostic result emitted by the Weather Regime Classifier.
    """
    regime: RegimeType = Field(description="Primary diagnosed atmospheric regime")
    regime_name: str = Field(description="Human-readable descriptive regime title")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence metric (0.0 to 1.0)")
    supporting_indicators: List[str] = Field(
        default_factory=list,
        description="Specific meteorological indicators and threshold exceedances justifying this diagnosis"
    )
    secondary_regime: Optional[RegimeType] = Field(
        default=None,
        description="Co-occurring secondary regime (e.g. High Wind accompanying Heavy Rain)"
    )
    severity_level: str = Field(
        default="NORMAL",
        description="Hazard level: NORMAL, MODERATE, SEVERE, or EXTREME"
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed synoptic explanation of the regime"
    )
    diagnosed_at: datetime = Field(default_factory=datetime.now)


class ForecastContext(BaseModel):
    """
    Atmospheric forecast context enriched with regime classification,
    providing situational awareness for downstream multi-model blending.
    """
    station_id: Optional[str] = None
    station_name: Optional[str] = None
    latitude: float
    longitude: float
    lead_time_hours: int = 24
    weather_variables: Dict[str, float] = Field(
        default_factory=dict,
        description="Forecasted or observed variables: temperature, rainfall, wind_speed, humidity, pressure, recent_rainfall"
    )
    regime_classification: RegimeClassificationResult
    created_at: datetime = Field(default_factory=datetime.now)
