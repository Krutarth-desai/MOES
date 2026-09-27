import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.weighting import (
    AdaptiveWeightEngine,
    AdaptiveWeightOutput,
    FallbackLevel,
    WeightCalculationRequest,
)
from backend.app.services.verification.store import SkillScoreStore


class TestAdaptiveWeightEngine(unittest.TestCase):
    """
    Comprehensive test suite for the Adaptive Model Weight Engine.
    Validates:
    1. Simplex property (weights strictly sum to 1.0)
    2. Monotonicity (better-performing models receive higher weight)
    3. Robustness against missing data, unseen regions, and unseen regimes
    4. Regime-dependent weight variations
    5. Safeguard enforcement (min/max clamps, sample-size shrinkage)
    6. Full API endpoint integration
    """

    def setUp(self):
        self.engine = AdaptiveWeightEngine(min_weight=0.05, max_weight=0.85)
        self.client = TestClient(app)

    # -------------------------------------------------------------
    # 1. Weights Sum to 1.0 (Simplex Constraint)
    # -------------------------------------------------------------
    def test_weights_sum_to_one_across_dimensions(self):
        """Proof 1: Weights must sum to 1.0 across diverse lead times, variables, and model counts."""
        test_cases = [
            (["Model 1", "Model 2"], "temperature", 24),
            (["Model A", "Model B", "Model C"], "rainfall", 48),
            (["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI/ML Forecast"], "rainfall", 24),
            (["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI/ML Forecast"], "wind_speed", 120),
            (["M1", "M2", "M3", "M4", "M5"], "temperature", 72),
        ]

        for models, var, lead in test_cases:
            with self.subTest(models=models, var=var, lead=lead):
                res = self.engine.calculate_weights(
                    models=models,
                    variable=var,
                    lead_time_hours=lead,
                )
                total = sum(res.weights.values())
                norm_total = sum(res.normalized_weights.values())

                self.assertAlmostEqual(total, 1.0, places=4)
                self.assertAlmostEqual(norm_total, 1.0, places=4)

                # Verify each weight is non-negative and respects min floor
                for m, w in res.weights.items():
                    self.assertGreaterEqual(w, 0.0)
                    self.assertLessEqual(w, 1.0)

    def test_weights_sum_to_one_with_extreme_skill_disparities(self):
        """Proof 1b: Weights must sum to 1.0 even when one model massively outperforms others."""
        custom_perf = {
            "SuperModel": {"skill": 0.99, "rmse": 0.1, "sample_size": 100},
            "PoorModel1": {"skill": 0.10, "rmse": 9.5, "sample_size": 100},
            "PoorModel2": {"skill": 0.05, "rmse": 12.0, "sample_size": 100},
        }
        res = self.engine.calculate_weights(
            models=["SuperModel", "PoorModel1", "PoorModel2"],
            variable="rainfall",
            lead_time_hours=24,
            historical_performance=custom_perf,
        )
        total = sum(res.weights.values())
        self.assertAlmostEqual(total, 1.0, places=4)
        self.assertGreater(res.weights["SuperModel"], res.weights["PoorModel1"])
        self.assertGreater(res.weights["SuperModel"], res.weights["PoorModel2"])

    # -------------------------------------------------------------
    # 2. Better-Performing Models Receive Higher Weight
    # -------------------------------------------------------------
    def test_better_performing_models_receive_higher_weight(self):
        """Proof 2: A model with lower error / higher historical skill must receive a higher weight."""
        custom_perf = {
            "HighSkillModel": {"rmse": 1.2, "composite_skill_score": 0.92, "sample_size": 80},
            "LowSkillModel": {"rmse": 4.5, "composite_skill_score": 0.35, "sample_size": 80},
        }

        res = self.engine.calculate_weights(
            models=["HighSkillModel", "LowSkillModel"],
            variable="temperature",
            lead_time_hours=24,
            historical_performance=custom_perf,
        )

        w_high = res.weights["HighSkillModel"]
        w_low = res.weights["LowSkillModel"]

        self.assertGreater(w_high, w_low)
        self.assertAlmostEqual(w_high + w_low, 1.0, places=4)
        # Ratio check: HighSkillModel should receive substantially more weight
        self.assertGreater(w_high, 0.65)

    def test_inverse_error_monotonicity(self):
        """Proof 2b: Monotonically increasing weights for decreasing RMSE."""
        custom_perf = {
            "Model_RMSE_1": {"rmse": 1.0, "sample_size": 50},
            "Model_RMSE_2": {"rmse": 2.0, "sample_size": 50},
            "Model_RMSE_4": {"rmse": 4.0, "sample_size": 50},
        }

        res = self.engine.calculate_weights(
            models=["Model_RMSE_1", "Model_RMSE_2", "Model_RMSE_4"],
            variable="rainfall",
            lead_time_hours=24,
            historical_performance=custom_perf,
        )

        self.assertGreater(res.weights["Model_RMSE_1"], res.weights["Model_RMSE_2"])
        self.assertGreater(res.weights["Model_RMSE_2"], res.weights["Model_RMSE_4"])

    # -------------------------------------------------------------
    # 3. Missing Data Handled Safely (Safeguards)
    # -------------------------------------------------------------
    def test_missing_model_data_handled_safely(self):
        """Proof 3a: Completely unseen models receive safe neutral fallback without crashing."""
        custom_perf = {
            "KnownModel": {"rmse": 2.0, "sample_size": 50},
        }

        res = self.engine.calculate_weights(
            models=["KnownModel", "UnknownModelA", "UnknownModelB"],
            variable="temperature",
            lead_time_hours=24,
            historical_performance=custom_perf,
        )

        self.assertAlmostEqual(sum(res.weights.values()), 1.0, places=4)
        self.assertIn("UnknownModelA", res.weights)
        self.assertIn("UnknownModelB", res.weights)
        # Both unknown models should receive equal neutral fallback weights
        self.assertAlmostEqual(res.weights["UnknownModelA"], res.weights["UnknownModelB"], places=4)
        # Known model should still outperform neutral fallback
        self.assertGreater(res.weights["KnownModel"], res.weights["UnknownModelA"])
        # Check safeguards explanation
        self.assertTrue(any("Missing historical data" in s for s in res.safeguards_applied))

    def test_unseen_region_and_unseen_regime_fallback(self):
        """Proof 3b: Unseen region and regime fall back gracefully to lead-time skill."""
        res = self.engine.calculate_weights(
            models=["NWP Model A", "NWP Model B"],
            variable="rainfall",
            lead_time_hours=24,
            region="Imaginary Atlantis Valley",
            weather_regime="Volcanic Ash Winter",
        )

        self.assertAlmostEqual(sum(res.weights.values()), 1.0, places=4)
        self.assertTrue(any("Unseen" in s for s in res.safeguards_applied))
        self.assertGreater(len(res.model_details), 0)

    def test_insufficient_sample_size_shrinkage(self):
        """Proof 3c: Sparse historical sample (N=2) is shrunk toward neutral prior (0.50)."""
        custom_perf = {
            # High raw skill but tiny sample size
            "LuckyFewSampleModel": {"skill": 0.99, "sample_size": 2},
            # Solid skill with high statistical power
            "ReliableModel": {"skill": 0.82, "sample_size": 150},
        }

        res = self.engine.calculate_weights(
            models=["LuckyFewSampleModel", "ReliableModel"],
            variable="temperature",
            lead_time_hours=24,
            historical_performance=custom_perf,
        )

        # Because LuckyFewSampleModel only has N=2, its reliability score is shrunk heavily
        lucky_detail = next(d for d in res.model_details if d.model_name == "LuckyFewSampleModel")
        self.assertLess(lucky_detail.reliability_score, 0.70)
        self.assertTrue(any("Insufficient sample size" in s for s in res.safeguards_applied))

    def test_empty_historical_store_produces_uniform_weights(self):
        """Proof 3d: Empty historical store falls back to uniform normalized weights."""
        res = self.engine.calculate_weights(
            models=["M1", "M2", "M3", "M4"],
            variable="rainfall",
            lead_time_hours=24,
            historical_performance={},
        )
        self.assertAlmostEqual(sum(res.weights.values()), 1.0, places=4)
        for w in res.weights.values():
            self.assertAlmostEqual(w, 0.25, places=3)

    # -------------------------------------------------------------
    # 4. Different Regimes Produce Different Weights
    # -------------------------------------------------------------
    def test_different_regimes_produce_different_weights(self):
        """Proof 4: Changing weather regime dynamically alters model weight ranking."""
        # Scenario: Model A specializes in Heavy Rain convective physics,
        # while Model B specializes in Heat Wave thermodynamic balance.
        regime_performance = {
            "Heavy Rain": {
                "Physics_Model_A": {"skill": 0.92, "rmse": 1.5, "sample_size": 80},
                "Thermodynamic_Model_B": {"skill": 0.40, "rmse": 6.2, "sample_size": 80},
            },
            "Heat Wave": {
                "Physics_Model_A": {"skill": 0.38, "rmse": 4.8, "sample_size": 80},
                "Thermodynamic_Model_B": {"skill": 0.95, "rmse": 1.1, "sample_size": 80},
            },
        }

        # 1. Evaluate during Heavy Rain regime
        rain_res = self.engine.calculate_weights(
            models=["Physics_Model_A", "Thermodynamic_Model_B"],
            variable="rainfall",
            lead_time_hours=24,
            weather_regime="Heavy Rain",
            historical_performance=regime_performance,
        )

        # 2. Evaluate during Heat Wave regime
        heat_res = self.engine.calculate_weights(
            models=["Physics_Model_A", "Thermodynamic_Model_B"],
            variable="temperature",
            lead_time_hours=24,
            weather_regime="Heat Wave",
            historical_performance=regime_performance,
        )

        # Assertions proving regime-driven dynamic adaptation
        self.assertGreater(rain_res.weights["Physics_Model_A"], rain_res.weights["Thermodynamic_Model_B"])
        self.assertGreater(heat_res.weights["Thermodynamic_Model_B"], heat_res.weights["Physics_Model_A"])
        # Cross-comparison
        self.assertGreater(rain_res.weights["Physics_Model_A"], heat_res.weights["Physics_Model_A"])
        self.assertGreater(heat_res.weights["Thermodynamic_Model_B"], rain_res.weights["Thermodynamic_Model_B"])

    # -------------------------------------------------------------
    # 5. Safeguards: Min/Max Weight Floor and Ceiling
    # -------------------------------------------------------------
    def test_min_and_max_weight_clamping(self):
        """Verify strict min_weight floor (0.10) and max_weight ceiling (0.60)."""
        custom_perf = {
            "DominantModel": {"skill": 0.99, "rmse": 0.1, "sample_size": 100},
            "WeakModel1": {"skill": 0.05, "rmse": 15.0, "sample_size": 100},
            "WeakModel2": {"skill": 0.05, "rmse": 16.0, "sample_size": 100},
        }

        res = self.engine.calculate_weights(
            models=["DominantModel", "WeakModel1", "WeakModel2"],
            variable="rainfall",
            lead_time_hours=24,
            historical_performance=custom_perf,
            min_weight=0.10,
            max_weight=0.60,
        )

        self.assertAlmostEqual(sum(res.weights.values()), 1.0, places=4)
        # DominantModel must be capped at 0.60
        self.assertLessEqual(res.weights["DominantModel"], 0.60)
        # Weak models must be at least 0.10
        self.assertGreaterEqual(res.weights["WeakModel1"], 0.10)
        self.assertGreaterEqual(res.weights["WeakModel2"], 0.10)
        self.assertTrue(any("boundary constraints" in s for s in res.safeguards_applied))

    # -------------------------------------------------------------
    # 6. REST API Endpoints Integration
    # -------------------------------------------------------------
    def test_api_calculate_endpoint(self):
        """POST /api/v1/weights/calculate"""
        payload = {
            "models": ["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI/ML Forecast"],
            "variable": "rainfall",
            "lead_time_hours": 24,
            "region": "Western Ghats",
            "weather_regime": "monsoon_active",
        }
        response = self.client.post("/api/v1/weights/calculate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("weights", data)
        self.assertIn("normalized_weights", data)
        self.assertIn("summary_explanation", data)
        self.assertIn("model_details", data)
        self.assertEqual(len(data["model_details"]), 4)

        total_w = sum(data["weights"].values())
        self.assertAlmostEqual(total_w, 1.0, places=3)

    def test_api_dynamic_get_endpoint(self):
        """GET /api/v1/weights/dynamic"""
        response = self.client.get(
            "/api/v1/weights/dynamic?variable=temperature&lead_time_hours=48&region=Indo-Gangetic+Plains"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertAlmostEqual(sum(data["weights"].values()), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
