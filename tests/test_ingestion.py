import unittest
from pathlib import Path
from backend.app.data.ingestion.schema import (
    ForecastVariable,
    QualityFlag,
    Season,
)
from backend.app.data.ingestion.normalizer import UnitNormalizer
from backend.app.data.ingestion.validator import RecordValidator
from backend.app.data.ingestion.sources.csv_source import CSVForecastSource
from backend.app.data.ingestion.sources.json_source import JSONForecastSource
from backend.app.data.ingestion.pipeline import IngestionPipeline

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample"


class TestUnitNormalizer(unittest.TestCase):
    def test_temperature_kelvin_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.TEMPERATURE, 308.15, "K")
        self.assertAlmostEqual(val, 35.0, places=1)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "UNIT_CONVERSION")
        self.assertEqual(issue.action_taken, "CONVERTED")

    def test_temperature_fahrenheit_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.TEMPERATURE, 68.0, "F")
        self.assertAlmostEqual(val, 20.0, places=1)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "UNIT_CONVERSION")

    def test_rainfall_inches_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.RAINFALL, 2.5, "in")
        self.assertAlmostEqual(val, 63.5, places=1)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "UNIT_CONVERSION")

    def test_rainfall_meters_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.RAINFALL, 0.025, "m")
        self.assertAlmostEqual(val, 25.0, places=1)
        self.assertIsNotNone(issue)

    def test_rainfall_negative_clamping(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.RAINFALL, -5.0, "mm")
        self.assertEqual(val, 0.0)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "PHYSICAL_VIOLATION")
        self.assertEqual(issue.action_taken, "CLAMPED")

    def test_wind_speed_knots_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.WIND_SPEED, 30.0, "kt")
        self.assertAlmostEqual(val, 55.56, places=1)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.issue_type, "UNIT_CONVERSION")

    def test_wind_speed_mps_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.WIND_SPEED, 10.0, "m/s")
        self.assertAlmostEqual(val, 36.0, places=1)
        self.assertIsNotNone(issue)

    def test_wind_direction_compass_conversion(self):
        val, issue = UnitNormalizer.normalize_value(ForecastVariable.WIND_DIRECTION, "SW", None)
        self.assertEqual(val, 225.0)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.action_taken, "CONVERTED")


class TestRecordValidator(unittest.TestCase):
    def test_missing_value_imputation(self):
        raw = {
            "forecast_variable": "rainfall",
            "forecast_value": None,  # Missing
            "latitude": 19.07,
            "longitude": 72.87,
            "lead_time": 24,
            "initialization_time": "2026-07-15T00:00:00Z",
        }
        record, issues = RecordValidator.validate_and_clean_record(raw, row_index=1)
        self.assertIsNotNone(record)
        self.assertEqual(record.quality_flag, QualityFlag.IMPUTED)
        self.assertEqual(record.forecast_value, 0.0)
        self.assertTrue(any(i.issue_type == "MISSING_VALUE" for i in issues))

    def test_out_of_bounds_coordinate_rejection(self):
        raw = {
            "forecast_variable": "temperature",
            "forecast_value": 25.0,
            "latitude": 125.0,  # Invalid latitude
            "longitude": 75.0,
        }
        record, issues = RecordValidator.validate_and_clean_record(raw, row_index=2)
        self.assertIsNone(record)
        self.assertTrue(any(i.issue_type == "OUT_OF_BOUNDS" for i in issues))

    def test_derived_timestamp_consistency(self):
        raw = {
            "forecast_variable": "temperature",
            "forecast_value": 30.0,
            "latitude": 28.61,
            "longitude": 77.20,
            "initialization_time": "2026-07-15T00:00:00Z",
            "lead_time": 48,
        }
        record, issues = RecordValidator.validate_and_clean_record(raw, row_index=3)
        self.assertIsNotNone(record)
        # Timestamp should equal init + 48h -> 2026-07-17 00:00:00
        expected_ts = record.initialization_time + (record.lead_time_hours * record.timestamp.resolution * 3600)
        self.assertEqual(record.timestamp.day, 17)


