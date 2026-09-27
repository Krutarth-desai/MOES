import unittest
from backend.app.models.domain import WeatherRegime, WeatherVariable
from backend.app.ml.weight_model import AdaptiveWeightModel
from backend.app.services.blender_service import AdaptiveSoftmaxBlender


class TestBlender(unittest.TestCase):
    def test_weight_simplex_constraint(self):
        """Verify that model weights sum to 1.0 and respect non-negativity."""
        model = AdaptiveWeightModel(min_floor=0.05)
        weights = model.predict_weights(
            lat=19.07,
            lon=72.87,
            lead_time_hours=24,
            regime=WeatherRegime.MONSOON_ACTIVE,
            variable=WeatherVariable.PRECIPITATION,
        )

        total_weight = sum(weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=3)
        for m, w in weights.items():
            self.assertGreaterEqual(w, 0.05)

    def test_lead_time_adaptive_shift(self):
        """Verify that AI models have higher weight at short lead time vs long lead time."""
        model = AdaptiveWeightModel()
        weights_24h = model.predict_weights(
            lat=28.61,
            lon=77.20,
            lead_time_hours=24,
            regime=WeatherRegime.NEUTRAL,
            variable=WeatherVariable.TEMPERATURE_2M,
        )
        weights_144h = model.predict_weights(
            lat=28.61,
            lon=77.20,
            lead_time_hours=144,
            regime=WeatherRegime.NEUTRAL,
            variable=WeatherVariable.TEMPERATURE_2M,
        )

        # GraphCast weight should be higher at 24h than at 144h
        self.assertGreater(weights_24h["graphcast"], weights_144h["graphcast"])
        # ECMWF weight should increase or dominate at long lead times
        self.assertGreater(weights_144h["ecmwf"], weights_24h["ecmwf"])

    def test_blender_precipitation_non_negative(self):
        """Ensure precipitation is clamped to non-negative values."""
        blender = AdaptiveSoftmaxBlender()
        raw_preds = {"gfs": 0.0, "ecmwf": 0.0, "graphcast": 0.0, "pangu": 0.0}
        weights = {"gfs": 0.25, "ecmwf": 0.25, "graphcast": 0.25, "pangu": 0.25}

        blended, conf_10, conf_90 = blender.blend_point(raw_preds, weights, WeatherVariable.PRECIPITATION)
        self.assertGreaterEqual(blended, 0.0)
        self.assertGreaterEqual(conf_10, 0.0)


if __name__ == "__main__":
    unittest.main()
