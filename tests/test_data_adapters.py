import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

from backend.app.data.ingestion.schema import ForecastVariable
from backend.app.data.sources.factory import ForecastSourceFactory, ObservationSourceFactory
from backend.app.data.sources.forecast_adapters import (
    CSVForecastAdapter,
    DemoForecastAdapter,
    JSONForecastAdapter,
    NetCDFForecastAdapter,
    OpenMeteoForecastAdapter,
    SimulatedForecastAdapter,
)
from backend.app.data.sources.interfaces import ForecastSource, ObservationSource
from backend.app.data.sources.netcdf_parser import load_netcdf, write_test_netcdf3
from backend.app.data.sources.observation_adapters import (
    CSVObservationAdapter,
    DemoObservationAdapter,
    JSONObservationAdapter,
    NetCDFObservationAdapter,
    SimulatedObservationAdapter,
)
from backend.app.data.sources.provenance import DataCategory, DataProvenance


class TestDataProvenanceAndDistinction(unittest.TestCase):
    """
    Tests strict classification of REAL DATA, SIMULATED DATA, and DEMO DATA.
    Verifies that simulated data is never claimed or marked as real observation data.
    """

    def test_provenance_categories(self):
        real_prov = DataProvenance.create_real(
            provider="IMD AWS Network",
            description="Operational in-situ automatic weather station telemetry.",
        )
        self.assertEqual(real_prov.category, DataCategory.REAL_DATA)
        self.assertTrue(real_prov.is_real)
        self.assertFalse(real_prov.is_simulated)
        self.assertFalse(real_prov.is_demo)

        sim_prov = DataProvenance.create_simulated(
            provider="Numerical Atmosphere Physics Model",
            description="Synthetic hydrodynamic temperature simulation.",
        )
        self.assertEqual(sim_prov.category, DataCategory.SIMULATED_DATA)
        self.assertFalse(sim_prov.is_real)
        self.assertTrue(sim_prov.is_simulated)
        self.assertFalse(sim_prov.is_demo)
        self.assertIn("SIMULATED / SYNTHETIC", sim_prov.disclaimer)
        self.assertIn("NOT REAL", sim_prov.disclaimer)

        demo_prov = DataProvenance.create_demo(
            provider="Sample Benchmark Fixtures",
            description="Static CSV/JSON benchmark fixtures.",
        )
        self.assertEqual(demo_prov.category, DataCategory.DEMO_DATA)
        self.assertFalse(demo_prov.is_real)
        self.assertFalse(demo_prov.is_simulated)
        self.assertTrue(demo_prov.is_demo)

    def test_simulated_adapter_explicit_disclaimer(self):
        sim_forecast = SimulatedForecastAdapter()
        self.assertEqual(sim_forecast.data_category, DataCategory.SIMULATED_DATA)
        self.assertFalse(sim_forecast.provenance.is_real)
        self.assertTrue(sim_forecast.provenance.is_simulated)

        sim_obs = SimulatedObservationAdapter()
        self.assertEqual(sim_obs.data_category, DataCategory.SIMULATED_DATA)
        self.assertFalse(sim_obs.provenance.is_real)
        self.assertTrue(sim_obs.provenance.is_simulated)
        self.assertIn("NOT REAL", sim_obs.provenance.disclaimer)


