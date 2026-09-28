import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.weighting.mapping import (
    DEFAULT_MODELS,
    METEOROLOGICAL_REGIONS,
    MODEL_COLORS,
    ModelWeightMappingEngine,
)
from backend.app.services.weighting.schemas import (
    PointWeightRequest,
    RegionalSummaryResponse,
    RegionWeightSummary,
    SpatialWeightGridResponse,
    WeightGridCell,
)


class TestModelWeightMapping(unittest.TestCase):
    """
    Test suite for the Model Weight Mapping module.
    
    Verifies:
    1. Geographic coordinate to region classification
    2. Weight calculations for arbitrary (lat, lon, variable, lead_time, season, regime)
    3. Simplex constraint (weights sum strictly to 1.0000 across all grid points)
    4. Contextual dominance (different models lead under different environmental conditions)
    5. Anti-monopoly governance (no single model declared 'best' globally)
    6. Regional reliability summary formatting:
       Region A:
       Model A = 0.52
       Model B = 0.28
       Model C = 0.20
    7. Full FastAPI endpoint integration (/grid, /regional-summary, /point)
    """

    def setUp(self):
        self.engine = ModelWeightMappingEngine()
        self.client = TestClient(app)

    # -------------------------------------------------------------------------
    # 1. Coordinate Classification Tests
    # -------------------------------------------------------------------------
    def test_classify_region_himalayas(self):
        reg_id, reg_name, elev = self.engine.classify_region(34.0, 75.0)
        self.assertEqual(reg_id, "himalayan")
        self.assertIn("Himalayan", reg_name)
        self.assertGreaterEqual(elev, 1500)

    def test_classify_region_western_ghats(self):
        reg_id, reg_name, elev = self.engine.classify_region(14.5, 74.2)
        self.assertEqual(reg_id, "western_ghats")
        self.assertIn("Western Ghats", reg_name)

    def test_classify_region_plains(self):
        reg_id, reg_name, elev = self.engine.classify_region(28.6, 77.2)
        self.assertEqual(reg_id, "plains")
        self.assertIn("Plains", reg_name)

    def test_classify_region_arid_west(self):
        reg_id, reg_name, elev = self.engine.classify_region(26.5, 71.0)
        self.assertEqual(reg_id, "arid_west")
        self.assertIn("Arid", reg_name)

    def test_classify_region_coastal_east(self):
        reg_id, reg_name, elev = self.engine.classify_region(19.8, 85.8)
        self.assertEqual(reg_id, "coastal_east")
        self.assertIn("Coastal", reg_name)

    # -------------------------------------------------------------------------
    # 2. Point Weight Calculation & Simplex Constraint
    # -------------------------------------------------------------------------
    def test_point_weights_sum_to_one(self):
        """Proof that sum of model weights strictly equals 1.0000 at any coordinate."""
        test_points = [
            (18.9, 72.8, "rainfall", 24),     # Mumbai
            (28.6, 77.2, "temperature", 48),  # Delhi
            (20.3, 85.8, "wind_speed", 24),   # Bhubaneswar
            (26.9, 75.8, "temperature", 96),  # Jaipur
            (12.9, 77.6, "rainfall", 72),     # Bengaluru
        ]

        for lat, lon, var, lead in test_points:
            with self.subTest(lat=lat, lon=lon, var=var, lead=lead):
                cell = self.engine.compute_cell_weights(
                    lat=lat,
                    lon=lon,
                    variable=var,
                    lead_time_hours=lead,
                )
                self.assertIsInstance(cell, WeightGridCell)
                tot_w = sum(cell.weights.values())
                self.assertAlmostEqual(tot_w, 1.0, places=3)
                self.assertIn(cell.dominant_model, cell.weights)
                self.assertGreaterEqual(cell.dominant_weight, 0.20)
                self.assertGreaterEqual(cell.weight_distribution.entropy, 0.0)
                self.assertLessEqual(cell.weight_distribution.entropy, 1.0)

    # -------------------------------------------------------------------------
    # 3. Contextual Dominance Proof (No Global "Best" Model)
    # -------------------------------------------------------------------------
    def test_contextual_dominance_western_ghats_rainfall(self):
        """In Western Ghats steep orography during monsoon rainfall, NWP Model A must lead."""
        cell = self.engine.compute_cell_weights(
            lat=15.5,
            lon=74.0,
            variable="rainfall",
            lead_time_hours=24,
            season="monsoon",
            weather_regime="heavy_rain",
        )
        self.assertEqual(cell.dominant_model, "NWP Model A")
        self.assertGreater(cell.weights["NWP Model A"], cell.weights["AI/ML Forecast"])

    def test_contextual_dominance_plains_temperature(self):
        """In continental plains for medium-range temperature, AI/ML Forecast must lead."""
        cell = self.engine.compute_cell_weights(
            lat=27.5,
            lon=79.0,
            variable="temperature",
            lead_time_hours=72,
            season="pre_monsoon",
            weather_regime="heat_wave",
        )
        self.assertEqual(cell.dominant_model, "AI/ML Forecast")
        self.assertGreater(cell.weights["AI/ML Forecast"], cell.weights["NWP Model A"])

    def test_contextual_dominance_coastal_east_wind(self):
        """In eastern coastal maritime gale winds, NWP Model B (ECMWF) must lead."""
        cell = self.engine.compute_cell_weights(
            lat=19.5,
            lon=85.5,
            variable="wind_speed",
            lead_time_hours=24,
            season="post_monsoon",
            weather_regime="high_wind",
        )
        self.assertEqual(cell.dominant_model, "NWP Model B")
        self.assertGreater(cell.weights["NWP Model B"], cell.weights["AI/ML Forecast"])

    def test_contextual_dominance_arid_west_uncertainty(self):
        """In arid zones with high convective uncertainty, Ensemble Forecast gains high weight."""
        cell = self.engine.compute_cell_weights(
            lat=26.5,
            lon=71.5,
            variable="rainfall",
            lead_time_hours=48,
            season="monsoon",
            weather_regime="convective_storm",
        )
        # Ensemble Forecast should have a high weight
        self.assertGreaterEqual(cell.weights["Ensemble Forecast"], 0.25)

    # -------------------------------------------------------------------------
    # 4. Regional Summaries & Text Formatting
    # -------------------------------------------------------------------------
    def test_regional_summary_format(self):
        """
        Verifies the summary text format:
        Region A:
        Model A = 0.52
        Model B = 0.28
        Model C = 0.20
        """
        summaries = self.engine.generate_regional_summaries(
            variable="rainfall",
            lead_time_hours=24,
            season="monsoon",
            weather_regime="normal",
        )

        self.assertGreaterEqual(len(summaries), 6)
        for s in summaries:
            self.assertIsInstance(s, RegionWeightSummary)
            tot_w = sum(s.weights.values())
            self.assertAlmostEqual(tot_w, 1.0, places=3)

            # Check formatted string structure
            lines = s.summary_formatted.strip().split("\n")
            self.assertTrue(lines[0].endswith(":"), f"Header '{lines[0]}' should end with ':'")
            self.assertGreaterEqual(len(lines), 4)

            # Verify line format: 'Model X = 0.XX'
            for model_line in lines[1:]:
                self.assertIn("=", model_line)
                parts = model_line.split("=")
                self.assertEqual(len(parts), 2)
                val = float(parts[1].strip())
                self.assertGreaterEqual(val, 0.0)
                self.assertLessEqual(val, 1.0)

            # Verify context explanation presence
            self.assertTrue(len(s.context_explanation) > 20)

    # -------------------------------------------------------------------------
    # 5. Full Spatial Grid Generation & Governance Verification
    # -------------------------------------------------------------------------
    def test_generate_spatial_weight_grid(self):
        """Verifies full spatial grid generation, coverage distribution, and anti-monopoly notice."""
        res = self.engine.generate_weight_grid(
            variable="rainfall",
            lead_time_hours=24,
            season="monsoon",
            weather_regime="normal",
            grid_resolution_deg=3.0,
        )

        self.assertIsInstance(res, SpatialWeightGridResponse)
        self.assertGreater(res.total_cells, 10)
        self.assertEqual(len(res.grid_cells), res.total_cells)
        self.assertGreaterEqual(len(res.regional_summaries), 6)

        # Governance verification: No model is declared 'best' globally
        self.assertIn("No model is labeled or treated as globally 'best'", res.contextual_governance_notice)

        # Macro distribution stats should show shared dominance across models
        stats = res.overall_distribution
        coverage = stats.get("dominant_model_coverage_pct", {})
        self.assertGreater(len(coverage), 1, "Dominance should be shared across multiple models")

    # -------------------------------------------------------------------------
    # 6. FastAPI Endpoints Integration
    # -------------------------------------------------------------------------
    def test_api_get_weight_grid(self):
        response = self.client.get(
            "/api/v1/weights/grid",
            params={
                "variable": "rainfall",
                "lead_time_hours": 24,
                "season": "monsoon",
                "weather_regime": "normal",
                "resolution_deg": 3.0,
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["variable"], "rainfall")
        self.assertIn("grid_cells", data)
        self.assertGreater(len(data["grid_cells"]), 0)
        self.assertIn("regional_summaries", data)
        self.assertIn("contextual_governance_notice", data)

    def test_api_get_regional_summary(self):
        response = self.client.get(
            "/api/v1/weights/regional-summary",
            params={
                "variable": "temperature",
                "lead_time_hours": 48,
                "season": "monsoon",
                "weather_regime": "normal",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("summaries", data)
        self.assertIn("all_formatted_text", data)
        self.assertIn("Western Ghats", data["all_formatted_text"])
        self.assertIn("Indo-Gangetic Plains", data["all_formatted_text"])
        self.assertIn("=", data["all_formatted_text"])

    def test_api_post_point_weight(self):
        payload = {
            "latitude": 19.07,
            "longitude": 72.87,
            "variable": "rainfall",
            "lead_time_hours": 24,
            "season": "monsoon",
            "weather_regime": "heavy_rain",
        }
        response = self.client.post("/api/v1/weights/point", json=payload)
        self.assertEqual(response.status_code, 200)
        cell = response.json()
        self.assertEqual(cell["region_id"], "western_ghats")
        self.assertIn("weights", cell)
        self.assertAlmostEqual(sum(cell["weights"].values()), 1.0, places=2)
        self.assertEqual(cell["dominant_model"], "NWP Model A")


if __name__ == "__main__":
    unittest.main()
