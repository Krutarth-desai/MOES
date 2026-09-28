import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.explainability.engine import ForecastExplainabilityEngine
from backend.app.services.verification.store import SkillScoreStore


class TestForecastExplainability(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.skill_store = SkillScoreStore()
        self.engine = ForecastExplainabilityEngine(skill_store=self.skill_store)

    def test_generate_explanation_structure(self):
        weights = {
            "NWP Model A": 0.46,
            "NWP Model B": 0.31,
            "AI/ML Forecast": 0.23,
        }
        exp = self.engine.generate_explanation(
            variable="rainfall",
            lead_time_hours=24,
            selected_weights=weights,
            region="Western Ghats & Coastal",
            season="monsoon",
            weather_regime="heavy_rain",
        )

        # 1. Verify required fields
        self.assertEqual(exp.variable, "rainfall")
        self.assertEqual(exp.lead_time_hours, 24)
        self.assertEqual(exp.current_weather_regime, "heavy_rain")
        self.assertEqual(exp.season, "monsoon")
        self.assertEqual(exp.dominant_model, "NWP Model A")
        self.assertAlmostEqual(exp.dominant_weight, 0.46, places=2)

        # 2. Verify summary text format conforms to specification
        self.assertIn("Rainfall forecast for Western Ghats & Coastal at 24-hour lead:", exp.summary_text)
        self.assertIn("NWP Model A weight = 0.46", exp.summary_text)
        self.assertIn("NWP Model B weight = 0.31", exp.summary_text)
        self.assertIn("AI/ML Forecast weight = 0.23", exp.summary_text)
        self.assertIn("NWP Model A received the highest weight because", exp.summary_text)

        # 3. Verify historical skill used includes all participating models with real metrics
        self.assertIn("NWP Model A", exp.historical_skill_used)
        self.assertIn("NWP Model B", exp.historical_skill_used)
        self.assertIn("AI/ML Forecast", exp.historical_skill_used)
        for m, skill in exp.historical_skill_used.items():
            self.assertGreater(skill.rmse, 0)
            self.assertGreater(skill.sample_size, 0)
            self.assertIsNotNone(skill.correlation)

        # 4. Verify decision factors and plain-language summary for non-technical judges
        self.assertGreaterEqual(len(exp.decision_factors), 3)
        self.assertIn("NWP Model A", exp.non_technical_summary)
        self.assertIn("heavy_rain", exp.non_technical_summary)

    def test_api_forecast_explanation_endpoint(self):
        response = self.client.get(
            "/api/forecast-explanation",
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
        self.assertIn("summary_text", data)
        self.assertIn("historical_skill_used", data)
        self.assertIn("selected_weights", data)
        self.assertEqual(data["current_weather_regime"], "heavy_rain")
        self.assertEqual(data["lead_time_hours"], 24)
        self.assertIn("dominant_model", data)
        self.assertIn("dominant_reason", data)

    def test_blended_forecast_includes_explanation(self):
        response = self.client.get(
            "/api/blended-forecast",
            params={
                "latitude": 19.076,
                "longitude": 72.877,
                "variable": "rainfall",
                "lead_time": 24,
                "season": "monsoon",
                "weather_regime": "heavy_rain",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("explanation", data)
        exp = data["explanation"]
        self.assertIsNotNone(exp)
        self.assertIn("summary_text", exp)
        self.assertIn("historical_skill_used", exp)
        self.assertEqual(exp["current_weather_regime"], "heavy_rain")
        self.assertEqual(exp["lead_time_hours"], 24)

    def test_model_weights_includes_detailed_explanation(self):
        response = self.client.get(
            "/api/model-weights",
            params={
                "region": "western_ghats",
                "variable": "temperature",
                "lead_time": 48,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("detailed_explanation", data)
        self.assertIsNotNone(data["detailed_explanation"])
        self.assertIn("summary_text", data["detailed_explanation"])
        self.assertEqual(data["detailed_explanation"]["variable"], "temperature")


if __name__ == "__main__":
    unittest.main()
