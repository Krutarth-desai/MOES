import unittest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.extremes.engine import ExtremeWeatherGuidanceEngine
from backend.app.services.extremes.scenarios import ExtremeScenarioProvider
from backend.app.services.extremes.schemas import (
    AlertCategory,
    ExtremeEventType,
    PointEvaluationRequest,
    RegionalThresholdConfig,
    SeverityLevel,
    ThresholdLevelConfig,
)
from backend.app.services.extremes.thresholds import ExtremeThresholdRegistry


class TestExtremeThresholdRegistry(unittest.TestCase):
    """
    Tests configurable and region-aware threshold logic.
    """

    def setUp(self):
        self.registry = ExtremeThresholdRegistry()

    def test_default_imd_thresholds(self):
        # Default Heavy Rain: Yellow=15.6, Orange=64.5, Red=115.6
        levels, desc = self.registry.get_thresholds(ExtremeEventType.HEAVY_RAINFALL, "default")
        self.assertEqual(levels.yellow_threshold, 15.6)
        self.assertEqual(levels.orange_threshold, 64.5)
        self.assertEqual(levels.red_threshold, 115.6)
        self.assertEqual(levels.unit, "mm")

    def test_region_specific_rainfall_thresholds(self):
        # Western Ghats has higher orographic baseline tolerance
        levels_wg, _ = self.registry.get_thresholds(ExtremeEventType.HEAVY_RAINFALL, "western_ghats")
        self.assertEqual(levels_wg.orange_threshold, 75.0)
        self.assertEqual(levels_wg.red_threshold, 125.0)

        # Hills has lower threshold due to flash flood & landslide risk
        levels_hills, _ = self.registry.get_thresholds(ExtremeEventType.HEAVY_RAINFALL, "hills")
        self.assertEqual(levels_hills.orange_threshold, 50.0)
        self.assertEqual(levels_hills.red_threshold, 90.0)

    def test_region_specific_heatwave_thresholds(self):
        # Plains standard: 40°C, 42°C, 45°C
        levels_plains, _ = self.registry.get_thresholds(ExtremeEventType.HEAT_WAVE, "plains")
        self.assertEqual(levels_plains.yellow_threshold, 40.0)
        self.assertEqual(levels_plains.orange_threshold, 42.0)
        self.assertEqual(levels_plains.red_threshold, 45.0)

        # Coastal zone: 36°C, 37.5°C, 40°C (due to high humidity heat index)
        levels_coastal, _ = self.registry.get_thresholds(ExtremeEventType.HEAT_WAVE, "coastal")
        self.assertEqual(levels_coastal.orange_threshold, 37.5)
        self.assertEqual(levels_coastal.red_threshold, 40.0)

    def test_custom_threshold_override_and_reset(self):
        custom_levels = ThresholdLevelConfig(
            yellow_threshold=25.0,
            orange_threshold=75.0,
            red_threshold=130.0,
            unit="mm",
            description="Custom Project Override",
        )
        self.registry.set_custom_threshold(ExtremeEventType.HEAVY_RAINFALL, "special_zone", custom_levels)

        retrieved, desc = self.registry.get_thresholds(ExtremeEventType.HEAVY_RAINFALL, "special_zone")
        self.assertEqual(retrieved.orange_threshold, 75.0)

        # Reset to defaults
        self.registry.reset_to_defaults()
        levels_after_reset, _ = self.registry.get_thresholds(ExtremeEventType.HEAVY_RAINFALL, "special_zone")
        # Should fall back to default
        self.assertEqual(levels_after_reset.orange_threshold, 64.5)


