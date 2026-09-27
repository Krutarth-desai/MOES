import math
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.blending.engine import ForecastBlendingEngine, PHYSICAL_LIMITS
from backend.app.services.blending.schemas import (
    BlendedForecastResult,
    BlendingMethod,
    ForecastBlendRequest,
    ModelContribution,
)
from backend.app.services.blending.store import BlendedForecastStore
from backend.app.services.blending.vector_math import (
    circular_dispersion_and_confidence,
    circular_mean_degrees,
)


class TestVectorMath(unittest.TestCase):
    """
    Tests circular / trigonometric vector averaging for wind direction.
    Verifies prevention of naive arithmetic averaging pitfalls.
    """

    def test_north_boundary_wrap_around(self):
        """
        Critical test: 350° (North-North-West) and 10° (North-North-East) with equal weights.
        Naive average: (350 + 10) / 2 = 180° (Due South - totally wrong!).
        Circular vector average: 0° / 360° (True North).
        """
        angles = [350.0, 10.0]
        weights = [0.5, 0.5]
        blended, R = circular_mean_degrees(angles, weights)
        self.assertAlmostEqual(blended % 360.0, 0.0, delta=0.5)
        self.assertGreater(R, 0.95)

    def test_weighted_angles(self):
        """
        Angles 0° (North) with weight 0.75 and 90° (East) with weight 0.25.
        Vector sum: X = 0.75, Y = 0.25. atan2(0.25, 0.75) ≈ 18.43°.
        """
        angles = [0.0, 90.0]
        weights = [0.75, 0.25]
        blended, R = circular_mean_degrees(angles, weights)
        expected = math.degrees(math.atan2(0.25, 0.75))
        self.assertAlmostEqual(blended, expected, delta=0.5)
        self.assertGreater(R, 0.7)

    def test_quadrant_averaging(self):
        """
        90° (East) and 180° (South) equal weights -> 135° (South-East).
        """
        angles = [90.0, 180.0]
        weights = [0.5, 0.5]
        blended, R = circular_mean_degrees(angles, weights)
        self.assertAlmostEqual(blended, 135.0, delta=0.5)

    def test_opposing_directions_dispersion(self):
        """
        Opposing angles (e.g. 0° and 180°) equal weights cancel out (R ≈ 0).
        Dispersion should be large and confidence should be minimal.
        """
        angles = [0.0, 180.0]
        weights = [0.5, 0.5]
        blended, R = circular_mean_degrees(angles, weights)
        self.assertAlmostEqual(R, 0.0, delta=0.01)

        dispersion, confidence = circular_dispersion_and_confidence(R)
        self.assertGreater(dispersion, 50.0)
        self.assertLessEqual(confidence, 0.20)

    def test_identical_angles_high_coherence(self):
        """
        All models agree on 225° (South-West) -> R = 1.0, dispersion ≈ 0, confidence high.
        """
        angles = [225.0, 225.0, 225.0]
        weights = [0.33, 0.33, 0.34]
        blended, R = circular_mean_degrees(angles, weights)
        self.assertAlmostEqual(blended, 225.0, delta=0.1)
        self.assertAlmostEqual(R, 1.0, delta=0.01)

        dispersion, confidence = circular_dispersion_and_confidence(R)
        self.assertLess(dispersion, 1.0)
        self.assertGreaterEqual(confidence, 0.90)


