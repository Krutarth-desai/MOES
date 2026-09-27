import unittest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.regime import (
    BaseWeatherRegimeClassifier,
    ForecastContext,
    MLWeatherRegimeClassifier,
    RegimeClassificationResult,
    RegimeClassificationService,
    RegimeType,
    RuleBasedRegimeClassifier,
    WeatherContext,
    WeatherRegimeClassifier,
)
from backend.app.services.regime_service import WeatherRegimeService


class TestWeatherRegimeClassification(unittest.TestCase):
    """
    Comprehensive test suite for the Weather Regime Classification module.
    Validates interface compliance, deterministic rules across all 7 regimes,
    ML classifier hot-swapping, forecast context integration, and API endpoints.
    """

    def setUp(self):
        self.rule_classifier = RuleBasedRegimeClassifier()
        self.ml_classifier = MLWeatherRegimeClassifier()
        self.service = RegimeClassificationService(self.rule_classifier)
        self.client = TestClient(app)

    # -------------------------------------------------------------
    # 1. Interface & Extensibility Tests
    # -------------------------------------------------------------
    def test_interface_compliance(self):
        """Verify WeatherRegimeClassifier interface contract."""
        self.assertTrue(issubclass(RuleBasedRegimeClassifier, WeatherRegimeClassifier))
        self.assertTrue(issubclass(MLWeatherRegimeClassifier, WeatherRegimeClassifier))
        self.assertIs(BaseWeatherRegimeClassifier, WeatherRegimeClassifier)

    def test_classifier_swappability(self):
        """Verify dynamic swapping of rule-based classifier with ML classifier."""
        service = RegimeClassificationService(self.rule_classifier)
        self.assertIn("Deterministic-RuleBased", service.active_classifier.classifier_name)

        # Hot-swap to ML classifier
        service.set_classifier(self.ml_classifier)
        self.assertIn("ML-Classifier", service.active_classifier.classifier_name)

        # Test classification with swapped ML classifier
        ctx = WeatherContext(temperature=30.0, rainfall=80.0, wind_speed=20.0)
        res = service.classify_context(ctx)
        self.assertIsInstance(res, RegimeClassificationResult)
        self.assertEqual(res.regime, RegimeType.HEAVY_RAIN)
        self.assertIn("ML feature vector", res.supporting_indicators[0])

    # -------------------------------------------------------------
    # 2. Rule 1: Heavy Rain Regime Tests
    # -------------------------------------------------------------
    def test_regime_heavy_rain_direct_threshold(self):
        """Rainfall >= 64.5 mm triggers Heavy Rain regime."""
        ctx = WeatherContext(
            temperature=28.0,
            rainfall=85.0,
            wind_speed=25.0,
            humidity=92.0,
            recent_rainfall=40.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(res.regime_name, "Heavy Rain")
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertLessEqual(res.confidence, 1.0)
        self.assertTrue(any("Heavy Rainfall" in ind for ind in res.supporting_indicators))

    def test_regime_heavy_rain_antecedent_saturation(self):
        """Moderate rain (>= 35 mm) on saturated ground (>= 100 mm) triggers Heavy Rain."""
        ctx = WeatherContext(
            temperature=27.0,
            rainfall=42.0,
            wind_speed=20.0,
            recent_rainfall=125.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(res.regime_name, "Heavy Rain")
        self.assertTrue(any("saturation" in ind.lower() for ind in res.supporting_indicators))

    def test_regime_extremely_heavy_rain_severity(self):
        """Rainfall >= 204.5 mm triggers EXTREME severity."""
        ctx = WeatherContext(
            temperature=26.0,
            rainfall=225.0,
            wind_speed=35.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(res.severity_level, "EXTREME")
        self.assertGreaterEqual(res.confidence, 0.88)

    # -------------------------------------------------------------
    # 3. Rule 2: Convective/Storm Regime Tests
    # -------------------------------------------------------------
    def test_regime_convective_storm_rain_and_squall(self):
        """Intense rain (>= 20 mm) + squall (>= 40 km/h) triggers Convective/Storm."""
        ctx = WeatherContext(
            temperature=29.0,
            rainfall=28.0,
            wind_speed=46.0,
            humidity=85.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.CONVECTIVE_STORM)
        self.assertEqual(res.regime_name, "Convective/Storm")
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertTrue(any("Convective signature" in ind for ind in res.supporting_indicators))

    def test_regime_convective_storm_pressure_drop(self):
        """Rapid 12h pressure drop (<= -2.5 hPa) + strong wind triggers Convective/Storm."""
        ctx = WeatherContext(
            temperature=31.0,
            rainfall=10.0,
            wind_speed=42.0,
            forecast_trends={"pressure_tendency_12h": -3.4},
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.CONVECTIVE_STORM)
        self.assertEqual(res.regime_name, "Convective/Storm")
        self.assertTrue(any("pressure fall" in ind.lower() for ind in res.supporting_indicators))

    def test_regime_convective_storm_cold_pool_outflow(self):
        """Abrupt 24h temp drop (<= -4°C) with rain and gust front triggers Convective/Storm."""
        ctx = WeatherContext(
            temperature=24.0,
            rainfall=15.0,
            wind_speed=38.0,
            forecast_trends={"temp_trend_24h": -5.2},
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.CONVECTIVE_STORM)
        self.assertTrue(any("cold-pool" in ind.lower() for ind in res.supporting_indicators))

    # -------------------------------------------------------------
    # 4. Rule 3: Heat Wave Regime Tests
    # -------------------------------------------------------------
    def test_regime_heat_wave_plains(self):
        """Plains temperature >= 40°C with dry air or rising trend triggers Heat Wave."""
        ctx = WeatherContext(
            temperature=43.5,
            rainfall=0.0,
            wind_speed=15.0,
            humidity=24.0,
            elevation_m=120.0,
            forecast_trends={"temp_trend_24h": +1.8},
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAT_WAVE)
        self.assertEqual(res.regime_name, "Heat Wave")
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertTrue(any("40.0" in ind for ind in res.supporting_indicators))

    def test_regime_heat_wave_severe_plains(self):
        """Plains temperature >= 47°C triggers EXTREME Heat Wave."""
        ctx = WeatherContext(
            temperature=47.5,
            rainfall=0.0,
            wind_speed=12.0,
            humidity=18.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAT_WAVE)
        self.assertEqual(res.severity_level, "EXTREME")
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_regime_heat_wave_hills(self):
        """Hill station (elevation >= 1000m) with temp >= 30°C triggers Heat Wave."""
        ctx = WeatherContext(
            temperature=31.5,
            rainfall=0.0,
            wind_speed=10.0,
            elevation_m=1800.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAT_WAVE)
        self.assertTrue(any("altitude" in ind.lower() or "hill" in ind.lower() for ind in res.supporting_indicators))

    # -------------------------------------------------------------
    # 5. Rule 4: High Wind Regime Tests
    # -------------------------------------------------------------
    def test_regime_high_wind(self):
        """Sustained surface winds >= 48 km/h trigger High Wind regime."""
        ctx = WeatherContext(
            temperature=27.0,
            rainfall=2.0,
            wind_speed=54.0,
            wind_direction=240.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HIGH_WIND)
        self.assertEqual(res.regime_name, "High Wind")
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertTrue(any("gale-force" in ind.lower() for ind in res.supporting_indicators))

    def test_regime_high_wind_cyclonic_gale(self):
        """Wind speed >= 75 km/h triggers EXTREME High Wind severity."""
        ctx = WeatherContext(
            temperature=26.0,
            rainfall=5.0,
            wind_speed=82.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HIGH_WIND)
        self.assertEqual(res.severity_level, "EXTREME")

    # -------------------------------------------------------------
    # 6. Rule 5: Cold Spell Regime Tests
    # -------------------------------------------------------------
    def test_regime_cold_spell_plains(self):
        """Plains temperature <= 7°C triggers Cold Spell."""
        ctx = WeatherContext(
            temperature=5.5,
            rainfall=0.0,
            wind_speed=12.0,
            elevation_m=200.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.COLD_SPELL)
        self.assertEqual(res.regime_name, "Cold Spell")
        self.assertGreaterEqual(res.confidence, 0.85)

    def test_regime_cold_spell_rapid_plunge(self):
        """Temperature <= 11°C with 24h drop <= -4°C triggers Cold Spell."""
        ctx = WeatherContext(
            temperature=9.0,
            rainfall=0.0,
            wind_speed=14.0,
            forecast_trends={"temp_trend_24h": -4.8},
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.COLD_SPELL)
        self.assertTrue(any("advection" in ind.lower() or "plunge" in ind.lower() for ind in res.supporting_indicators))

    def test_regime_cold_spell_hills(self):
        """Hill station with temperature <= 0°C triggers Cold Spell."""
        ctx = WeatherContext(
            temperature=-2.5,
            rainfall=4.0,
            wind_speed=16.0,
            elevation_m=2200.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.COLD_SPELL)

    # -------------------------------------------------------------
    # 7. Rule 6: Dry/Extreme Dry Regime Tests
    # -------------------------------------------------------------
    def test_regime_extreme_dry(self):
        """No rainfall, low antecedent rain, relative humidity <= 25% triggers Dry/Extreme Dry."""
        ctx = WeatherContext(
            temperature=33.0,
            rainfall=0.0,
            recent_rainfall=0.5,
            humidity=19.0,
            wind_speed=14.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.DRY_EXTREME_DRY)
        self.assertEqual(res.regime_name, "Dry/Extreme Dry")
        self.assertGreaterEqual(res.confidence, 0.80)
        self.assertTrue(any("moisture deficit" in ind.lower() for ind in res.supporting_indicators))

    # -------------------------------------------------------------
    # 8. Rule 7: Normal Baseline Regime Tests
    # -------------------------------------------------------------
    def test_regime_normal_baseline(self):
        """Mild, non-anomalous conditions trigger Normal regime."""
        ctx = WeatherContext(
            temperature=27.5,
            rainfall=4.0,
            wind_speed=14.0,
            humidity=62.0,
            recent_rainfall=12.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.NORMAL)
        self.assertEqual(res.regime_name, "Normal")
        self.assertEqual(res.severity_level, "NORMAL")
        self.assertGreaterEqual(res.confidence, 0.85)

    # -------------------------------------------------------------
    # 9. Co-occurring / Secondary Regimes Tests
    # -------------------------------------------------------------
    def test_secondary_regime_heavy_rain_with_high_wind(self):
        """Heavy rain with wind speed >= 45 km/h includes High Wind as secondary regime."""
        ctx = WeatherContext(
            temperature=28.0,
            rainfall=95.0,
            wind_speed=48.0,
        )
        res = self.rule_classifier.classify(ctx)
        self.assertEqual(res.regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(res.secondary_regime, RegimeType.HIGH_WIND)

    # -------------------------------------------------------------
    # 10. Forecast Context & Spatial Integration Tests
    # -------------------------------------------------------------
    def test_build_forecast_context(self):
        """Verify building of an integrated ForecastContext."""
        fc = self.service.build_forecast_context(
            station_id="BOM",
            station_name="Mumbai Santacruz",
            latitude=19.076,
            longitude=72.877,
            lead_time_hours=24,
            temperature=29.0,
            rainfall=75.0,
            wind_speed=30.0,
            humidity=88.0,
            recent_rainfall=90.0,
        )
        self.assertIsInstance(fc, ForecastContext)
        self.assertEqual(fc.station_id, "BOM")
        self.assertEqual(fc.regime_classification.regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(fc.regime_classification.regime_name, "Heavy Rain")
        self.assertIn("rainfall", fc.weather_variables)

    def test_spatial_batch_classification(self):
        """Verify batch classification across multiple spatial contexts."""
        contexts = [
            WeatherContext(temperature=27.0, rainfall=80.0, wind_speed=20.0),  # Heavy Rain
            WeatherContext(temperature=44.0, rainfall=0.0, wind_speed=15.0),   # Heat Wave
            WeatherContext(temperature=5.0, rainfall=0.0, wind_speed=10.0),    # Cold Spell
            WeatherContext(temperature=26.0, rainfall=2.0, wind_speed=12.0),   # Normal
        ]
        results = self.service.classify_spatial(contexts)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].regime, RegimeType.HEAVY_RAIN)
        self.assertEqual(results[1].regime, RegimeType.HEAT_WAVE)
        self.assertEqual(results[2].regime, RegimeType.COLD_SPELL)
        self.assertEqual(results[3].regime, RegimeType.NORMAL)

    def test_reference_stations_snapshot(self):
        """Verify diagnostics across reference observatories."""
        station_regimes = self.service.get_reference_station_regimes()
        self.assertIn("BOM", station_regimes)
        self.assertIn("DEL", station_regimes)
        bom_res = station_regimes["BOM"]["regime_classification"]
        self.assertEqual(bom_res.regime, RegimeType.HEAVY_RAIN)

    # -------------------------------------------------------------
    # 11. REST API Endpoints Tests
    # -------------------------------------------------------------
    def test_api_classify_endpoint(self):
        """POST /api/v1/regimes/classify"""
        payload = {
            "temperature": 43.0,
            "rainfall": 0.0,
            "wind_speed": 16.0,
            "humidity": 20.0,
            "recent_rainfall": 0.0,
            "forecast_trends": {"temp_trend_24h": 1.5},
        }
        response = self.client.post("/api/v1/regimes/classify", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["regime"], "Heat Wave")
        self.assertEqual(data["regime_name"], "Heat Wave")
        self.assertGreaterEqual(data["confidence"], 0.80)
        self.assertIsInstance(data["supporting_indicators"], list)
        self.assertGreater(len(data["supporting_indicators"]), 0)

    def test_api_classify_batch_endpoint(self):
        """POST /api/v1/regimes/classify/batch"""
        payload = [
            {"temperature": 28.0, "rainfall": 75.0, "wind_speed": 22.0},
            {"temperature": 26.0, "rainfall": 1.0, "wind_speed": 10.0},
        ]
        response = self.client.post("/api/v1/regimes/classify/batch", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["regime"], "Heavy Rain")
        self.assertEqual(data[1]["regime"], "Normal")

    def test_api_types_endpoint(self):
        """GET /api/v1/regimes/types"""
        response = self.client.get("/api/v1/regimes/types")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        regime_names = [r["regime_type"] for r in data["supported_regimes"]]
        self.assertEqual(len(regime_names), 7)
        self.assertIn("Normal", regime_names)
        self.assertIn("Heavy Rain", regime_names)
        self.assertIn("Convective/Storm", regime_names)
        self.assertIn("Heat Wave", regime_names)
        self.assertIn("High Wind", regime_names)
        self.assertIn("Cold Spell", regime_names)
        self.assertIn("Dry/Extreme Dry", regime_names)

    def test_api_stations_endpoint(self):
        """GET /api/v1/regimes/stations"""
        response = self.client.get("/api/v1/regimes/stations")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("BOM", data)
        self.assertIn("regime_classification", data["BOM"])

    def test_api_forecast_context_endpoint(self):
        """POST /api/v1/regimes/forecast-context"""
        response = self.client.post(
            "/api/v1/regimes/forecast-context?station_id=BOM&lead_time_hours=24&temperature=29.0&rainfall=80.0&wind_speed=30.0"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["station_id"], "BOM")
        self.assertEqual(data["regime_classification"]["regime"], "Heavy Rain")

    def test_api_point_forecast_includes_regime_context(self):
        """GET /api/v1/forecast/point includes regime_context."""
        response = self.client.get("/api/v1/forecast/point?station_id=BOM&variable=precipitation")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("regime_context", data)
        regime_ctx = data["regime_context"]
        self.assertIsNotNone(regime_ctx)
        self.assertIn("regime_name", regime_ctx)
        self.assertIn("confidence", regime_ctx)
        self.assertIn("supporting_indicators", regime_ctx)
        self.assertIsInstance(regime_ctx["supporting_indicators"], list)


if __name__ == "__main__":
    unittest.main()
