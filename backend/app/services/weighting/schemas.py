from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FallbackLevel(str, Enum):
    EXACT = "EXACT"                       # Full match: Model, Variable, Lead, Region, Regime, Season
    REGIME_LEAD = "REGIME_LEAD"           # Model, Variable, Lead, Regime
    REGION_LEAD = "REGION_LEAD"           # Model, Variable, Lead, Region
    LEAD_TIME = "LEAD_TIME"               # Model, Variable, Lead
    OVERALL = "OVERALL"                   # Model, Variable overall
    UNSEEN_FALLBACK = "UNSEEN_FALLBACK"   # Neutral prior fallback (no historical records)


class ModelWeightDetail(BaseModel):
    """
    Transparent breakdown of a single model's derived weight and verified skill.
    """
    model_name: str
    weight: float = Field(description="Final normalized model weight (0.0 to 1.0)")
    raw_score: float = Field(description="Unadjusted raw historical skill score or inverse error")
    reliability_score: float = Field(description="Adjusted reliability score after sample size shrinkage")
    sample_size: int = Field(ge=0, description="Number of historical evaluation samples supporting this weight")
    fallback_level: FallbackLevel = Field(description="Stratification level matched in historical verification")
    explanation: str = Field(description="Transparent explanation of how this model's weight was derived")


class AdaptiveWeightOutput(BaseModel):
    """
    Output of the AdaptiveWeightEngine.
    Delivers normalized weights summing to 1.0 alongside rich interpretability summaries.
    """
    variable: str
    region: Optional[str] = None
    lead_time_hours: int
    season: Optional[str] = None
    weather_regime: Optional[str] = None
    weights: Dict[str, float] = Field(description="Model weights strictly normalized to sum to 1.0")
    normalized_weights: Dict[str, float] = Field(description="Convenience alias for normalized weights")
    model_details: List[ModelWeightDetail] = Field(description="Detailed derivation per model")
    summary_explanation: str = Field(description="Synthesized meteorological rationale for the weighting decision")
    safeguards_applied: List[str] = Field(default_factory=list, description="Active safeguards invoked during calculation")


class WeightCalculationRequest(BaseModel):
    """
    Input payload for requesting dynamic adaptive weights.
    """
    models: List[str] = Field(description="List of forecast models to assign weights to")
    variable: str = Field(description="Target forecast variable: rainfall, temperature, wind_speed")
    lead_time_hours: int = Field(default=24, ge=0, description="Forecast lead time in hours")
    region: Optional[str] = Field(default=None, description="Geographic region name")
    season: Optional[str] = Field(default=None, description="Climatological season")
    weather_regime: Optional[str] = Field(default=None, description="Current or diagnosed weather regime")
    min_weight: Optional[float] = Field(default=None, ge=0.0, le=0.5, description="Custom minimum weight floor")
    max_weight: Optional[float] = Field(default=None, ge=0.5, le=1.0, description="Custom maximum weight ceiling")
    historical_performance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional custom historical performance metrics overriding persisted store"
    )
