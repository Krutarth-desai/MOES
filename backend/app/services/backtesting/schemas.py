from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BacktestSplitMethod(str, Enum):
    CHRONOLOGICAL_SPLIT = "chronological_split"
    ROLLING_ORIGIN = "rolling_origin"


class BacktestConfig(BaseModel):
    """
    Configuration options for forecast backtesting and skill comparison.
    """
    train_ratio: float = Field(
        default=0.60,
        ge=0.20,
        le=0.85,
        description="Fraction of historical data used strictly for training/calibration (0.60 = 60% train, 40% test)"
    )
    split_method: BacktestSplitMethod = Field(
        default=BacktestSplitMethod.CHRONOLOGICAL_SPLIT,
        description="Time-series evaluation split methodology"
    )
    rolling_window_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Window size in days for rolling-origin evaluation if rolling_origin method is selected"
    )
    variables: List[str] = Field(
        default_factory=lambda: ["temperature", "rainfall", "wind_speed"],
        description="Meteorological variables to evaluate"
    )
    rainfall_extreme_threshold: float = Field(
        default=64.5,
        description="IMD Heavy rainfall threshold in mm/day for categorical extreme metrics"
    )
    rainfall_event_threshold: float = Field(
        default=2.5,
        description="Rainfall measurable event threshold in mm/day"
    )


class ModelEvaluationScore(BaseModel):
    """
    Quantitative performance metrics for a specific model evaluated on test data.
    """
    model_name: str
    variable: str
    sample_size: int = Field(ge=0)
    mae: float = Field(description="Mean Absolute Error in variable units")
    rmse: float = Field(description="Root Mean Square Error in variable units")
    bias: float = Field(description="Mean Signed Bias (positive = overprediction, negative = underprediction)")
    correlation: float = Field(description="Pearson correlation coefficient [-1.0, 1.0]")

    # Categorical extreme/event metrics (especially for rainfall)
    csi: Optional[float] = Field(default=None, description="Critical Success Index (Threat Score) [0.0, 1.0]")
    pod: Optional[float] = Field(default=None, description="Probability of Detection (Hit Rate) [0.0, 1.0]")
    far: Optional[float] = Field(default=None, description="False Alarm Ratio [0.0, 1.0]")
    ets: Optional[float] = Field(default=None, description="Equitable Threat Score")
    brier_score: Optional[float] = Field(default=None, description="Probabilistic Brier Score")


class ModelRelativeComparison(BaseModel):
    """
    Comparative assessment of the Hybrid Blended Forecast relative to an individual baseline model.
    """
    model_name: str
    variable: str
    baseline_rmse: float
    hybrid_rmse: float
    rmse_reduction_pct: float = Field(
        description="Percentage error reduction: ((baseline - hybrid) / baseline) * 100%. Positive means improvement."
    )
    baseline_mae: float
    hybrid_mae: float
    mae_reduction_pct: float = Field(
        description="Percentage MAE reduction: ((baseline - hybrid) / baseline) * 100%"
    )
    baseline_correlation: float
    hybrid_correlation: float
    correlation_gain: float = Field(
        description="Absolute increase in Pearson correlation: (hybrid - baseline)"
    )


class ComparisonReportRow(BaseModel):
    """
    Standard tabular record for the dimensional comparison report:
    model | variable | lead time | region | metric
    """
    model_name: str
    variable: str
    lead_time_hours: Optional[int] = None
    region: Optional[str] = None
    metric: str = Field(description="Metric name: RMSE, MAE, Bias, Correlation, CSI, POD, FAR")
    value: float = Field(description="Calculated value of the metric")
    unit: str = Field(default="", description="Physical unit or index type")
    sample_size: int = Field(ge=0)
    relative_improvement_pct: Optional[float] = Field(
        default=None,
        description="Improvement percentage of Hybrid over this individual model (if applicable)"
    )


class DashboardHeadlineStatement(BaseModel):
    """
    Auditable executive statement formatted for the dashboard:
    'Hybrid forecast RMSE: X'
    'Best individual model RMSE: Y'
    'Relative improvement: Z%'
    """
    variable: str
    unit: str
    hybrid_rmse: float
    best_individual_model: str
    best_individual_rmse: float
    relative_improvement_pct: float
    statement_hybrid_rmse: str
    statement_best_model_rmse: str
    statement_relative_improvement: str
    summary_paragraph: str


class BacktestRunResult(BaseModel):
    """
    Comprehensive output artifact of a complete backtest run.
    """
    backtest_id: str
    evaluated_at: datetime = Field(default_factory=datetime.now)
    config: BacktestConfig
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    train_sample_count: int
    test_sample_count: int
    models_evaluated: List[str]
    variables_evaluated: List[str]

    # 1. Headline Statements for Dashboard
    headlines: Dict[str, DashboardHeadlineStatement] = Field(
        description="Key executive statements per variable for instant dashboard display"
    )

    # 2. Overall Scores Grouped by Variable -> Model Name
    overall_scores: Dict[str, Dict[str, ModelEvaluationScore]] = Field(
        description="Full metrics for all 5 models per variable"
    )

    # 3. Model Improvements Relative to Individual Models
    relative_improvements: Dict[str, List[ModelRelativeComparison]] = Field(
        description="Itemized relative improvement of Hybrid forecast vs each individual model"
    )

    # 4. Dimensional Comparison Report Rows (model | variable | lead time | region | metric)
    dimensional_report: List[ComparisonReportRow] = Field(
        description="Full multi-dimensional comparison table"
    )

    # 5. Timeseries Predictions for Dashboard Meteograms
    sample_test_predictions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sample aligned predictions for visualization"
    )