class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = IngestionPipeline()

    def test_ingest_nwp_model_a_csv(self):
        csv_file = SAMPLE_DIR / "nwp_model_a.csv"
        records, report = self.pipeline.ingest_file(csv_file, source_key="nwp_model_a")

        self.assertGreater(len(records), 200)
        self.assertEqual(report.total_records_read, len(records) + report.rejected_records_count)
        self.assertGreater(report.valid_records_count, 200)

        # Check that Kelvin conversion occurred
        kelvin_issues = [i for i in report.issues if i.original_value == 308.15]
        self.assertGreater(len(kelvin_issues), 0)
        self.assertEqual(kelvin_issues[0].resolved_value, 35.0)

        # Check that negative rain was clamped
        clamped_issues = [i for i in report.issues if i.original_value == -4.5]
        self.assertGreater(len(clamped_issues), 0)
        self.assertEqual(clamped_issues[0].resolved_value, 0.0)

    def test_ingest_nwp_model_b_csv(self):
        csv_file = SAMPLE_DIR / "nwp_model_b.csv"
        records, report = self.pipeline.ingest_file(csv_file, source_key="nwp_model_b")

        self.assertGreater(len(records), 200)
        # Check that knots conversion occurred
        knot_issues = [i for i in report.issues if i.original_value == 30.0 and i.action_taken == "CONVERTED"]
        self.assertGreater(len(knot_issues), 0)
        self.assertAlmostEqual(knot_issues[0].resolved_value, 55.56, places=1)

    def test_ingest_ensemble_csv(self):
        csv_file = SAMPLE_DIR / "ensemble_forecast.csv"
        records, report = self.pipeline.ingest_file(csv_file, source_key="ensemble_forecast")

        self.assertGreater(len(records), 200)
        # Check that missing value imputation was recorded
        self.assertGreaterEqual(report.imputed_records_count, 1)

    def test_ingest_ai_forecast_json(self):
        json_file = SAMPLE_DIR / "ai_forecast.json"
        records, report = self.pipeline.ingest_file(json_file, source_key="ai_forecast")

        self.assertGreater(len(records), 200)
        # Check that inches conversion occurred
        inch_issues = [i for i in report.issues if i.original_value == 2.5]
        self.assertGreater(len(inch_issues), 0)
        self.assertEqual(inch_issues[0].resolved_value, 63.5)

        # Check compass conversion occurred
        sw_issues = [i for i in report.issues if i.original_value == "SW"]
        self.assertGreater(len(sw_issues), 0)
        self.assertEqual(sw_issues[0].resolved_value, 225.0)

    def test_pipeline_query_filters(self):
        self.pipeline.ingest_file(SAMPLE_DIR / "nwp_model_a.csv", source_key="nwp_model_a")
        self.pipeline.ingest_file(SAMPLE_DIR / "ai_forecast.json", source_key="ai_forecast")

        # Query rainfall at T+24h
        rain_24 = self.pipeline.query_records(
            variable=ForecastVariable.RAINFALL,
            lead_time_hours=24,
        )
        self.assertGreater(len(rain_24), 0)
        for r in rain_24:
            self.assertEqual(r.forecast_variable, ForecastVariable.RAINFALL)
            self.assertEqual(r.lead_time_hours, 24)
            self.assertGreaterEqual(r.forecast_value, 0.0)

    def test_ingest_entire_directory(self):
        self.pipeline.clear()
        reports = self.pipeline.ingest_directory(SAMPLE_DIR)
        self.assertEqual(len(reports), 5)  # 4 models + 1 ground truth

        all_records = self.pipeline.get_all_records()
        self.assertGreater(len(all_records), 1000)


if __name__ == "__main__":
    unittest.main()
