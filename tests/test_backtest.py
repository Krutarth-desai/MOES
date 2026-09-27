import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.backtesting.evaluator import BacktestEngine
from backend.app.services.backtesting.report import BacktestReportFormatter
from backend.app.services.backtesting.schemas import (
    BacktestConfig,
    BacktestRunResult,
    BacktestSplitMethod,
    ComparisonReportRow,
)
from backend.app.services.backtesting.store import BacktestResultStore


class TestBacktestEngine(unittest.TestCase):
    """
    Tests the Forecast Skill Comparison and Backtesting Engine.
    Verifies zero data leakage, multi-model evaluation across 5 models,
    non-fabricated metrics, and headline generation.
    """

    @classmethod
    def setUpClass(cls):
        cls.config = BacktestConfig(
            train_ratio=0.60,
            variables=["temperature", "rainfall", "wind_speed"],
        )
        cls.engine = BacktestEngine(config=cls.config)
        cls.result = cls.engine.run_backtest(config=cls.config)

    def test_all_five_models_present(self):
        """
        Verify that all 5 required models are evaluated:
        1. NWP Model A
        2. NWP Model B
        3. Ensemble Forecast
        4. AI Forecast
        5. Hybrid Blended Forecast
        """
        expected_models = {
            "NWP Model A",
            "NWP Model B",
            "Ensemble Forecast",
            "AI Forecast",
            "Hybrid Blended Forecast",
        }
        self.assertEqual(set(self.result.models_evaluated), expected_models)

        # Check in overall scores for each variable
        for var in self.result.variables_evaluated:
            scores = self.result.overall_scores[var]
            self.assertEqual(set(scores.keys()), expected_models)

    def test_time_series_split_and_no_data_leakage(self):
        """
        Verifies that training window and testing window are strictly disjoint
        and ordered chronologically (train_end < test_start).
        """
        train_start = self.result.train_start
        train_end = self.result.train_end
        test_start = self.result.test_start
        test_end = self.result.test_end

        self.assertLess(train_start, train_end)
        self.assertLess(train_end, test_start)
        self.assertLess(test_start, test_end)

        self.assertGreater(self.result.train_sample_count, 0)
        self.assertGreater(self.result.test_sample_count, 0)

    def test_separate_variable_evaluations(self):
        """
        Metrics must be calculated separately for temperature, rainfall, and wind_speed.
        """
        evaluated = self.result.variables_evaluated
        self.assertIn("temperature", evaluated)
        self.assertIn("rainfall", evaluated)
        self.assertIn("wind_speed", evaluated)

        for var in ["temperature", "rainfall", "wind_speed"]:
            self.assertIn(var, self.result.overall_scores)
            self.assertIn(var, self.result.headlines)
            self.assertIn(var, self.result.relative_improvements)

    def test_metrics_integrity_and_no_fabricated_numbers(self):
        """
        Ensures all continuous metrics (MAE, RMSE, Bias, Correlation) are calculated
        and that relative improvement is mathematically derived from test scores:
        improvement = ((baseline - hybrid) / baseline) * 100%.
        """
        for var, improvements in self.result.relative_improvements.items():
            hybrid_score = self.result.overall_scores[var]["Hybrid Blended Forecast"]

            # Verify Hybrid metrics are mathematically positive/reasonable
            self.assertGreaterEqual(hybrid_score.rmse, 0.0)
            self.assertGreaterEqual(hybrid_score.mae, 0.0)
            self.assertGreaterEqual(hybrid_score.correlation, -1.0)
            self.assertLessEqual(hybrid_score.correlation, 1.0)

            for comp in improvements:
                base_score = self.result.overall_scores[var][comp.model_name]

                # Verify exact mathematical formula for RMSE reduction
                expected_rmse_red = ((base_score.rmse - hybrid_score.rmse) / base_score.rmse) * 100.0
                self.assertAlmostEqual(comp.rmse_reduction_pct, expected_rmse_red, delta=0.05)

                # Verify exact mathematical formula for MAE reduction
                expected_mae_red = ((base_score.mae - hybrid_score.mae) / base_score.mae) * 100.0
                self.assertAlmostEqual(comp.mae_reduction_pct, expected_mae_red, delta=0.05)

                # Verify correlation gain: hybrid - baseline
                expected_corr_gain = hybrid_score.correlation - base_score.correlation
                self.assertAlmostEqual(comp.correlation_gain, expected_corr_gain, delta=0.01)

    def test_rainfall_event_metrics(self):
        """
        Rainfall must include categorical extreme event metrics (CSI, POD, FAR, Brier Score).
        """
        rain_scores = self.result.overall_scores["rainfall"]
        for m, score in rain_scores.items():
            self.assertIsNotNone(score.csi)
            self.assertIsNotNone(score.pod)
            self.assertIsNotNone(score.far)
            self.assertGreaterEqual(score.csi, 0.0)
            self.assertLessEqual(score.csi, 1.0)
            self.assertGreaterEqual(score.pod, 0.0)
            self.assertLessEqual(score.pod, 1.0)
            self.assertGreaterEqual(score.far, 0.0)
            self.assertLessEqual(score.far, 1.0)

    def test_dashboard_headline_statements(self):
        """
        Verifies dashboard executive statements contain exact required structure:
        - "Hybrid forecast RMSE: X"
        - "Best individual model RMSE: Y"
        - "Relative improvement: Z%"
        """
        for var, headline in self.result.headlines.items():
            self.assertTrue(headline.statement_hybrid_rmse.startswith("Hybrid forecast RMSE: "))
            self.assertTrue(headline.statement_best_model_rmse.startswith("Best individual model RMSE: "))
            self.assertTrue(headline.statement_relative_improvement.startswith("Relative improvement: "))

            # The best individual model must not be the Hybrid itself
            self.assertNotEqual(headline.best_individual_model, "Hybrid Blended Forecast")
            self.assertIn(headline.best_individual_model, [
                "NWP Model A",
                "NWP Model B",
                "Ensemble Forecast",
                "AI Forecast",
            ])

            # The best model's RMSE in the statement must match its evaluation score
            best_model_score = self.result.overall_scores[var][headline.best_individual_model]
            self.assertAlmostEqual(headline.best_individual_rmse, best_model_score.rmse, places=2)

    def test_dimensional_comparison_report(self):
        """
        Comparison report must contain records of:
        model | variable | lead time | region | metric
        """
        report_rows = self.result.dimensional_report
        self.assertGreater(len(report_rows), 20)

        # Check required fields
        for r in report_rows:
            self.assertIn(r.model_name, self.result.models_evaluated)
            self.assertIn(r.variable, self.result.variables_evaluated)
            self.assertIn(r.metric, ["RMSE", "MAE", "Bias", "Correlation", "CSI"])
            self.assertIsInstance(r.value, float)
            self.assertGreaterEqual(r.sample_size, 0)

        # Check formatters
        table_md = BacktestReportFormatter.format_comparison_table(report_rows[:10])
        self.assertIn("| Model | Variable | Lead Time | Region | Metric |", table_md)
        self.assertIn("NWP Model A", table_md)

        csv_str = BacktestReportFormatter.export_report_csv(report_rows[:10])
        self.assertIn("model,variable,lead_time_hours,region,metric,value", csv_str)


