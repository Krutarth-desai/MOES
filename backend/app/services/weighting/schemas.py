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


# =============================================================================
# Spatial Model Weight Mapping Schemas
# =============================================================================

class WeightDistributionMetrics(BaseModel):
    """
    Quantitative metrics describing the distribution and dispersion of model weights.
    """
    entropy: float = Field(ge=0.0, le=1.0, description="Normalized Shannon entropy (1.0 = equal consensus, 0.0 = single model monopoly)")
    spread: float = Field(description="Standard deviation across assigned model weights")
    dominant_margin: float = Field(description="Difference between dominant model weight and second-highest weight")
    top_share_pct: float = Field(description="Percentage share commanded by the dominant model")
    is_consensus: bool = Field(description="True if models have balanced weights without sharp divergence")


class WeightGridCell(BaseModel):
    """
    Spatial grid point containing geographic model weight allocation.
    """
    lat: float = Field(description="Latitude in degrees North")
    lon: float = Field(description="Longitude in degrees East")
    region_id: str = Field(description="Standardized region identifier (e.g. western_ghats, plains)")
    region_name: str = Field(description="Human readable sub-region name")
    elevation_m: float = Field(description="Approximate terrain elevation in meters")
    dominant_model: str = Field(description="Model receiving the highest weight at this coordinate")
    dominant_weight: float = Field(description="Numerical weight of the dominant model")
    weights: Dict[str, float] = Field(description="Normalized weights for all contributing models summing to 1.0")
    weight_distribution: WeightDistributionMetrics = Field(description="Dispersion and entropy statistics")
    model_reliabilities: Dict[str, float] = Field(description="Underlying verified reliability/skill scores per model")
    color: str = Field(description="Hex color code associated with the dominant model")


class RegionWeightSummary(BaseModel):
    """
    Aggregated region-level model reliability summary.
    """
    region_id: str = Field(description="Region identifier")
    region_name: str = Field(description="Region name")
    center_lat: float = Field(description="Representative latitude")
    center_lon: float = Field(description="Representative longitude")
    dominant_model: str = Field(description="Dominant forecast source in this region")
    dominant_weight: float = Field(description="Weight of the dominant model")
    weights: Dict[str, float] = Field(description="Normalized average regional weights")
    model_reliabilities: Dict[str, float] = Field(description="Regional average reliability scores per model")
    summary_formatted: str = Field(description="Formatted multiline text summary: 'Region A:\nModel A = 0.52...'")
    context_explanation: str = Field(description="Meteorological rationale explaining why model reliability varies in this region")
    key_strengths: Dict[str, str] = Field(description="Contextual strengths of individual models in this region")


class SpatialWeightGridResponse(BaseModel):
    """
    Complete spatial weight grid response suitable for interactive GIS map rendering.
    """
    variable: str = Field(description="Target forecast variable")
    lead_time_hours: int = Field(description="Forecast lead time in hours")
    season: str = Field(description="Climatological season")
    weather_regime: str = Field(description="Active synoptic weather regime")
    grid_resolution_deg: float = Field(description="Spatial resolution of the grid in degrees")
    total_cells: int = Field(description="Total number of evaluated spatial grid cells")
    grid_cells: List[WeightGridCell] = Field(description="List of all geographic weight cells")
    regional_summaries: List[RegionWeightSummary] = Field(description="Aggregated regional reliability summaries")
    model_colors: Dict[str, str] = Field(description="Color mapping for models")
    overall_distribution: Dict[str, Any] = Field(description="Macro distribution stats across the spatial domain")
    contextual_governance_notice: str = Field(
        default="Model reliability varies dynamically by geography, lead time, season, and atmospheric regime. No model is labeled or treated as globally 'best'.",
        description="Mandatory scientific governance notice preventing misleading 'best model' claims"
    )


class RegionalSummaryResponse(BaseModel):
    """
    Dedicated response container for region-level model reliability summaries.
    """
    variable: str
    lead_time_hours: int
    season: str
    weather_regime: str
    summaries: List[RegionWeightSummary]
    all_formatted_text: str = Field(description="Concatenated multiline summaries for all regions")
    contextual_governance_notice: str = Field(
        default="Model reliability varies dynamically by geography, lead time, season, and atmospheric regime. No model is labeled or treated as globally 'best'."
    )


class PointWeightRequest(BaseModel):
    """
    Payload for calculating model weights at an arbitrary geographic coordinate.
    """
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    variable: str = Field(default="rainfall")
    lead_time_hours: int = Field(default=24, ge=0)
    season: Optional[str] = Field(default=None)
    weather_regime: Optional[str] = Field(default=None)
    models: Optional[List[str]] = Field(default=None)

