import unittest
from datetime import datetime, timedelta
from pathlib import Path
from backend.app.data.ingestion.schema import ForecastVariable, StandardForecastRecord, Season, WeatherRegime
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.observation.schema import ObservationRecord
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.matcher import SpatialTemporalMatcher, MatchingConfig
from backend.app.data.observation.evaluator import ForecastErrorCalculator
from backend.app.config.settings import SAMPLE_DIR


class TestObservationPipeline(unittest.TestCase):
    def setUp(self):
        self.ingestion_service = ObservationIngestionService()
        self.matcher = SpatialTemporalMatcher()
        self.obs_csv = SAMPLE_DIR / "observations.csv"
        self.obs_json = SAMPLE_DIR / "observations.json"

    def test_ingest_observations_csv(self):
        records, report = self.ingestion_service.load_file(self.obs_csv)
        self.assertGreater(len(records), 50)
        self.assertGreater(report.valid_records_count, 50)

        # Check negative rain clamping test case
        clamped_issues = [i for i in report.issues if i.field == "rainfall" and i.action_taken == "CLAMPED"]
        self.assertGreater(len(clamped_issues), 0)
        self.assertEqual(clamped_issues[0].resolved_value, 0.0)

        # Check missing wind direction test case
        records_with_missing_wd = [r for r in records if r.quality_flags.get("wind_direction") == "MISSING"]
        self.assertGreater(len(records_with_missing_wd), 0)

    def test_ingest_observations_json(self):
        records, report = self.ingestion_service.load_file(self.obs_json)
        self.assertGreater(len(records), 50)
        self.assertEqual(report.valid_records_count, len(records))

    def test_spatial_temporal_matching(self):
        # 1. Ingest forecast records
        pipeline = IngestionPipeline()
        pipeline.ingest_file(SAMPLE_DIR / "nwp_model_a.csv", source_key="nwp_model_a")
        pipeline.ingest_file(SAMPLE_DIR / "ai_forecast.json", source_key="ai_forecast")
        fcst_records = pipeline.get_all_records()

        # 2. Ingest observations
        obs_records, _ = self.ingestion_service.load_file(self.obs_csv)

        # 3. Match
        matched = self.matcher.match(fcst_records, obs_records)
        self.assertGreater(len(matched), 100)

        # Inspect first matched pair
        first = matched[0]
        self.assertIsNotNone(first.forecast_value)
        self.assertIsNotNone(first.observed_value)
        self.assertAlmostEqual(first.error, first.forecast_value - first.observed_value, places=2)
        self.assertAlmostEqual(first.absolute_error, abs(first.error), places=2)
        self.assertLessEqual(first.spatial_distance_km, 40.0)
        self.assertLessEqual(first.temporal_offset_minutes, 60.0)

    def test_temporal_offset_window_matching(self):
        # Create a forecast at 12:00
        fcst_time = datetime(2026, 7, 16, 12, 0, 0)
        fcst = StandardForecastRecord(
            timestamp=fcst_time,
            latitude=19.0760,
            longitude=72.8777,
            forecast_variable=ForecastVariable.TEMPERATURE,
            forecast_value=32.0,
            initialization_time=datetime(2026, 7, 15, 0, 0, 0),
            lead_time_hours=36,
            source_name="Test Model",
            region="Western Ghats",
            season=Season.MONSOON,
            weather_regime=WeatherRegime.MONSOON_ACTIVE,
            station_id="BOM",
        )

        # Observation recorded 20 minutes later at 12:20
        obs_within = ObservationRecord(
            timestamp=fcst_time + timedelta(minutes=20),
            latitude=19.0760,
            longitude=72.8777,
            temperature=31.5,
            station_id="BOM",
        )

        # Observation recorded 90 minutes later (beyond 60min default window)
        obs_outside = ObservationRecord(
            timestamp=fcst_time + timedelta(minutes=90),
            latitude=19.0760,
            longitude=72.8777,
            temperature=31.5,
            station_id="BOM",
        )

        # Matching with 30min window
        config_30min = MatchingConfig(max_temporal_offset_minutes=30)
        matcher_30 = SpatialTemporalMatcher(config=config_30min)

        matched = matcher_30.match([fcst], [obs_within, obs_outside])
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0].temporal_offset_minutes, 20.0)

    def test_error_calculator_across_all_models(self):
        # Ingest all sample forecast models
        pipeline = IngestionPipeline()
        pipeline.ingest_directory(SAMPLE_DIR)
        fcst_records = pipeline.get_all_records()

        # Ingest observations
        obs_records, _ = self.ingestion_service.load_file(self.obs_csv)

        # Match pairs
        matched = self.matcher.match(fcst_records, obs_records)
        self.assertGreater(len(matched), 500)

        # Compute error summaries
        summary = ForecastErrorCalculator.evaluate_by_model_and_variable(matched)

        # Check that error calculations exist for all models
        models_found = list(summary.keys())
        self.assertTrue(any("NWP Model A" in m for m in models_found))
        self.assertTrue(any("NWP Model B" in m for m in models_found))
        self.assertTrue(any("Ensemble Forecast" in m for m in models_found))
        self.assertTrue(any("AI/ML Forecast" in m for m in models_found))

        # Check metrics properties
        for m_name, var_dict in summary.items():
            for v_name, comp in var_dict.items():
                m = comp.overall_metrics
                self.assertGreater(m.sample_count, 0)
                self.assertGreaterEqual(m.mean_absolute_error, 0.0)
                self.assertGreaterEqual(m.root_mean_square_error, 0.0)
                self.assertTrue(-1.0 <= m.pearson_correlation <= 1.0)
                # Check lead time profiles
                self.assertGreater(len(comp.lead_time_profile), 0)


if __name__ == "__main__":
    unittest.main()
