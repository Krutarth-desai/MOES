from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ModelSkillSnapshot(BaseModel):
    """
    Historical verification metrics for a specific model used in weight derivation.
    """
    model_name: str = Field(description="Name of the forecast model")
    weight: float = Field(description="Normalized adaptive weight (0.0 to 1.0)")
    rmse: float = Field(description="Root Mean Square Error against ground truth")
    mae: float = Field(description="Mean Absolute Error")
    bias: float = Field(description="Mean signed forecast bias")
    correlation: float = Field(description="Pearson correlation coefficient")
    csi: Optional[float] = Field(default=None, description="Critical Success Index for event detection")
    sample_size: int = Field(description="Number of verified historical observations")
    composite_skill_score: float = Field(description="Reliability score derived from error metrics")


class WeightingExplanation(BaseModel):
    """
    Machine-readable explainability metadata for the adaptive weighting decision.
    Grounds all statements strictly in actual model weights and verified historical metrics.
    """
    summary_text: str = Field(
        description="Concise human-readable narrative formatted for operational displays and SIH judges"
    )
    variable: str = Field(description="Forecast variable evaluated")
    region: str = Field(description="Geographic region of the forecast point")
    lead_time_hours: int = Field(description="Forecast lead time in hours")
    season: str = Field(description="Climatological season")
    current_weather_regime: str = Field(description="Active synoptic weather regime")
    selected_weights: Dict[str, float] = Field(description="Final normalized model weights summing to 1.0")
    dominant_model: str = Field(description="Forecast model receiving the highest adaptive weight")
    dominant_weight: float = Field(description="Weight of the dominant model")
    dominant_reason: str = Field(description="Empirically verified reason why dominant model was chosen")
    historical_skill_used: Dict[str, ModelSkillSnapshot] = Field(
        description="Factual verification metrics for each participating model"
    )
    decision_factors: List[str] = Field(
        description="Key factual factors driving the dynamic weight allocation"
    )
    non_technical_summary: str = Field(
        description="Transparent 1-2 sentence explanation written for non-technical evaluation judges"
    )
