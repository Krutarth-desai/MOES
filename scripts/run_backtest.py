#!/usr/bin/env python3
"""
Forecast Skill Comparison & Backtesting CLI Command.
Objectively compares NWP Model A, NWP Model B, Ensemble Forecast, AI Forecast,
and Hybrid Blended Forecast using out-of-sample time-series evaluation.

Usage:
    python scripts/run_backtest.py
    python scripts/run_backtest.py --train-ratio 0.60 --variable rainfall
    python scripts/run_backtest.py --format table
    python scripts/run_backtest.py --output data/processed/backtest_results.json
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from backend.app.services.backtesting.evaluator import BacktestEngine
from backend.app.services.backtesting.report import BacktestReportFormatter
from backend.app.services.backtesting.schemas import BacktestConfig, BacktestSplitMethod
from backend.app.services.backtesting.store import BacktestResultStore


def main():
    parser = argparse.ArgumentParser(
        description="Forecast Skill Comparison and Time-Series Backtesting Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.60,
        help="Fraction of data used strictly for training/calibration (default: 0.60)",
    )
    parser.add_argument(
        "--variable",
        type=str,
        default="all",
        choices=["all", "temperature", "rainfall", "wind_speed"],
        help="Specific variable to evaluate (default: all)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="table",
        choices=["table", "markdown", "json", "csv"],
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional path to save JSON results",
    )
    args = parser.parse_args()

    variables = ["temperature", "rainfall", "wind_speed"] if args.variable == "all" else [args.variable]
    cfg = BacktestConfig(
        train_ratio=args.train_ratio,
        variables=variables,
    )

    print("================================================================================")
    print("        HYBRID AI-NWP MULTI-MODEL FORECAST BACKTESTING ENGINE")
    print("================================================================================")
    print(f"Configuration: Split={int(cfg.train_ratio * 100)}% Train / {int((1 - cfg.train_ratio) * 100)}% Test")
    print(f"Target Variables: {', '.join(cfg.variables)}")
    print("Evaluating: 1. NWP Model A | 2. NWP Model B | 3. Ensemble | 4. AI | 5. Hybrid Blend")
    print("Status: Ingesting observations & forecasts, verifying time alignment...")

    engine = BacktestEngine(config=cfg)
    try:
        result = engine.run_backtest(config=cfg)
    except Exception as e:
        print(f"\n[ERROR] Backtesting failed: {e}", file=sys.stderr)
        sys.exit(1)

    # Persist results
    store = BacktestResultStore(storage_path=Path(args.output) if args.output else None)
    store.save_run(result)

    print(f"\n[SUCCESS] Backtest completed! ID: {result.backtest_id}")
    print(f"Train Window: {result.train_start} to {result.train_end} ({result.train_sample_count} pairs)")
    print(f"Test Window:  {result.test_start} to {result.test_end} ({result.test_sample_count} pairs)\n")

    # Print Executive Dashboard Statements
    print("--------------------------------------------------------------------------------")
    print("                       DASHBOARD EXECUTIVE STATEMENTS")
    print("--------------------------------------------------------------------------------")
    for var, headline in result.headlines.items():
        print(f"\n[{var.upper()}]")
        print(f"  * {headline.statement_hybrid_rmse}")
        print(f"  * {headline.statement_best_model_rmse}")
        print(f"  * {headline.statement_relative_improvement}")
        print(f"  > Summary: {headline.summary_paragraph}")

    # Print Output in Requested Format
    if args.format == "table" or args.format == "markdown":
        print("\n--------------------------------------------------------------------------------")
        print("          MULTI-MODEL COMPARISON REPORT (model | var | lead | region | metric)")
        print("--------------------------------------------------------------------------------")
        # Filter dimensional rows for the top 50 rows or overall
        overall_rows = [r for r in result.dimensional_report if r.lead_time_hours is None and r.region is None]
        print(BacktestReportFormatter.format_comparison_table(overall_rows))

        lead_rows = [r for r in result.dimensional_report if r.lead_time_hours is not None][:24]
        if lead_rows:
            print("\n### Performance by Forecast Lead Time:")
            print(BacktestReportFormatter.format_comparison_table(lead_rows))

    elif args.format == "csv":
        print(BacktestReportFormatter.export_report_csv(result.dimensional_report))

    elif args.format == "json":
        import json
        print(json.dumps(result.model_dump(mode="json"), indent=2))

    print("\n[INFO] Persisted results available via REST API at /api/v1/backtest/summary and /api/v1/backtest/report.")


if __name__ == "__main__":
    main()
