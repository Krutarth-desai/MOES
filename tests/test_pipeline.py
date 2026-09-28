import json
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path

from backend.app.config.settings import DATA_DIR
from backend.app.pipeline.interfaces import (
    DashboardNotifierInterface,
    ForecastSourceInterface,
    ObservationSourceInterface,
)
from backend.app.pipeline.schemas import (
    PipelineConfig,
    PipelineExecutionReport,
    PipelineTelemetry,
)
from backend.app.pipeline.scheduler import PipelineScheduler
from backend.app.pipeline.sources import (
    FileForecastSource,
    FileObservationSource,
    SimulatedForecastSource,
    SimulatedObservationSource,
)
from backend.app.pipeline.store import PipelineRunStore
from backend.app.pipeline.workflow import AutomatedForecastPipeline


class TestAutomatedForecastPipeline(unittest.TestCase):
    """
    Comprehensive verification suite for the Automated Forecast Processing Workflow.
    Verifies all 12 sequential pipeline steps, modular source swapping,
    structured telemetry logging, CLI runner execution, and dashboard notifications.
    """

    def setUp(self):
        self.test_run_store = PipelineRunStore()
        self.pipeline = AutomatedForecastPipeline(run_store=self.test_run_store)

    def test_complete_12_step_pipeline_execution(self):
        """Verify all 12 operational steps execute sequentially and successfully."""
        config = PipelineConfig(
            stations=["BOM", "DEL"],
            variables=["rainfall", "temperature"],
            lead_times=[24],
            dry_run=True,
            persist_results=False,
            notify_dashboard=False,
        )

        report = self.pipeline.run(config=config)

        self.assertIsInstance(report, PipelineExecutionReport)
        self.assertIn(report.status, ("SUCCESS", "PARTIAL"))
        self.assertEqual(len(report.step_results), 12)

        # Verify all 12 step numbers and names
        expected_steps = [
            (1, "Ingest forecast data"),
            (2, "Ingest observations"),
            (3, "Validate data"),
            (4, "Preprocess data"),
            (5, "Determine weather regime"),
            (6, "Retrieve historical model skill"),
            (7, "Calculate adaptive weights"),
            (8, "Generate blended forecast"),
            (9, "Calculate uncertainty/confidence"),
            (10, "Detect extreme events"),
            (11, "Store results"),
            (12, "Update dashboard"),
        ]

        for idx, (expected_num, expected_name) in enumerate(expected_steps):
            step = report.step_results[idx]
            self.assertEqual(step.step_number, expected_num)
            self.assertEqual(step.step_name, expected_name)
            self.assertIn(step.status, ("SUCCESS", "WARNING"))
            self.assertGreaterEqual(step.execution_time_ms, 0.0)

    def test_telemetry_required_logging_fields(self):
        """
        Verify that all 6 required telemetry fields are populated:
        - execution time
        - data sources
        - records processed
        - errors
        - models used
        - generated forecasts
        """
        config = PipelineConfig(
            stations=["BOM"],
            variables=["rainfall"],
            lead_times=[24],
            dry_run=True,
            persist_results=False,
            notify_dashboard=False,
        )
        report = self.pipeline.run(config=config)
        tel = report.telemetry

        # 1. Execution time
        self.assertGreater(tel.execution_time_seconds, 0.0)
        self.assertGreater(tel.execution_time_ms, 0.0)

        # 2. Data sources
        self.assertIsInstance(tel.data_sources, list)
        self.assertGreaterEqual(len(tel.data_sources), 1)

        # 3. Records processed
        self.assertIn("total_records", tel.records_processed)
        self.assertIn("forecast_records", tel.records_processed)
        self.assertIn("observation_records", tel.records_processed)
        self.assertIn("validated_records", tel.records_processed)
        self.assertGreater(tel.records_processed["total_records"], 0)

        # 4. Errors
        self.assertIsInstance(tel.errors, list)
        self.assertEqual(tel.error_count, len(tel.errors))

        # 5. Models used
        self.assertIsInstance(tel.models_used, list)
        self.assertIn("NWP Model A", tel.models_used)
        self.assertIn("NWP Model B", tel.models_used)

        # 6. Generated forecasts
        self.assertIsInstance(tel.generated_forecasts, dict)
        self.assertIn("total_blended_forecasts", tel.generated_forecasts)
        self.assertGreater(tel.generated_forecasts["total_blended_forecasts"], 0)

    def test_modular_source_swapping(self):
        """Verify that modular custom data sources can replace default feeds seamlessly."""
        custom_forecast_source = SimulatedForecastSource()
        custom_observation_source = SimulatedObservationSource()

        custom_pipeline = AutomatedForecastPipeline(
            forecast_source=custom_forecast_source,
            observation_source=custom_observation_source,
            run_store=self.test_run_store,
        )

        config = PipelineConfig(
            stations=["CCU"],
            variables=["wind_speed"],
            lead_times=[12],
            dry_run=True,
            persist_results=False,
            notify_dashboard=False,
        )

        report = custom_pipeline.run(config=config)
        self.assertTrue(any("SimulatedForecastProvider" in s for s in report.telemetry.data_sources))

    def test_pipeline_persistence_and_dashboard_update(self):
        """Verify report persistence to latest_pipeline_run.json."""
        config = PipelineConfig(
            stations=["BOM"],
            variables=["rainfall"],
            lead_times=[24],
            dry_run=False,
            persist_results=True,
            notify_dashboard=True,
        )
        report = self.pipeline.run(config=config)

        latest = self.test_run_store.get_latest_run()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.execution_id, report.execution_id)

    def test_scheduler_bounded_execution(self):
        """Verify PipelineScheduler runs for the exact bounded iteration count."""
        config = PipelineConfig(
            stations=["BOM"],
            variables=["temperature"],
            lead_times=[24],
            dry_run=True,
            persist_results=False,
            notify_dashboard=False,
        )
        scheduler = PipelineScheduler(pipeline=self.pipeline, config=config)

        # Run for 2 iterations with small interval (0.1s)
        scheduler.run_interval(interval_seconds=1, max_iterations=2, blocking=True)
        self.assertEqual(scheduler.iteration_count, 2)
        self.assertIsNotNone(scheduler.last_report)

    def test_cli_runner_execution(self):
        """Verify that `python run_pipeline.py --once` executes cleanly from the terminal."""
        cmd = [
            sys.executable,
            "run_pipeline.py",
            "--once",
            "--stations", "BOM",
            "--variables", "temperature",
            "--lead-times", "24",
            "--dry-run",
            "--no-dashboard-update",
        ]
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, f"CLI runner failed: {result.stderr}")
        self.assertIn("AUTOMATED METEOROLOGICAL FORECAST PROCESSING REPORT", result.stdout + result.stderr)
        self.assertIn("Pipeline Execution ID:", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