class TestExtremeWeatherGuidanceEngine(unittest.TestCase):
    """
    Tests event detection, severity calculation, risk indicators,
    and strict separation between forecast value, risk score, and threshold.
    """

    def setUp(self):
        self.registry = ExtremeThresholdRegistry()
        self.engine = ExtremeWeatherGuidanceEngine(registry=self.registry)

    def test_heavy_rainfall_detection_and_distinctions(self):
        """
        Verify detection and strict separation:
        - forecast_value
        - derived_risk_indicator
        - alert_threshold
        """
        model_forecasts = {
            "NWP Model A": 125.0,
            "NWP Model B": 118.0,
            "Ensemble Forecast": 120.0,
            "AI Forecast": 122.0,
        }
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAVY_RAINFALL,
            forecast_value=121.0,
            location_name="Mumbai",
            affected_region="plains",
            latitude=19.07,
            longitude=72.87,
            lead_time_hours=24,
            station_id="BOM",
            model_forecasts=model_forecasts,
        )

        # 1. Physical Forecast Value
        self.assertEqual(guidance.forecast_value, 121.0)
        self.assertEqual(guidance.forecast_unit, "mm")

        # 2. Alert Threshold Applied
        self.assertEqual(guidance.alert_threshold.applied_threshold, 115.6)
        self.assertEqual(guidance.alert_threshold.alert_category, AlertCategory.RED)
        self.assertIn("red", guidance.alert_threshold.all_threshold_levels)

        # 3. Derived Risk Indicator (Separated & Disclaimed)
        risk = guidance.derived_risk_indicator
        self.assertGreaterEqual(risk.probability_score, 0.8)
        self.assertGreaterEqual(risk.composite_risk_score, 70.0)
        self.assertEqual(risk.risk_level, "Critical")
        self.assertIn("not a guaranteed deterministic outcome", risk.disclaimer)

        # 4. Severity & Category
        self.assertEqual(guidance.severity_level, SeverityLevel.EXTREME)
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)

        # 5. Timing
        self.assertTrue(guidance.expected_start_time.endswith("Z"))
        self.assertTrue(guidance.expected_end_time.endswith("Z"))

        # 6. Contributing models
        self.assertEqual(len(guidance.contributing_models), 4)
        self.assertGreater(guidance.confidence, 0.70)

    def test_heat_wave_detection(self):
        """
        Verify heat wave detection in plains.
        """
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAT_WAVE,
            forecast_value=45.5,
            location_name="Nagpur",
            affected_region="plains",
            latitude=21.14,
            longitude=79.08,
            lead_time_hours=48,
            station_id="NAG",
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)
        self.assertEqual(guidance.severity_level, SeverityLevel.EXTREME)
        self.assertEqual(guidance.forecast_unit, "°C")
        self.assertIn("HEATWAVE", guidance.advisory_headline.upper())
        self.assertGreater(len(guidance.recommended_actions), 0)

    def test_high_wind_detection(self):
        """
        Verify gale wind detection in coastal area.
        """
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HIGH_WIND,
            forecast_value=65.0,
            location_name="Puri",
            affected_region="coastal",
            latitude=19.81,
            longitude=85.83,
            lead_time_hours=24,
        )
        # Coastal orange threshold is 60 km/h, red is 80 km/h -> ORANGE alert
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.ORANGE)
        self.assertEqual(guidance.severity_level, SeverityLevel.SEVERE)
        self.assertEqual(guidance.forecast_unit, "km/h")
        self.assertIn("HIGH WIND", guidance.advisory_headline.upper())

    def test_cold_wave_detection(self):
        """
        Verify cold wave detection where lower values mean higher severity.
        """
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.COLD_WAVE,
            forecast_value=3.5,
            location_name="Hisar",
            affected_region="plains",
            latitude=29.15,
            longitude=75.72,
            lead_time_hours=24,
        )
        # Plains cold wave: <= 4°C is RED
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)
        self.assertEqual(guidance.severity_level, SeverityLevel.EXTREME)

    def test_benign_normal_conditions(self):
        """
        Calm weather triggers GREEN category / NONE severity.
        """
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAVY_RAINFALL,
            forecast_value=2.0,
            location_name="Bengaluru",
            affected_region="plains",
            latitude=12.97,
            longitude=77.59,
            lead_time_hours=24,
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.GREEN)
        self.assertEqual(guidance.severity_level, SeverityLevel.NONE)
        self.assertLess(guidance.derived_risk_indicator.composite_risk_score, 25.0)


class TestExtremeScenarios(unittest.TestCase):
    """
    Tests pre-packaged demonstration scenarios:
    - Heavy rainfall
    - Heat wave
    - High wind
    - Normal conditions
    """

    def setUp(self):
        self.engine = ExtremeWeatherGuidanceEngine()

    def test_all_four_scenarios_available(self):
        scenarios = ExtremeScenarioProvider.get_all_scenarios()
        self.assertEqual(len(scenarios), 4)
        categories = {s.category for s in scenarios}
        self.assertEqual(categories, {"heavy_rainfall", "heat_wave", "high_wind", "normal_conditions"})

    def test_heavy_rainfall_scenario(self):
        sc = ExtremeScenarioProvider.get_scenario_by_name("heavy_rainfall")
        self.assertIsNotNone(sc)
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAVY_RAINFALL,
            forecast_value=sc.blended_value,
            location_name=sc.location_name,
            affected_region=sc.region,
            latitude=19.0,
            longitude=73.0,
            station_id=sc.station_id,
            model_forecasts=sc.model_forecasts,
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)
        self.assertEqual(guidance.severity_level, SeverityLevel.EXTREME)

    def test_heat_wave_scenario(self):
        sc = ExtremeScenarioProvider.get_scenario_by_name("heat_wave")
        self.assertIsNotNone(sc)
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAT_WAVE,
            forecast_value=sc.blended_value,
            location_name=sc.location_name,
            affected_region=sc.region,
            latitude=21.0,
            longitude=79.0,
            station_id=sc.station_id,
            model_forecasts=sc.model_forecasts,
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)
        self.assertEqual(guidance.severity_level, SeverityLevel.EXTREME)

    def test_high_wind_scenario(self):
        sc = ExtremeScenarioProvider.get_scenario_by_name("high_wind")
        self.assertIsNotNone(sc)
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HIGH_WIND,
            forecast_value=sc.blended_value,
            location_name=sc.location_name,
            affected_region=sc.region,
            latitude=20.0,
            longitude=86.0,
            station_id=sc.station_id,
            model_forecasts=sc.model_forecasts,
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.RED)

    def test_normal_conditions_scenario(self):
        sc = ExtremeScenarioProvider.get_scenario_by_name("normal_conditions")
        self.assertIsNotNone(sc)
        guidance = self.engine.evaluate_point(
            event_type=ExtremeEventType.HEAVY_RAINFALL,
            forecast_value=sc.blended_value,
            location_name=sc.location_name,
            affected_region=sc.region,
            latitude=13.0,
            longitude=77.0,
            station_id=sc.station_id,
            model_forecasts=sc.model_forecasts,
        )
        self.assertEqual(guidance.recommended_alert_category, AlertCategory.GREEN)
        self.assertEqual(guidance.severity_level, SeverityLevel.NONE)


