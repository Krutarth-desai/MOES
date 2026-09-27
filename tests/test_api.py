import unittest
from fastapi.testclient import TestClient
from backend.app.main import app


class TestAPIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_root_endpoint(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("active_models", data)

    def test_stations_endpoint(self):
        response = self.client.get("/api/v1/forecast/stations")
        self.assertEqual(response.status_code, 200)
        stations = response.json()
        self.assertGreaterEqual(len(stations), 5)
        station_names = [s["name"] for s in stations]
        self.assertTrue(any("Mumbai" in name for name in station_names))

    def test_point_forecast_endpoint(self):
        response = self.client.get("/api/v1/forecast/point?station_id=BOM&variable=precipitation")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["station_id"], "BOM")
        self.assertGreater(len(data["time_series"]), 0)
        self.assertIn("blended_value", data["time_series"][0])

    def test_weights_endpoint(self):
        response = self.client.get("/api/v1/weights/map?lead_time_hours=48")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["regional_weights"]), 0)

    def test_alerts_endpoint(self):
        response = self.client.get("/api/v1/extremes/alerts?lead_time_hours=24")
        self.assertEqual(response.status_code, 200)
        alerts = response.json()
        self.assertIsInstance(alerts, list)

    def test_metrics_endpoint(self):
        response = self.client.get("/api/v1/metrics/skill-score?lead_time_hours=48")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("mae_improvement_pct", data)
        self.assertGreater(data["mae_improvement_pct"], 0)

    def test_ingestion_records_endpoint(self):
        response = self.client.get("/api/v1/ingestion/records?limit=10")
        self.assertEqual(response.status_code, 200)
        records = response.json()
        self.assertGreater(len(records), 0)
        first = records[0]
        self.assertIn("timestamp", first)
        self.assertIn("latitude", first)
        self.assertIn("longitude", first)
        self.assertIn("forecast_variable", first)
        self.assertIn("forecast_value", first)
        self.assertIn("initialization_time", first)
        self.assertIn("lead_time_hours", first)
        self.assertIn("source_name", first)
        self.assertIn("region", first)
        self.assertIn("season", first)

    def test_observation_records_endpoint(self):
        response = self.client.get("/api/v1/observations/records?limit=10")
        self.assertEqual(response.status_code, 200)
        records = response.json()
        self.assertGreater(len(records), 0)
        first = records[0]
        self.assertIn("timestamp", first)
        self.assertIn("temperature", first)
        self.assertIn("rainfall", first)
        self.assertIn("wind_speed", first)
        self.assertIn("wind_direction", first)

    def test_observation_match_and_errors_endpoints(self):
        match_resp = self.client.post("/api/v1/observations/match?limit=10")
        self.assertEqual(match_resp.status_code, 200)
        matched = match_resp.json()
        self.assertGreater(len(matched), 0)
        self.assertIn("error", matched[0])
        self.assertIn("absolute_error", matched[0])

        err_resp = self.client.get("/api/v1/observations/errors")
        self.assertEqual(err_resp.status_code, 200)
        summary = err_resp.json()
        self.assertGreater(len(summary), 0)

    def test_verification_engine_endpoints(self):
        # 1. Recalculate
        recalc_resp = self.client.post("/api/v1/verification/recalculate")
        self.assertEqual(recalc_resp.status_code, 200)
        self.assertEqual(recalc_resp.json()["status"], "success")

        # 2. Overall
        overall_resp = self.client.get("/api/v1/verification/overall?variable=rainfall")
        self.assertEqual(overall_resp.status_code, 200)
        overall_data = overall_resp.json()
        self.assertEqual(overall_data["variable"], "rainfall")
        self.assertGreater(len(overall_data["models"]), 0)

        # 3. By Lead Time
        lead_resp = self.client.get("/api/v1/verification/by-lead-time?variable=temperature&model_name=NWP Model A")
        self.assertEqual(lead_resp.status_code, 200)
        lead_data = lead_resp.json()
        self.assertGreater(len(lead_data["lead_time_profile"]), 0)

        # 4. By Region
        region_resp = self.client.get("/api/v1/verification/by-region?variable=rainfall&model_name=NWP Model B")
        self.assertEqual(region_resp.status_code, 200)
        region_data = region_resp.json()
        self.assertGreater(len(region_data["regional_profile"]), 0)

        # 5. By Season
        season_resp = self.client.get("/api/v1/verification/by-season?variable=rainfall&model_name=NWP Model A")
        self.assertEqual(season_resp.status_code, 200)
        season_data = season_resp.json()
        self.assertGreater(len(season_data["seasonal_profile"]), 0)

        # 6. By Regime
        regime_resp = self.client.get("/api/v1/verification/by-regime?variable=rainfall&model_name=NWP Model A")
        self.assertEqual(regime_resp.status_code, 200)
        regime_data = regime_resp.json()
        self.assertGreater(len(regime_data["regime_profile"]), 0)

    def test_regime_classification_endpoints(self):
        # 1. Current Synoptic
        curr_resp = self.client.get("/api/v1/regimes/current")
        self.assertEqual(curr_resp.status_code, 200)
        self.assertIn("active_regime", curr_resp.json())

        # 2. Supported Regimes List
        types_resp = self.client.get("/api/v1/regimes/types")
        self.assertEqual(types_resp.status_code, 200)
        regimes_list = types_resp.json()["supported_regimes"]
        self.assertEqual(len(regimes_list), 7)

        # 3. Dynamic Classification
        classify_resp = self.client.post(
            "/api/v1/regimes/classify",
            json={"temperature": 28.0, "rainfall": 85.0, "wind_speed": 25.0}
        )
        self.assertEqual(classify_resp.status_code, 200)
        res = classify_resp.json()
        self.assertEqual(res["regime"], "Heavy Rain")
        self.assertEqual(res["regime_name"], "Heavy Rain")
        self.assertGreater(len(res["supporting_indicators"]), 0)
        self.assertGreaterEqual(res["confidence"], 0.80)

        # 4. Stations Regime Snapshot
        st_resp = self.client.get("/api/v1/regimes/stations")
        self.assertEqual(st_resp.status_code, 200)
        self.assertIn("BOM", st_resp.json())


if __name__ == "__main__":
    unittest.main()

