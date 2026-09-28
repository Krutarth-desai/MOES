from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BlendingMethod(str, Enum):
    LINEAR_WEIGHTED_SUM = "linear_weighted_sum"
    VECTOR_CIRCULAR_AVERAGE = "vector_circular_average"


class ModelContribution(BaseModel):
    """
    Detailed audit of an individual model's weighted contribution to the blended consensus.
    """
    model_name: str
    forecast_value: float = Field(description="Individual raw forecast prediction")
    adaptive_weight: float = Field(description="Final normalized adaptive weight assigned to this model")
    weighted_contribution: float = Field(description="Product of forecast_value and adaptive_weight")
    contribution_percentage: float = Field(description="Relative percentage share of the blended forecast (0 to 100%)")


class BlendedForecastResult(BaseModel):
    """
    Operational Blended Forecast Container.
    Captures individual model inputs, adaptive weights, final consensus,
    contributions, uncertainty bounds, and provenance.
    """
    forecast_id: str = Field(description="Unique deterministic ID for this blended realization")
    timestamp: datetime = Field(description="Forecast valid evaluation time")
    variable: str = Field(description="Standardized meteorological variable: temperature, rainfall, wind_speed, wind_direction")
    unit: str = Field(description="Physical unit (°C, mm, km/h, degrees)")
    station_id: Optional[str] = Field(default=None, description="Observatory code, e.g. BOM, DEL")
    station_name: Optional[str] = Field(default=None, description="Human readable station title")
    latitude: float = Field(description="Latitude in decimal degrees")
    longitude: float = Field(description="Longitude in decimal degrees")
    lead_time_hours: int = Field(ge=0, description="Forecast lead time in hours")
    region: Optional[str] = Field(default=None, description="Geographical or agro-climatic region")
    weather_regime: Optional[str] = Field(default=None, description="Active weather regime context")

    # 1. Inputs & Outputs
    individual_forecasts: Dict[str, float] = Field(description="Forecasts from all participating models")
    model_weights: Dict[str, float] = Field(description="Normalized adaptive weights applied to available models")
    blended_value: float = Field(description="Final dynamically blended forecast value")
    model_contributions: List[ModelContribution] = Field(description="Itemized contribution from each model")

    # 2. Confidence & Uncertainty Indicators
    confidence_index: float = Field(ge=0.0, le=1.0, description="Agreement confidence metric (1.0 = high consensus, 0.0 = high dispersion)")
    ensemble_spread: float = Field(ge=0.0, description="Multi-model weighted standard deviation or circular dispersion")
    confidence_interval_10th: Optional[float] = Field(default=None, description="Lower 10th percentile bound")
    confidence_interval_90th: Optional[float] = Field(default=None, description="Upper 90th percentile bound")

    # 3. Provenance & Validation Metadata
    models_available: List[str] = Field(description="Models providing valid inputs for this forecast")
    models_missing: List[str] = Field(default_factory=list, description="Configured models with missing predictions")
    models_rejected: List[str] = Field(default_factory=list, description="Models rejected due to physical boundary violations")
    weights_renormalized: bool = Field(default=False, description="Whether weights were dynamically re-scaled due to missing/rejected models")
    blending_method: BlendingMethod = Field(description="Mathematical blending technique utilized")
    explanation: Optional[Dict[str, Any]] = Field(default=None, description="Concise machine-readable explanation of the adaptive weighting decision")
    created_at: datetime = Field(default_factory=datetime.now)


class ForecastBlendRequest(BaseModel):
    """
    Request model for computing a blended forecast.
    """
    variable: str = Field(description="temperature, rainfall, wind_speed, wind_direction")
    lead_time_hours: int = Field(default=24, ge=0)
    station_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timestamp: Optional[datetime] = None
    region: Optional[str] = None
    weather_regime: Optional[str] = None
    model_forecasts: Optional[Dict[str, float]] = Field(
        default=None,
        description="Explicit dictionary of model forecasts. If None, retrieved from simulated provider."
    )
    model_weights: Optional[Dict[str, float]] = Field(
        default=None,
        description="Explicit dictionary of model weights. If None, derived dynamically from AdaptiveWeightEngine."
    )
    persist: bool = Field(default=True, description="Whether to persist the result into the BlendedForecastStore")