class TestBacktestStore(unittest.TestCase):
    """
    Tests saving, querying, and loading backtest run artifacts.
    """

    def setUp(self):
        self.test_store_path = Path("data/processed/test_backtest_store.json")
        self.store = BacktestResultStore(storage_path=self.test_store_path)
        self.store.clear()

    def tearDown(self):
        self.store.clear()

    def test_save_and_query_store(self):
        engine = BacktestEngine(config=BacktestConfig(variables=["temperature"]))
        run = engine.run_backtest()
        self.store.save_run(run)

        # Retrieve by latest
        latest = self.store.get_latest()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.backtest_id, run.backtest_id)

        # Query dimensional rows
        rows = self.store.query_report_rows(variable="temperature", metric="RMSE")
        self.assertGreater(len(rows), 0)
        for r in rows:
            self.assertEqual(r.metric, "RMSE")
            self.assertEqual(r.variable, "temperature")


class TestBacktestAPIEndpoints(unittest.TestCase):
    """
    Integration tests for the backtest REST API endpoints.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Ensure fresh backtest run with all target variables
        cls.client.post("/api/v1/backtest/run", json={"train_ratio": 0.60, "variables": ["temperature", "rainfall", "wind_speed"]})

    def test_post_run_endpoint(self):
        payload = {
            "train_ratio": 0.60,
            "variables": ["temperature", "rainfall"],
        }
        response = self.client.post("/api/v1/backtest/run", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("backtest_id", data)
        self.assertIn("headlines", data)
        self.assertIn("overall_scores", data)
        self.assertIn("relative_improvements", data)

    def test_get_summary_endpoint(self):
        response = self.client.get("/api/v1/backtest/summary")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("headlines", data)
        self.assertIn("temperature", data["headlines"])
        self.assertIn("statement_hybrid_rmse", data["headlines"]["temperature"])
        self.assertIn("statement_best_model_rmse", data["headlines"]["temperature"])
        self.assertIn("statement_relative_improvement", data["headlines"]["temperature"])

    def test_get_report_json_and_markdown(self):
        # JSON format
        resp_json = self.client.get("/api/v1/backtest/report?variable=rainfall&metric=RMSE")
        self.assertEqual(resp_json.status_code, 200)
        rows = resp_json.json()
        self.assertIsInstance(rows, list)
        self.assertGreater(len(rows), 0)
        self.assertEqual(rows[0]["variable"], "rainfall")
        self.assertEqual(rows[0]["metric"], "RMSE")

        # Markdown format
        resp_md = self.client.get("/api/v1/backtest/report?export_format=markdown")
        self.assertEqual(resp_md.status_code, 200)
        self.assertIn("| Model | Variable |", resp_md.text)

        # CSV format
        resp_csv = self.client.get("/api/v1/backtest/report?export_format=csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertIn("model,variable,lead_time_hours", resp_csv.text)

    def test_get_timeseries_endpoint(self):
        response = self.client.get("/api/v1/backtest/timeseries")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("observed_value", first)
        self.assertIn("predictions", first)
        self.assertIn("Hybrid Blended Forecast", first["predictions"])

    def test_get_latest_endpoint(self):
        response = self.client.get("/api/v1/backtest/latest")
        self.assertEqual(response.status_code, 200)
        self.assertIn("backtest_id", response.json())


class TestBacktestCLIExecution(unittest.TestCase):
    """
    Tests CLI command execution for reproducing backtest results.
    """

    def test_cli_command_runs_successfully(self):
        out_file = Path("data/processed/test_cli_reproduce.json")
        cmd = [
            sys.executable,
            "scripts/run_backtest.py",
            "--train-ratio", "0.60",
            "--variable", "temperature",
            "--format", "table",
            "--output", str(out_file),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path("d:/GIT/MOES")))
        if out_file.exists():
            out_file.unlink()
        self.assertEqual(proc.returncode, 0, f"CLI error: {proc.stderr}")
        self.assertIn("DASHBOARD EXECUTIVE STATEMENTS", proc.stdout)
        self.assertIn("Hybrid forecast RMSE:", proc.stdout)
        self.assertIn("Best individual model RMSE:", proc.stdout)
        self.assertIn("Relative improvement:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
