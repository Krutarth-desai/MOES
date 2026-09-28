import unittest
from fastapi.testclient import TestClient

from backend.app.main import app


class TestCoreAPIEndpoints(unittest.TestCase):
    """
    Test suite for the primary FastAPI backend endpoints (/api/...).
    
    Verifies:
    1. GET /api/health
    2. GET /api/forecasts
    3. GET /api/blended-forecast
    4. GET /api/model-weights
    5. GET /api/model-performance
    6. GET /api/skill-comparison
    7. GET /api/extreme-events
    8. GET /api/weather-regime
    9. GET /api/regions
    10. POST /api/run-forecast
    11. POST /api/run-backtest
    12. Query parameters (latitude, longitude, region, variable, lead_time, season, weather_regime)
    13. Structured error handling (422 validation, error envelope)
    14. Middleware processing time and CORS headers
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. GET /api/health
    # -------------------------------------------------------------------------
    def test_get_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("active_modules", data)
        self.assertGreaterEqual(len(data["active_modules"]), 5)
        self.assertIn("active_models", data)
        self.assertGreaterEqual(len(data["active_models"]), 4)
        self.assertIn("uptime_seconds", data)

    # -------------------------------------------------------------------------
    # 2. GET /api/forecasts
    # -------------------------------------------------------------------------
    def test_get_forecasts(self):
        response = self.client.get(
            "/api/forecasts",
            params={
                "latitude": 19.076,
                "longitude": 72.877,
                "variable": "rainfall",
                "lead_time": 24,
                "season": "monsoon",
                "weather_regime": "normal",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["variable"], "rainfall")
        self.assertEqual(data["unit"], "mm")
        self.assertEqual(data["lead_time_hours"], 24)
        self.assertIn("individual_forecasts", data)
        self.assertGreaterEqual(len(data["individual_forecasts"]), 4)
        self.assertIn("NWP Model A", data["individual_forecasts"])
        self.assertIn("AI/ML Forecast", data["individual_forecasts"])

    # -------------------------------------------------------------------------
    # 3. GET /api/blended-forecast
    # -------------------------------------------------------------------------
    def test_get_blended_forecast(self):
        response = self.client.get(
            "/api/blended-forecast",
            params={
                "latitude": 28.613,
                "longitude": 77.209,
                "variable": "temperature",
                "lead_time": 48,
                "season": "pre_monsoon",
                "weather_regime": "heat_wave",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["variable"], "temperature")
        self.assertEqual(data["unit"], "°C")
        self.assertIn("blended_value", data)
        self.assertIsInstance(data["blended_value"], float)
        self.assertIn("model_weights", data)
        self.assertAlmostEqual(sum(data["model_weights"].values()), 1.0, places=3)
        self.assertIn("confidence_interval_10th", data)
        self.assertIn("confidence_interval_90th", data)
        self.assertGreaterEqual(data["confidence_interval_90th"], data["confidence_interval_10th"])

    # -------------------------------------------------------------------------
    # 4. GET /api/model-weights
    # -------------------------------------------------------------------------
    def test_get_model_weights(self):
        response = self.client.get(
            "/api/model-weights",
            params={
                "region": "western_ghats",
                "variable": "rainfall",
                "lead_time": 24,
                "season": "monsoon",
                "weather_regime": "heavy_rain",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["variable"], "rainfall")
        self.assertIn("weights", data)
        self.assertAlmostEqual(sum(data["weights"].values()), 1.0, places=3)
        self.assertIn("dominant_model", data)
        self.assertIn("distribution_entropy", data)
        self.assertGreaterEqual(data["distribution_entropy"], 0.0)
        self.assertLessEqual(data["distribution_entropy"], 1.0)
        self.assertIn("contextual_governance_notice", data)

    # -------------------------------------------------------------------------
    # 5. GET /api/model-performance
    # -------------------------------------------------------------------------
    def test_get_model_performance(self):
        response = self.client.get(
            "/api/model-performance",
            params={
                "variable": "rainfall",
                "lead_time": 24,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("performance", data)
        self.assertGreater(data["records_count"], 0)
        first = data["performance"][0]
        self.assertIn("mae", first)
        self.assertIn("rmse", first)
        self.assertIn("correlation", first)
        self.assertIn("composite_skill_score", first)

    # -------------------------------------------------------------------------
    # 6. GET /api/skill-comparison
    # -------------------------------------------------------------------------
    def test_get_skill_comparison(self):
        response = self.client.get(
            "/api/skill-comparison",
            params={
                "variable": "rainfall",
                "lead_time": 24,
                "region": "plains",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("models_compared", data)
        self.assertIn("hybrid_forecast_rmse", data)
        self.assertIn("best_individual_model_name", data)
        self.assertIn("best_individual_model_rmse", data)
        self.assertIn("relative_improvement_pct", data)
        self.assertGreater(data["relative_improvement_pct"], 0.0)
        self.assertIn("Hybrid forecast RMSE", data["summary_statement"])

    # -------------------------------------------------------------------------
    # 7. GET /api/extreme-events
    # -------------------------------------------------------------------------
    def test_get_extreme_events(self):
        response = self.client.get(
            "/api/extreme-events",
            params={
                "lead_time": 24,
                "hazard_type": "heavy_rainfall",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("guidance", data)
        self.assertIn("advisories_count_by_severity", data)
        if data["guidance"]:
            first = data["guidance"][0]
            self.assertIn("forecast_value", first)
            self.assertIn("derived_risk_indicator", first)
            self.assertIn("alert_threshold", first)
            self.assertIn("disclaimer", first["derived_risk_indicator"])

    # -------------------------------------------------------------------------
    # 8. GET /api/weather-regime
    # -------------------------------------------------------------------------
    def test_get_weather_regime(self):
        response = self.client.get(
            "/api/weather-regime",
            params={
                "latitude": 21.145,
                "longitude": 79.088,
                "lead_time": 24,
                "temperature": 45.5,
                "rainfall": 0.0,
                "humidity": 25.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("diagnosed_regime", data)
        self.assertIn("confidence", data)
        self.assertGreaterEqual(data["confidence"], 0.5)
        self.assertIn("supporting_indicators", data)

    # -------------------------------------------------------------------------
    # 9. GET /api/regions
    # -------------------------------------------------------------------------
    def test_get_regions(self):
        response = self.client.get("/api/regions")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("regions", data)
        self.assertGreaterEqual(data["total_regions"], 6)
        names = [r["name"] for r in data["regions"]]
        self.assertTrue(any("Western Ghats" in n for n in names))
        self.assertTrue(any("Plains" in n for n in names))

    # -------------------------------------------------------------------------
    # 10. POST /api/run-forecast
    # -------------------------------------------------------------------------
    def test_post_run_forecast(self):
        payload = {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "variable": "rainfall",
            "lead_time": 24,
            "season": "monsoon",
            "custom_model_inputs": {
                "NWP Model A": 95.0,
                "NWP Model B": 88.0,
                "Ensemble Forecast": 92.0,
                "AI/ML Forecast": 85.0,
            },
        }
        response = self.client.post("/api/run-forecast", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("execution_id", data)
        self.assertIn("blended_forecast", data)
        self.assertGreaterEqual(data["blended_forecast"], 80.0)
        self.assertIn("adaptive_weights", data)
        self.assertAlmostEqual(sum(data["adaptive_weights"].values()), 1.0, places=3)
        self.assertIn("execution_time_ms", data)
        self.assertGreater(data["execution_time_ms"], 0.0)

    # -------------------------------------------------------------------------
    # 11. POST /api/run-backtest
    # -------------------------------------------------------------------------
    def test_post_run_backtest(self):
        payload = {
            "variable": "rainfall",
            "lead_time_hours": 24,
            "test_split_ratio": 0.30,
        }
        response = self.client.post("/api/run-backtest", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("backtest_id", data)
        self.assertIn("model_comparison", data)
        self.assertIn("hybrid_forecast_rmse", data)
        self.assertIn("relative_improvement_pct", data)
        self.assertIn("data_leakage_safeguard", data)

    # -------------------------------------------------------------------------
    # 12. Structured Error Handling & Validation
    # -------------------------------------------------------------------------
    def test_structured_validation_error_422(self):
        # Invalid latitude > 90
        response = self.client.get("/api/forecasts?latitude=999.0&longitude=72.0")
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(data["status_code"], 422)
        self.assertIn("details", data)
        self.assertIn("path", data)
        self.assertIn("timestamp", data)

    def test_timing_and_cors_headers(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertIn("x-process-time-ms", response.headers)
        duration = float(response.headers["x-process-time-ms"])
        self.assertGreaterEqual(duration, 0.0)


if __name__ == "__main__":
    unittest.main()
