from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime


class MetricDimensionSlice(BaseModel):
    """
    Identifies the exact multi-dimensional stratum of a skill score record.
    """
    model_name: str
    variable: ForecastVariable
    region: Optional[str] = None
    lead_time_hours: Optional[int] = None
    season: Optional[Season] = None
    weather_regime: Optional[WeatherRegime] = None


class ComprehensiveSkillScore(BaseModel):
    """
    Complete meteorological verification metrics container.
    Supports continuous, categorical extreme, and probabilistic skill scores.
    """
    sample_size: int = Field(ge=0, description="Number of verified forecast-observation pairs")

    # 1. Continuous Verification Metrics
    mae: float = Field(description="Mean Absolute Error in canonical variable units")
    rmse: float = Field(description="Root Mean Square Error in canonical variable units")
    bias: float = Field(description="Mean Signed Bias: (forecast - observed)")
    correlation: float = Field(ge=-1.0, le=1.0, description="Pearson Correlation Coefficient")

    # 2. Categorical Extreme Event Metrics (IMD criteria)
    extreme_threshold: Optional[float] = Field(default=None, description="Event exceedance threshold (e.g. 64.5 mm)")
    hits: Optional[int] = Field(default=None, ge=0)
    misses: Optional[int] = Field(default=None, ge=0)
    false_alarms: Optional[int] = Field(default=None, ge=0)
    correct_negatives: Optional[int] = Field(default=None, ge=0)
    pod: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Probability of Detection / Hit Rate")
    far: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="False Alarm Ratio")
    csi: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Critical Success Index / Threat Score")
    ets: Optional[float] = Field(default=None, description="Equitable Threat Score / Gilbert Skill Score")

    # 3. Probabilistic Verification Metrics
    brier_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Brier Score for event exceedance")
    brier_skill_score: Optional[float] = Field(default=None, description="Brier Skill Score relative to climatology")
    crps: Optional[float] = Field(default=None, ge=0.0, description="Continuous Ranked Probability Score")

    # 4. Computed Composite Skill Index for Adaptive Weighting
    composite_skill_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalized composite skill weight factor (1.0 = perfect, 0.0 = zero skill)"
    )


class HistoricalSkillRecord(BaseModel):
    """
    Persisted record linking dimensional slice to computed verification metrics.
    """
    dimension: MetricDimensionSlice
    metrics: ComprehensiveSkillScore
    evaluated_at: datetime = Field(default_factory=datetime.now)


class OverallPerformanceResponse(BaseModel):
    variable: ForecastVariable
    models: Dict[str, ComprehensiveSkillScore]
    best_model_by_mae: str
    best_model_by_rmse: str
    evaluated_at: str


class LeadTimePerformanceResponse(BaseModel):
    variable: ForecastVariable
    model_name: str
    lead_time_profile: Dict[int, ComprehensiveSkillScore]


class RegionalPerformanceResponse(BaseModel):
    variable: ForecastVariable
    model_name: str
    regional_profile: Dict[str, ComprehensiveSkillScore]


class SeasonalPerformanceResponse(BaseModel):
    variable: ForecastVariable
    model_name: str
    seasonal_profile: Dict[str, ComprehensiveSkillScore]


class RegimePerformanceResponse(BaseModel):
    variable: ForecastVariable
    model_name: str
    regime_profile: Dict[str, ComprehensiveSkillScore]
