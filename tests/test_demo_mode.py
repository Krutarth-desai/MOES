"""Unit and Integration Tests for SIH Presentation Demo Mode.
Validates that the 7 sequential stages, deterministic scenarios, model weighting,
IMD alert thresholds, and FastAPI endpoints function correctly and without data fabrication.
"""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.demo.engine import SIHDemoEngine
from backend.app.services.demo.schemas import DemoScenarioId, DemoScenarioResult


class TestSIHDemoMode(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_available_scenarios(self):
        scenarios = SIHDemoEngine.get_available_scenarios()
        self.assertGreaterEqual(len(scenarios), 2)
        scenario_ids = [s["id"] for s in scenarios]
        self.assertIn("monsoon_convective_storm", scenario_ids)
        self.assertIn("severe_heatwave_plains", scenario_ids)

    def test_monsoon_convective_storm_pipeline(self):
        result = SIHDemoEngine.run_scenario(DemoScenarioId.MONSOON_CONVECTIVE_STORM.value)
        self.assertIsInstance(result, DemoScenarioResult)
        self.assertEqual(result.station_id, "BOM")
        self.assertEqual(result.target_variable, "rainfall")
        self.assertEqual(result.unit, "mm")

        # 1. Multiple forecast models provide different predictions
        self.assertEqual(len(result.individual_models), 4)
        vals = [m.forecast_value for m in result.individual_models]
        self.assertGreater(len(set(vals)), 1, "Models must provide different predictions")

        # 2. Sequential processing stages strictly matching the required 7 stages
        stage_ids = [s.stage_id for s in result.stages]
        expected_stage_ids = [
            "DATA_INGESTION",
            "WEATHER_REGIME",
            "MODEL_SKILL",
            "ADAPTIVE_WEIGHTS",
            "FORECAST_BLENDING",
            "EXTREME_EVENT",
            "FINAL_FORECAST",
        ]
        self.assertEqual(stage_ids, expected_stage_ids)

        # 3. Model weights sum strictly to 1.00
        total_weight = sum(m.assigned_weight for m in result.individual_models)
        self.assertAlmostEqual(total_weight, 1.0, places=2)

        # 4. Blended value is mathematically consistent with model predictions & weights
        weighted_sum = sum(m.weighted_contribution for m in result.individual_models)
        self.assertAlmostEqual(result.blended_value, weighted_sum, places=1)

        # 5. Extreme event detection
        self.assertTrue(result.extreme_event_detected)
        self.assertEqual(result.alert_category, "ORANGE")
        self.assertEqual(result.severity_level, "severe")

        # 6. Geographic impact & affected stations
        self.assertIsNotNone(result.geographic_impact)
        self.assertGreaterEqual(len(result.geographic_impact.affected_stations), 3)

        # 7. Explainability
        self.assertIn("NWP Model B received the highest weight", result.explanation_text)
        self.assertIn("NWP Model B", result.weighting_rationale)

        # 8. Empirical skill verification (zero fabrication notice)
        self.assertGreater(result.relative_improvement_pct, 0.0)
        self.assertIn("unseen test partition", result.stages[-1].key_metrics["data_leakage_safeguard"])

    def test_heatwave_scenario_pipeline(self):
        result = SIHDemoEngine.run_scenario(DemoScenarioId.SEVERE_HEATWAVE_PLAINS.value)
        self.assertIsInstance(result, DemoScenarioResult)
        self.assertEqual(result.station_id, "DEL")
        self.assertEqual(result.target_variable, "temperature")
        self.assertEqual(result.unit, "°C")

        # 7 stages
        self.assertEqual(len(result.stages), 7)
        self.assertEqual(result.stages[1].stage_id, "WEATHER_REGIME")
        self.assertEqual(result.alert_category, "RED")
        self.assertTrue(result.blended_value >= 45.0)

    def test_demo_api_endpoints(self):
        # GET /api/demo/scenarios
        resp = self.client.get("/api/demo/scenarios")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("scenarios", data)
        self.assertGreaterEqual(data["total_count"], 2)

        # POST /api/demo/run default
        resp = self.client.post("/api/demo/run", json={"scenario_id": "monsoon_convective_storm"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["scenario_id"], "monsoon_convective_storm")
        self.assertEqual(len(data["stages"]), 7)
        self.assertIn("stages", data)
        self.assertIn("individual_models", data)
        self.assertIn("geographic_impact", data)

        # GET /api/demo/run
        resp = self.client.get("/api/demo/run?scenario_id=severe_heatwave_plains")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["scenario_id"], "severe_heatwave_plains")
        self.assertEqual(data["alert_category"], "RED")


if __name__ == "__main__":
    unittest.main()