class TestNetCDFParserAndAdapters(unittest.TestCase):
    """
    Tests NetCDF-3 binary writing, parsing, coordinate mapping, and adapter ingestion.
    """

    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.nc_path = Path(self.test_dir.name) / "forecast_test.nc"

        dims = {"time": 1, "lat": 3, "lon": 4}
        vars_dict = {
            "lat": np.array([18.9, 28.6, 12.9], dtype=np.float32),
            "lon": np.array([72.8, 77.2, 80.2, 88.3], dtype=np.float32),
            "t2m": np.array([[[298.5, 299.0, 297.5, 296.0],
                              [303.2, 304.1, 302.8, 301.5],
                              [300.1, 300.5, 299.8, 298.9]]], dtype=np.float32),
            "tp": np.array([[[12.5, 0.0, 5.2, 25.0],
                             [0.0, 0.0, 1.1, 0.0],
                             [18.0, 22.5, 8.0, 4.5]]], dtype=np.float32),
            "ws10": np.array([[[15.2, 12.0, 8.5, 22.0],
                              [9.0, 11.5, 7.8, 14.0],
                              [18.5, 16.0, 12.5, 10.0]]], dtype=np.float32),
        }
        var_dims = {
            "lat": ["lat"],
            "lon": ["lon"],
            "t2m": ["time", "lat", "lon"],
            "tp": ["time", "lat", "lon"],
            "ws10": ["time", "lat", "lon"],
        }
        write_test_netcdf3(
            output_path=self.nc_path,
            variables=vars_dict,
            dimensions=dims,
            var_dims=var_dims,
            global_attrs={"title": "IMD NCMRWF CF Test Forecast", "convention": "CF-1.6"},
            var_attrs={"t2m": {"units": "K"}, "tp": {"units": "mm"}, "ws10": {"units": "km/h"}},
        )

    def tearDown(self):
        self.test_dir.cleanup()

    def test_netcdf_dataset_loading(self):
        ds = load_netcdf(self.nc_path)
        self.assertEqual(ds.dimensions["lat"], 3)
        self.assertEqual(ds.dimensions["lon"], 4)
        self.assertIn("t2m", ds.variables)

        # Test CF synonym discovery
        t_var = ds.find_variable("temperature")
        self.assertIsNotNone(t_var)
        self.assertEqual(t_var[0], "t2m")

        r_var = ds.find_variable("rainfall")
        self.assertIsNotNone(r_var)
        self.assertEqual(r_var[0], "tp")

        w_var = ds.find_variable("wind_speed")
        self.assertIsNotNone(w_var)
        self.assertEqual(w_var[0], "ws10")

    def test_netcdf_forecast_adapter(self):
        adapter = NetCDFForecastAdapter(file_or_dir_path=self.nc_path, model_name="ECMWF NetCDF Operational")
        records, report = adapter.load_file(self.nc_path)

        self.assertGreater(len(records), 0)
        self.assertEqual(report.valid_records_count, len(records))

        # Check Kelvin to Celsius conversion
        temp_recs = [r for r in records if r.forecast_variable == ForecastVariable.TEMPERATURE]
        self.assertGreater(len(temp_recs), 0)
        for r in temp_recs:
            self.assertLess(r.forecast_value, 60.0)  # Should be in Celsius (~25-32 C)
            self.assertGreater(r.forecast_value, 15.0)

    def test_netcdf_observation_adapter(self):
        adapter = NetCDFObservationAdapter(nc_path=self.nc_path, source_name="IMD 0.25 Gridded NetCDF")
        records, report = adapter.load_file(self.nc_path)

        self.assertGreater(len(records), 0)
        self.assertEqual(adapter.data_category, DataCategory.REAL_DATA)
        for r in records:
            self.assertIsNotNone(r.latitude)
            self.assertIsNotNone(r.longitude)
            if r.temperature is not None:
                self.assertLess(r.temperature, 50.0)


class TestCSVAndJSONAdapters(unittest.TestCase):
    """
    Tests CSV and JSON forecast and observation adapters on sample datasets.
    """

    def test_csv_forecast_adapter(self):
        adapter = CSVForecastAdapter(model_name="NWP Model A")
        self.assertIn("CSV", adapter.source_name)
        records, meta = adapter.fetch_forecasts(station_ids=["BOM"], lead_times=[24])
        self.assertIsInstance(records, list)
        self.assertIn("provenance", meta)

    def test_json_forecast_adapter(self):
        adapter = JSONForecastAdapter(model_name="GraphCast AI Forecast")
        records, meta = adapter.fetch_forecasts(station_ids=["BOM"], lead_times=[24])
        self.assertIsInstance(records, list)
        self.assertIn("provenance", meta)

    def test_csv_observation_adapter(self):
        adapter = CSVObservationAdapter()
        records, meta = adapter.fetch_observations(station_ids=["BOM", "DEL"])
        self.assertIsInstance(records, list)
        self.assertEqual(adapter.data_category, DataCategory.REAL_DATA)

    def test_demo_adapters(self):
        demo_f = DemoForecastAdapter()
        self.assertEqual(demo_f.data_category, DataCategory.DEMO_DATA)
        self.assertTrue(demo_f.provenance.is_demo)

        demo_obs = DemoObservationAdapter()
        self.assertEqual(demo_obs.data_category, DataCategory.DEMO_DATA)
        self.assertTrue(demo_obs.provenance.is_demo)


class TestDataSourceFactories(unittest.TestCase):
    """
    Tests ForecastSourceFactory and ObservationSourceFactory resolution
    across explicit arguments, environment variables, and defaults.
    """

    def test_factory_explicit_type(self):
        f_sim = ForecastSourceFactory.create("simulated")
        self.assertIsInstance(f_sim, SimulatedForecastAdapter)
        self.assertEqual(f_sim.data_category, DataCategory.SIMULATED_DATA)

        f_demo = ForecastSourceFactory.create("demo")
        self.assertIsInstance(f_demo, DemoForecastAdapter)
        self.assertEqual(f_demo.data_category, DataCategory.DEMO_DATA)

        o_sim = ObservationSourceFactory.create("simulated")
        self.assertIsInstance(o_sim, SimulatedObservationAdapter)
        self.assertEqual(o_sim.data_category, DataCategory.SIMULATED_DATA)

    def test_factory_env_var_override(self):
        os.environ["MOES_FORECAST_SOURCE"] = "simulated"
        os.environ["MOES_OBSERVATION_SOURCE"] = "simulated"
        try:
            f = ForecastSourceFactory.create()
            o = ObservationSourceFactory.create()
            self.assertEqual(f.data_category, DataCategory.SIMULATED_DATA)
            self.assertEqual(o.data_category, DataCategory.SIMULATED_DATA)
        finally:
            del os.environ["MOES_FORECAST_SOURCE"]
            del os.environ["MOES_OBSERVATION_SOURCE"]


if __name__ == "__main__":
    unittest.main()
