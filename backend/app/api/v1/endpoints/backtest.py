from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from backend.app.services.backtesting.evaluator import BacktestEngine
from backend.app.services.backtesting.report import BacktestReportFormatter
from backend.app.services.backtesting.schemas import (
    BacktestConfig,
    BacktestRunResult,
    ComparisonReportRow,
    DashboardHeadlineStatement,
    ModelEvaluationScore,
    ModelRelativeComparison,
)
from backend.app.services.backtesting.store import BacktestResultStore

router = APIRouter()
store = BacktestResultStore()
engine = BacktestEngine()


def ensure_backtest_executed(required_variable: Optional[str] = None) -> BacktestRunResult:
    """Helper to auto-run backtest if no prior run exists or if requested variable is missing."""
    latest = store.get_latest()
    if not latest or (required_variable and required_variable.lower() not in [v.lower() for v in latest.variables_evaluated]):
        latest = engine.run_backtest()
        store.save_run(latest)
    return latest


@router.post("/run", response_model=BacktestRunResult, status_code=status.HTTP_200_OK)
def trigger_backtest_run(config: Optional[BacktestConfig] = None):
    """
    Executes a complete out-of-sample backtesting evaluation across all 5 models:
    NWP Model A, NWP Model B, Ensemble Forecast, AI Forecast, and Hybrid Blended Forecast.
    Guarantees no data leakage: weights are calibrated strictly on the training partition.
    """
    cfg = config or BacktestConfig()
    try:
        result = engine.run_backtest(config=cfg)
        store.save_run(result)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest execution failed: {str(e)}")


@router.get("/summary")
def get_backtest_dashboard_summary():
    """
    Returns executive summary statistics and headline statements for the dashboard.
    Outputs:
    - 'Hybrid forecast RMSE: X'
    - 'Best individual model RMSE: Y'
    - 'Relative improvement: Z%'
    - Model comparison metrics & relative error reduction
    """
    latest = ensure_backtest_executed()
    return {
        "backtest_id": latest.backtest_id,
        "evaluated_at": latest.evaluated_at.isoformat(),
        "train_window": f"{latest.train_start} to {latest.train_end}",
        "test_window": f"{latest.test_start} to {latest.test_end}",
        "train_sample_count": latest.train_sample_count,
        "test_sample_count": latest.test_sample_count,
        "models_evaluated": latest.models_evaluated,
        "headlines": latest.headlines,
        "overall_scores": latest.overall_scores,
        "relative_improvements": latest.relative_improvements,
    }


@router.get("/report")
def get_backtest_comparison_report(
    variable: Optional[str] = Query(None, description="Filter by variable (temperature, rainfall, wind_speed)"),
    lead_time_hours: Optional[int] = Query(None, ge=0, description="Filter by lead time"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. plains, coastal)"),
    model_name: Optional[str] = Query(None, description="Filter by model name"),
    metric: Optional[str] = Query(None, description="Filter by metric (RMSE, MAE, Bias, Correlation, CSI)"),
    export_format: str = Query("json", description="Output format: json, markdown, csv"),
):
    """
    Retrieves dimensional comparison report rows:
    model | variable | lead time | region | metric
    Supports JSON, Markdown table, and CSV formats.
    """
    ensure_backtest_executed(required_variable=variable)
    rows = store.query_report_rows(
        variable=variable,
        lead_time_hours=lead_time_hours,
        region=region,
        model_name=model_name,
        metric=metric,
    )

    if export_format == "markdown":
        md = BacktestReportFormatter.format_comparison_table(rows)
        return Response(content=md, media_type="text/markdown")
    elif export_format == "csv":
        csv_str = BacktestReportFormatter.export_report_csv(rows)
        return Response(content=csv_str, media_type="text/csv")

    return rows


@router.get("/timeseries", response_model=List[Dict[str, Any]])
def get_backtest_test_timeseries():
    """
    Retrieves aligned test time-series points (observed ground truth + all 5 model predictions)
    for plotting interactive verification charts on the dashboard.
    """
    latest = ensure_backtest_executed()
    return latest.sample_test_predictions


@router.get("/latest", response_model=BacktestRunResult)
def get_latest_backtest_result():
    """
    Retrieves the complete latest backtest run artifact.
    """
    return ensure_backtest_executed()