class TestForecastBlendingEngine(unittest.TestCase):
    """
    Unit tests for core multi-model blending logic, weighted contributions,
    variable support, and persistence.
    """

    def setUp(self):
        self.temp_store_file = Path("data/processed/test_blended_store.json")
        self.store = BlendedForecastStore(storage_path=self.temp_store_file)
        self.store.clear()
        self.engine = ForecastBlendingEngine(store=self.store)

    def tearDown(self):
        self.store.clear()

    def test_linear_blending_temperature(self):
        """
        Verifies Blended Forecast = sum(model forecast × adaptive model weight)
        for continuous variables (temperature).
        """
        forecasts = {
            "gfs": 30.0,
            "ecmwf": 32.0,
            "graphcast": 31.0,
            "pangu": 29.0,
        }
        weights = {
            "gfs": 0.25,
            "ecmwf": 0.35,
            "graphcast": 0.20,
            "pangu": 0.20,
        }
        expected_blend = (30.0 * 0.25) + (32.0 * 0.35) + (31.0 * 0.20) + (29.0 * 0.20)  # 30.70

        result = self.engine.blend(
            variable="temperature",
            lead_time_hours=24,
            station_id="BOM",
            model_forecasts=forecasts,
            model_weights=weights,
            persist=True,
        )

        self.assertAlmostEqual(result.blended_value, expected_blend, places=2)
        self.assertEqual(result.blending_method, BlendingMethod.LINEAR_WEIGHTED_SUM)
        self.assertEqual(result.variable, "temperature")
        self.assertEqual(result.unit, "°C")

        # Verify model contributions
        self.assertEqual(len(result.model_contributions), 4)
        total_pct = sum(c.contribution_percentage for c in result.model_contributions)
        self.assertAlmostEqual(total_pct, 100.0, delta=0.5)

        for c in result.model_contributions:
            self.assertAlmostEqual(c.weighted_contribution, c.forecast_value * c.adaptive_weight, delta=0.05)

        # Verify confidence bounds exist
        self.assertIsNotNone(result.confidence_interval_10th)
        self.assertIsNotNone(result.confidence_interval_90th)
        self.assertLess(result.confidence_interval_10th, result.blended_value)
        self.assertGreater(result.confidence_interval_90th, result.blended_value)

    def test_rainfall_blending_non_negativity(self):
        """
        Rainfall must respect the physical lower bound (>= 0 mm).
        """
        forecasts = {"gfs": 45.0, "ecmwf": 55.0, "graphcast": 50.0}
        weights = {"gfs": 0.3, "ecmwf": 0.4, "graphcast": 0.3}
        expected_blend = (45.0 * 0.3) + (55.0 * 0.4) + (50.0 * 0.3)  # 50.5

        result = self.engine.blend(
            variable="rainfall",
            lead_time_hours=48,
            station_id="BOM",
            model_forecasts=forecasts,
            model_weights=weights,
        )

        self.assertAlmostEqual(result.blended_value, expected_blend, places=2)
        self.assertGreaterEqual(result.blended_value, 0.0)
        self.assertGreaterEqual(result.confidence_interval_10th, 0.0)
        self.assertEqual(result.unit, "mm")

    def test_wind_speed_blending(self):
        """
        Wind speed must be non-negative and weighted.
        """
        forecasts = {"gfs": 18.0, "ecmwf": 22.0}
        weights = {"gfs": 0.5, "ecmwf": 0.5}

        result = self.engine.blend(
            variable="wind_speed",
            lead_time_hours=24,
            latitude=19.07,
            longitude=72.87,
            model_forecasts=forecasts,
            model_weights=weights,
        )

        self.assertAlmostEqual(result.blended_value, 20.0, places=1)
        self.assertGreaterEqual(result.confidence_interval_10th, 0.0)
        self.assertEqual(result.unit, "km/h")

    def test_wind_direction_circular_blending(self):
        """
        Wind direction uses circular vector averaging across the 0°/360° boundary.
        """
        forecasts = {
            "gfs": 355.0,
            "ecmwf": 5.0,
            "graphcast": 358.0,
        }
        weights = {"gfs": 0.33, "ecmwf": 0.34, "graphcast": 0.33}

        result = self.engine.blend(
            variable="wind_direction",
            lead_time_hours=24,
            station_id="DEL",
            model_forecasts=forecasts,
            model_weights=weights,
        )

        self.assertEqual(result.blending_method, BlendingMethod.VECTOR_CIRCULAR_AVERAGE)
        # Should be approximately 359° / 0° (North), NOT 239° arithmetic
        self.assertTrue(result.blended_value >= 355.0 or result.blended_value <= 5.0)
        self.assertEqual(result.unit, "degrees")
        self.assertGreaterEqual(result.confidence_index, 0.85)

    def test_store_and_retrieve_persistence(self):
        """
        Verifies individual forecasts, weights, and blended result are stored and retrievable.
        """
        result = self.engine.blend(
            variable="temperature",
            lead_time_hours=72,
            station_id="BLR",
            persist=True,
        )

        # Retrieve by deterministic ID
        stored = self.store.get_by_id(result.forecast_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.blended_value, result.blended_value)
        self.assertEqual(stored.station_id, "BLR")
        self.assertEqual(stored.lead_time_hours, 72)
        self.assertEqual(len(stored.individual_forecasts), len(result.individual_forecasts))
        self.assertEqual(len(stored.model_weights), len(result.model_weights))

        # Query by criteria
        queried = self.store.query(station_id="BLR", variable="temperature", lead_time_hours=72)
        self.assertGreaterEqual(len(queried), 1)
        self.assertEqual(queried[0].forecast_id, result.forecast_id)


