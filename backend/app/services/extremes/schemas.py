from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExtremeEventType(str, Enum):
    HEAVY_RAINFALL = "heavy_rainfall"
    HEAT_WAVE = "heat_wave"
    HIGH_WIND = "high_wind"
    COLD_WAVE = "cold_wave"
    CONVECTIVE_STORM = "convective_storm"
    CUSTOM = "custom"


class AlertCategory(str, Enum):
    GREEN = "green"       # No Warning / Normal Conditions
    YELLOW = "yellow"     # Watch / Be Updated
    ORANGE = "orange"     # Alert / Be Prepared
    RED = "red"           # Warning / Take Action


class SeverityLevel(str, Enum):
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"


class ThresholdLevelConfig(BaseModel):
    """
    Threshold escalation bounds for an extreme weather hazard.
    """
    yellow_threshold: float = Field(description="Boundary value triggering Yellow Watch advisory")
    orange_threshold: float = Field(description="Boundary value triggering Orange Alert advisory")
    red_threshold: float = Field(description="Boundary value triggering Red Warning advisory")
    unit: str = Field(description="Physical unit: mm, °C, km/h, etc.")
    description: Optional[str] = Field(default=None, description="Criteria description or climatological basis")


class RegionalThresholdConfig(BaseModel):
    """
    Region-specific threshold configuration to account for geographic vulnerability.
    """
    hazard_type: ExtremeEventType
    region: str = Field(description="Region key: default, plains, hills, coastal, western_ghats, northeast, arid")
    levels: ThresholdLevelConfig


class DerivedRiskIndicator(BaseModel):
    """
    Derived probabilistic / vulnerability risk indicator.
    
    IMPORTANT: System must clearly distinguish between forecast value,
    derived risk indicator, and alert threshold. A risk score is an advisory
    indicator representing consensus potential, NOT a guaranteed deterministic outcome.
    """
    probability_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Multi-model ensemble exceedance probability (0.0 to 1.0)"
    )
    composite_risk_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Composite vulnerability index (0 to 100) combining magnitude, spread, and exceedance"
    )
    risk_level: str = Field(description="Qualitative risk classification: Low, Moderate, High, Extreme")
    disclaimer: str = Field(
        default="Probabilistic advisory indicator representing multi-model consensus; not a guaranteed deterministic outcome.",
        description="Mandatory scientific disclaimer preventing presentation of risk scores as guarantees"
    )


class AlertThresholdInfo(BaseModel):
    """
    Audit record of the specific alert threshold applied during hazard evaluation.
    """
    applied_threshold: float = Field(description="Active numerical boundary value checked")
    alert_category: AlertCategory = Field(description="Active category: GREEN, YELLOW, ORANGE, RED")
    threshold_unit: str = Field(description="Physical unit for this threshold")
    threshold_source: str = Field(description="Origin: IMD Standard, Regional Western Ghats, Custom Override, etc.")
    all_threshold_levels: Dict[str, float] = Field(description="All escalation cutoffs for this hazard and region")


class ExtremeWeatherGuidance(BaseModel):
    """
    Structured Extreme Weather Guidance Advisory Container.
    
    Explicitly distinguishes between:
    1. forecast_value: The predicted physical quantity (e.g. 118.5 mm, 45.2°C)
    2. derived_risk_indicator: The calculated probabilistic risk score and vulnerability index
    3. alert_threshold: The decision boundary used to trigger the alert category
    """
    event_id: str = Field(description="Deterministic unique ID for this advisory realization")
    event_type: ExtremeEventType = Field(description="Hazard category: heavy_rainfall, heat_wave, high_wind, etc.")
    location_name: str = Field(description="Human readable name of observatory or area")
    affected_region: str = Field(description="Geographic / agro-climatic region (e.g. Western Ghats, Coastal, Plains)")
    station_id: Optional[str] = Field(default=None, description="Observatory code if station-based (e.g. BOM, DEL)")
    latitude: float
    longitude: float
    expected_start_time: str = Field(description="ISO format expected onset time")
    expected_end_time: str = Field(description="ISO format expected cessation time")
    lead_time_hours: int = Field(ge=0, description="Lead time in hours")

    # Severity & Alert Recommendation
    severity_level: SeverityLevel = Field(description="Severity: none, minor, moderate, severe, extreme")
    recommended_alert_category: AlertCategory = Field(description="Color code: GREEN, YELLOW, ORANGE, RED")
    confidence: float = Field(ge=0.0, le=1.0, description="Agreement confidence metric across models (0.0 to 1.0)")

    # 1. Forecast Value (Physical Multi-Model Prediction)
    forecast_value: float = Field(description="Final blended multi-model forecast prediction value")
    forecast_unit: str = Field(description="Unit of measurement (°C, mm, km/h)")

    # 2. Derived Risk Indicator (Probabilistic Metric with Disclaimer)
    derived_risk_indicator: DerivedRiskIndicator = Field(
        description="Probabilistic consensus score & composite risk metric"
    )

    # 3. Alert Threshold (Active Decision Boundary)
    alert_threshold: AlertThresholdInfo = Field(
        description="Threshold configuration against which the forecast was tested"
    )

    # Contributing Models & Diagnostics
    contributing_models: List[str] = Field(description="Models providing inputs (e.g. GFS, ECMWF, GraphCast)")
    individual_model_forecasts: Dict[str, float] = Field(description="Raw forecast values from each participating model")
    model_weights: Optional[Dict[str, float]] = Field(default=None, description="Weights applied to models in consensus")

    # Actionable Guidance & Advisories
    advisory_headline: str = Field(description="Concise official headline warning")
    detailed_guidance: str = Field(description="Meteorological context and diagnostic rationale")
    recommended_actions: List[str] = Field(description="Targeted public safety and disaster mitigation actions")
    created_at: datetime = Field(default_factory=datetime.now)


class ScenarioDefinition(BaseModel):
    """
    Standard test scenario demonstrating specific meteorological conditions.
    """
    scenario_id: str
    name: str
    category: str = Field(description="heavy_rainfall, heat_wave, high_wind, normal_conditions")
    description: str
    station_id: str
    location_name: str
    region: str
    lead_time_hours: int
    variable: str
    model_forecasts: Dict[str, float]
    blended_value: float
    expected_alert_category: AlertCategory
    guidance: Optional[ExtremeWeatherGuidance] = None


class PointEvaluationRequest(BaseModel):
    """
    Payload for on-demand extreme weather guidance evaluation.
    """
    event_type: Optional[ExtremeEventType] = None
    station_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region: Optional[str] = None
    lead_time_hours: int = 24
    temperature: Optional[float] = None
    rainfall: Optional[float] = None
    wind_speed: Optional[float] = None
    model_forecasts: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional explicit multi-model forecasts dictionary"
    )
