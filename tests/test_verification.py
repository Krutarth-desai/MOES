import unittest
from pathlib import Path
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.matcher import SpatialTemporalMatcher
from backend.app.services.verification.metrics import VerificationMath
from backend.app.services.verification.store import SkillScoreStore
from backend.app.services.verification.service import ForecastMetricsService
from backend.app.services.verification.schemas import (
    ComprehensiveSkillScore,
    HistoricalSkillRecord,
    MetricDimensionSlice,
)
from backend.app.config.settings import SAMPLE_DIR


class TestVerificationMath(unittest.TestCase):
    def test_continuous_metrics_calculation(self):
        # Known hand-calculated test vectors
        forecasts = [10.0, 20.0, 30.0]
        observations = [12.0, 18.0, 33.0]
        # Errors: [-2.0, +2.0, -3.0]
        # Abs:    [2.0, 2.0, 3.0] -> MAE = 7/3 = 2.33
        # Sq:     [4.0, 4.0, 9.0] -> RMSE = sqrt(17/3) = sqrt(5.667) = 2.38
        # Bias:   -3.0 / 3 = -1.0

        mae, rmse, bias, corr = VerificationMath.compute_continuous_metrics(forecasts, observations)
        self.assertAlmostEqual(mae, 2.33, places=2)
        self.assertAlmostEqual(rmse, 2.38, places=2)
        self.assertAlmostEqual(bias, -1.0, places=2)
        self.assertGreater(corr, 0.95)

    def test_contingency_and_extreme_metrics(self):
        # Known contingency table:
        # Hits: 40, Misses: 10, False Alarms: 20, Correct Negatives: 130 (Total: 200)
        hits, misses, fa, cn = 40, 10, 20, 130

        pod, far, csi, ets = VerificationMath.compute_extreme_skill_scores(hits, misses, fa, cn)
        # POD = 40 / (40 + 10) = 0.8
        self.assertAlmostEqual(pod, 0.80, places=2)
        # FAR = 20 / (40 + 20) = 0.333
        self.assertAlmostEqual(far, 0.333, places=2)
        # CSI = 40 / (40 + 10 + 20) = 40 / 70 = 0.571
        self.assertAlmostEqual(csi, 0.571, places=2)
        # ETS should be > 0.40 and < CSI
        self.assertGreater(ets, 0.40)
        self.assertLess(ets, csi)

    def test_probabilistic_brier_score(self):
        # Probabilities: [0.9, 0.8, 0.1, 0.2]
        # Observations:  [70.0, 85.0, 5.0, 10.0] with threshold 64.5 mm
        # Binary outcome: [1.0, 1.0, 0.0, 0.0]
        # Brier = ((0.9-1)^2 + (0.8-1)^2 + (0.1-0)^2 + (0.2-0)^2) / 4 = (0.01 + 0.04 + 0.01 + 0.04) / 4 = 0.025
        probs = [0.9, 0.8, 0.1, 0.2]
        obs = [70.0, 85.0, 5.0, 10.0]
        brier, bss = VerificationMath.compute_probabilistic_metrics(probs, obs, threshold=64.5)

        self.assertAlmostEqual(brier, 0.025, places=3)
        self.assertGreater(bss, 0.80)

    def test_composite_skill_score_bounds(self):
        score_high = VerificationMath.compute_composite_skill_score(rmse=0.5, corr=0.98, csi=0.85)
        score_low = VerificationMath.compute_composite_skill_score(rmse=25.0, corr=0.10, csi=0.05)

        self.assertGreaterEqual(score_high, 0.80)
        self.assertLessEqual(score_high, 1.0)
        self.assertLess(score_low, 0.35)
        self.assertGreaterEqual(score_low, 0.05)