class TestBlendingSafeguardsAndValidation(unittest.TestCase):
    """
    Validates edge cases:
    - Missing models handled without crashing
    - Weights renormalized to 1.0 strictly
    - Invalid physical values rejected
    - Spatio-temporal coordinate alignment checks
    """

    def setUp(self):
        self.engine = ForecastBlendingEngine()

    def test_missing_model_tolerance_and_weight_renormalization(self):
        """
        If a model is missing (None or NaN), the engine must NOT crash.
        Remaining weights must be renormalized to sum exactly to 1.0000.
        """
        forecasts = {
            "gfs": 28.0,
            "ecmwf": float("nan"),  # Missing
            "graphcast": 29.0,
            "pangu": None,           # Missing
        }
        weights = {
            "gfs": 0.25,
            "ecmwf": 0.35,
            "graphcast": 0.20,
            "pangu": 0.20,
        }

        result = self.engine.blend(
            variable="temperature",
            lead_time_hours=24,
            station_id="BOM",
            model_forecasts=forecasts,
            model_weights=weights,
            persist=False,
        )

        self.assertIn("ecmwf", result.models_missing)
        self.assertIn("pangu", result.models_missing)
        self.assertEqual(set(result.models_available), {"gfs", "graphcast"})
        self.assertTrue(result.weights_renormalized)

        # Renormalized weights must sum strictly to 1.0
        w_sum = sum(result.model_weights.values())
        self.assertAlmostEqual(w_sum, 1.0, places=4)

        # Expected weights: gfs was 0.25, graphcast was 0.20. Ratio = 0.25 / 0.45 ≈ 0.5556, 0.20 / 0.45 ≈ 0.4444
        self.assertAlmostEqual(result.model_weights["gfs"], 0.25 / 0.45, delta=0.01)
        self.assertAlmostEqual(result.model_weights["graphcast"], 0.20 / 0.45, delta=0.01)

    def test_invalid_physical_value_rejection(self):
        """
        Values outside physical boundaries (e.g., Temperature = 150°C, Rain = -10mm)
        must be rejected and logged in models_rejected.
        """
        forecasts = {
            "gfs": 28.0,
            "ecmwf": 150.0,   # Physical limit violation (> 65°C)
            "graphcast": 29.0,
        }
        weights = {"gfs": 0.4, "ecmwf": 0.3, "graphcast": 0.3}

        result = self.engine.blend(
            variable="temperature",
            lead_time_hours=24,
            station_id="DEL",
            model_forecasts=forecasts,
            model_weights=weights,
            persist=False,
        )

        self.assertIn("ecmwf", result.models_rejected)
        self.assertNotIn("ecmwf", result.models_available)
        self.assertEqual(set(result.models_available), {"gfs", "graphcast"})
        self.assertTrue(result.weights_renormalized)
        self.assertAlmostEqual(sum(result.model_weights.values()), 1.0, places=4)

    def test_all_models_invalid_raises_error(self):
        """
        If all inputs are invalid/missing, system raises ValueError instead of corrupting data.
        """
        forecasts = {"gfs": 200.0, "ecmwf": -100.0}
        with self.assertRaises(ValueError):
            self.engine.blend(
                variable="temperature",
                station_id="BOM",
                model_forecasts=forecasts,
            )

    def test_spatial_misalignment_rejection(self):
        """
        Forecast coordinates that deviate beyond tolerance (> 0.15°) must be rejected.
        """
        target_lat, target_lon = 19.07, 72.87  # Mumbai
        model_coords = {
            "gfs": (19.07, 72.87),
            "ecmwf": (28.61, 77.20),  # Delhi! Way out of alignment
        }

        with self.assertRaises(ValueError) as ctx:
            self.engine.blend(
                variable="temperature",
                latitude=target_lat,
                longitude=target_lon,
                model_coordinates=model_coords,
            )
        self.assertIn("Spatial alignment error", str(ctx.exception))

    def test_temporal_misalignment_rejection(self):
        """
        Forecast timestamps that deviate beyond 1 hour from target must be rejected.
        """
        now = datetime.now()
        model_times = {
            "gfs": now,
            "ecmwf": now + timedelta(hours=6),  # 6 hours off!
        }

        with self.assertRaises(ValueError) as ctx:
            self.engine.blend(
                variable="temperature",
                timestamp=now,
                model_timestamps=model_times,
            )
        self.assertIn("Temporal alignment error", str(ctx.exception))


