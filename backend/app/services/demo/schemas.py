from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DemoScenarioId(str, Enum):
    MONSOON_CONVECTIVE_STORM = "monsoon_convective_storm"
    SEVERE_HEATWAVE_PLAINS = "severe_heatwave_plains"


class DemoStageStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DemoStageInfo(BaseModel):
    stage_number: int
    stage_id: str
    title: str
    description: str
    status: DemoStageStatus = DemoStageStatus.COMPLETED
    duration_ms: float = 0.0
    key_metrics: Dict[str, Any] = Field(default_factory=dict)
    summary_text: str = ""


class ModelPredictionItem(BaseModel):
    model_name: str
    forecast_value: float
    unit: str
    bias_characteristics: str
    historical_rmse: float
    assigned_weight: float
    weighted_contribution: float


class GeographicImpactZone(BaseModel):
    region_id: str
    region_name: str
    center_lat: float
    center_lon: float
    radius_km: float
    bounding_box: List[List[float]]
    affected_stations: List[Dict[str, Any]]
    hazard_summary: str
    alert_level: str  # RED, ORANGE, YELLOW, GREEN


class DemoScenarioResult(BaseModel):
    scenario_id: str
    scenario_title: str
    location_name: str
    station_id: str
    latitude: float
    longitude: float
    target_variable: str
    unit: str
    lead_time_hours: int
    executed_at: datetime = Field(default_factory=datetime.now)

    # 7 Required Sequential Processing Stages
    stages: List[DemoStageInfo]

    # Model Breakdown
    individual_models: List[ModelPredictionItem]

    # Weather Regime
    diagnosed_regime: str
    regime_confidence: float
    supporting_indicators: List[str]

    # Consensus & Blending
    blended_value: float
    ensemble_spread: float
    confidence_index: float

    # Comparative Skill & Backtesting Verification
    hybrid_rmse: float
    best_individual_rmse: float
    best_model_name: str
    relative_improvement_pct: float
    skill_verification_notice: str

    # Severe Weather Hazard
    extreme_event_detected: bool
    hazard_type: str
    alert_category: str  # RED, ORANGE, YELLOW, GREEN
    severity_level: str
    risk_score: float
    action_statement: str

    # Geographic Impact on Map
    geographic_impact: GeographicImpactZone

    # Machine-Readable Explainability
    explanation_title: str
    explanation_text: str
    weighting_rationale: Dict[str, str]

    # Processing Latency
    total_execution_time_ms: float