class TestSkillScoreStore(unittest.TestCase):
    def setUp(self):
        self.test_store_path = SAMPLE_DIR.parent / "processed" / "test_skill_store.json"
        self.store = SkillScoreStore(storage_path=self.test_store_path)
        self.store.clear()

    def tearDown(self):
        self.store.clear()

    def test_hierarchical_fallback_for_adaptive_weighting(self):
        dim = MetricDimensionSlice(
            model_name="NWP Model A",
            variable=ForecastVariable.RAINFALL,
            lead_time_hours=48,
            region="Western Ghats",
            season=Season.MONSOON,
            weather_regime=WeatherRegime.MONSOON_ACTIVE,
        )
        score = ComprehensiveSkillScore(
            sample_size=50,
            mae=3.2,
            rmse=4.1,
            bias=1.5,
            correlation=0.89,
            composite_skill_score=0.78,
        )
        self.store.add_record(HistoricalSkillRecord(dimension=dim, metrics=score))

        # 1. Exact match retrieval
        w_exact = self.store.get_adaptive_skill_weight(
            model_name="NWP Model A",
            variable=ForecastVariable.RAINFALL,
            lead_time_hours=48,
            region="Western Ghats",
            weather_regime=WeatherRegime.MONSOON_ACTIVE,
        )
        self.assertEqual(w_exact, 0.78)

        # 2. Region & Lead fallback (unseen regime)
        w_reg = self.store.get_adaptive_skill_weight(
            model_name="NWP Model A",
            variable=ForecastVariable.RAINFALL,
            lead_time_hours=48,
            region="Western Ghats",
            weather_regime=WeatherRegime.CYCLONIC_CIRCULATION,
        )
        self.assertEqual(w_reg, 0.78)

        # 3. Safe default fallback when model has no records
        w_default = self.store.get_adaptive_skill_weight(
            model_name="Nonexistent Model",
            variable=ForecastVariable.RAINFALL,
            lead_time_hours=48,
        )
        self.assertEqual(w_default, 0.50)


class TestForecastMetricsService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fcst_pipeline = IngestionPipeline()
        cls.fcst_pipeline.ingest_directory(SAMPLE_DIR)
        cls.obs_service = ObservationIngestionService()
        cls.matcher = SpatialTemporalMatcher()
        cls.metrics_service = ForecastMetricsService()

        # Ingest and match
        fcst_records = cls.fcst_pipeline.get_all_records()
        obs_records, _ = cls.obs_service.load_file(SAMPLE_DIR / "observations.csv")
        cls.matched = cls.matcher.match(fcst_records, obs_records)

        # Populate verification engine
        cls.records = cls.metrics_service.evaluate_and_store(cls.matched)

    def test_evaluate_and_store_generates_all_strata(self):
        self.assertGreater(len(self.records), 50)
        # Check that records are persisted
        persisted = self.metrics_service.store.get_all_records()
        self.assertGreaterEqual(len(persisted), len(self.records))

    def test_get_overall_performance(self):
        resp = self.metrics_service.get_overall_performance(ForecastVariable.RAINFALL)
        self.assertEqual(resp.variable, ForecastVariable.RAINFALL)
        self.assertGreaterEqual(len(resp.models), 4)

        # Check model names
        model_names = list(resp.models.keys())
        self.assertTrue(any("NWP Model A" in m for m in model_names))
        self.assertTrue(any("NWP Model B" in m for m in model_names))

        # NWP Model A should have positive rainfall bias (wet bias)
        gfs_model = next(m for m in model_names if "NWP Model A" in m)
        self.assertGreater(resp.models[gfs_model].bias, 0.0)

    def test_get_performance_by_lead_time(self):
        resp = self.metrics_service.get_performance_by_lead_time(
            variable=ForecastVariable.TEMPERATURE,
            model_name="NWP Model A",
        )
        self.assertEqual(resp.variable, ForecastVariable.TEMPERATURE)
        self.assertGreaterEqual(len(resp.lead_time_profile), 5)
        # Check lead times are represented
        self.assertIn(24, resp.lead_time_profile)
        self.assertIn(72, resp.lead_time_profile)
        self.assertIn(120, resp.lead_time_profile)

    def test_get_performance_by_region(self):
        resp = self.metrics_service.get_performance_by_region(
            variable=ForecastVariable.RAINFALL,
            model_name="NWP Model B",
        )
        self.assertEqual(resp.variable, ForecastVariable.RAINFALL)
        self.assertGreater(len(resp.regional_profile), 0)

    def test_get_performance_by_season(self):
        resp = self.metrics_service.get_performance_by_season(
            variable=ForecastVariable.WIND_SPEED,
            model_name="AI/ML Forecast",
        )
        self.assertEqual(resp.variable, ForecastVariable.WIND_SPEED)
        self.assertIn("monsoon", resp.seasonal_profile)

    def test_get_performance_by_weather_regime(self):
        resp = self.metrics_service.get_performance_by_regime(
            variable=ForecastVariable.WIND_SPEED,
            model_name="AI/ML Forecast",
        )
        self.assertEqual(resp.variable, ForecastVariable.WIND_SPEED)
        self.assertIn("monsoon_active", resp.regime_profile)


if __name__ == "__main__":
    unittest.main()