class TestBlendingAPIEndpoints(unittest.TestCase):
    """
    Integration tests for FastAPI endpoints:
    - POST /api/v1/forecast/blend
    - GET /api/v1/forecast/blended
    - GET /api/v1/forecast/blended/history
    - GET /api/v1/forecast/blended/{forecast_id}
    """

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_post_blend_custom_forecasts(self):
        """
        Test POST /api/v1/forecast/blend with explicit models and weights.
        """
        payload = {
            "variable": "temperature",
            "lead_time_hours": 24,
            "station_id": "DEL",
            "model_forecasts": {
                "gfs": 32.5,
                "ecmwf": 34.0,
                "graphcast": 33.0,
            },
            "model_weights": {
                "gfs": 0.3,
                "ecmwf": 0.4,
                "graphcast": 0.3,
            },
            "persist": True,
        }
        response = self.client.post("/api/v1/forecast/blend", json=payload)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["station_id"], "DEL")
        self.assertEqual(data["variable"], "temperature")
        self.assertAlmostEqual(data["blended_value"], (32.5 * 0.3) + (34.0 * 0.4) + (33.0 * 0.3), delta=0.1)
        self.assertEqual(len(data["model_contributions"]), 3)
        self.assertIn("confidence_index", data)
        self.assertIn("ensemble_spread", data)

        # Verify it can be retrieved via GET /blended/{forecast_id}
        fid = data["forecast_id"]
        get_resp = self.client.get(f"/api/v1/forecast/blended/{fid}")
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.json()["forecast_id"], fid)

    def test_post_blend_wind_direction_vector_average(self):
        """
        Test POST /api/v1/forecast/blend for wind direction with circular averaging.
        """
        payload = {
            "variable": "wind_direction",
            "lead_time_hours": 12,
            "station_id": "BOM",
            "model_forecasts": {
                "gfs": 350.0,
                "ecmwf": 10.0,
            },
            "model_weights": {
                "gfs": 0.5,
                "ecmwf": 0.5,
            },
            "persist": True,
        }
        response = self.client.post("/api/v1/forecast/blend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["blending_method"], "vector_circular_average")
        # Near 0°/360°
        self.assertTrue(data["blended_value"] >= 355.0 or data["blended_value"] <= 5.0)

    def test_get_blended_on_demand(self):
        """
        Test GET /api/v1/forecast/blended query params.
        """
        response = self.client.get("/api/v1/forecast/blended?station_id=BOM&variable=rainfall&lead_time_hours=48")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["station_id"], "BOM")
        self.assertEqual(data["variable"], "rainfall")
        self.assertEqual(data["unit"], "mm")
        self.assertGreaterEqual(data["blended_value"], 0.0)
        self.assertGreater(len(data["individual_forecasts"]), 0)
        self.assertGreater(len(data["model_weights"]), 0)

    def test_get_blended_history(self):
        """
        Test GET /api/v1/forecast/blended/history filtering.
        """
        # Ensure at least one record is stored
        self.client.get("/api/v1/forecast/blended?station_id=DEL&variable=temperature&lead_time_hours=24&persist=true")

        response = self.client.get("/api/v1/forecast/blended/history?station_id=DEL&variable=temperature")
        self.assertEqual(response.status_code, 200)
        records = response.json()
        self.assertIsInstance(records, list)
        self.assertGreater(len(records), 0)
        self.assertEqual(records[0]["station_id"], "DEL")

    def test_invalid_station_returns_400(self):
        """
        Test that an unknown station returns HTTP 400.
        """
        response = self.client.get("/api/v1/forecast/blended?station_id=INVALID_XYZ")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown station ID", response.json()["detail"])

    def test_nonexistent_id_returns_404(self):
        """
        Test that a nonexistent forecast ID returns HTTP 404.
        """
        response = self.client.get("/api/v1/forecast/blended/NON_EXISTENT_ID_9999")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