class TestExtremeWeatherAPIEndpoints(unittest.TestCase):
    """
    Tests FastAPI endpoints under /api/v1/extremes:
    - GET /guidance
    - POST /evaluate
    - GET /thresholds
    - PUT /thresholds
    - POST /thresholds/reset
    - GET /scenarios
    - GET /scenarios/{name}
    - GET /alerts (backward compatibility)
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_get_guidance_endpoint(self):
        response = self.client.get("/api/v1/extremes/guidance?lead_time_hours=24")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        first = data[0]
        self.assertIn("forecast_value", first)
        self.assertIn("derived_risk_indicator", first)
        self.assertIn("alert_threshold", first)
        self.assertIn("probability_score", first["derived_risk_indicator"])
        self.assertIn("disclaimer", first["derived_risk_indicator"])
        self.assertIn("applied_threshold", first["alert_threshold"])

    def test_post_evaluate_endpoint(self):
        payload = {
            "station_id": "BOM",
            "region": "western_ghats",
            "lead_time_hours": 24,
            "rainfall": 140.0,
            "model_forecasts": {
                "NWP Model A": 145.0,
                "NWP Model B": 138.0,
                "Ensemble Forecast": 140.0,
            }
        }
        response = self.client.post("/api/v1/extremes/evaluate", json=payload)
        self.assertEqual(response.status_code, 200)
        items = response.json()
        self.assertGreaterEqual(len(items), 1)
        rain_item = items[0]
        self.assertEqual(rain_item["event_type"], "heavy_rainfall")
        self.assertEqual(rain_item["recommended_alert_category"], "red")
        self.assertEqual(rain_item["severity_level"], "extreme")
        self.assertEqual(rain_item["forecast_value"], 140.0)

    def test_get_and_put_thresholds_endpoints(self):
        # 1. Get thresholds
        get_resp = self.client.get("/api/v1/extremes/thresholds")
        self.assertEqual(get_resp.status_code, 200)
        data = get_resp.json()
        self.assertIn("heavy_rainfall", data)

        # 2. Put custom threshold
        put_payload = {
            "hazard_type": "heavy_rainfall",
            "region": "custom_basin",
            "levels": {
                "yellow_threshold": 30.0,
                "orange_threshold": 90.0,
                "red_threshold": 160.0,
                "unit": "mm",
                "description": "API Test Override",
            }
        }
        put_resp = self.client.put("/api/v1/extremes/thresholds", json=put_payload)
        self.assertEqual(put_resp.status_code, 200)
        self.assertEqual(put_resp.json()["status"], "success")

        # 3. Reset thresholds
        reset_resp = self.client.post("/api/v1/extremes/thresholds/reset")
        self.assertEqual(reset_resp.status_code, 200)

    def test_scenarios_endpoints(self):
        # 1. List scenarios
        resp = self.client.get("/api/v1/extremes/scenarios")
        self.assertEqual(resp.status_code, 200)
        scenarios = resp.json()
        self.assertEqual(len(scenarios), 4)

        # 2. Get specific scenario
        resp_single = self.client.get("/api/v1/extremes/scenarios/heavy_rainfall")
        self.assertEqual(resp_single.status_code, 200)
        single = resp_single.json()
        self.assertEqual(single["category"], "heavy_rainfall")
        self.assertIn("guidance", single)
        self.assertEqual(single["guidance"]["recommended_alert_category"], "red")

        # 3. Invalid scenario name -> 404
        resp_404 = self.client.get("/api/v1/extremes/scenarios/non_existent_hazard")
        self.assertEqual(resp_404.status_code, 404)

    def test_backward_compatible_alerts_endpoint(self):
        response = self.client.get("/api/v1/extremes/alerts?lead_time_hours=24")
        self.assertEqual(response.status_code, 200)
        alerts = response.json()
        self.assertIsInstance(alerts, list)


if __name__ == "__main__":
    unittest.main()
