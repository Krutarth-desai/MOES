"""
Data Sources & Adapters Module for Meteorological Datasets.
Supports:
- NetCDF (Classic NetCDF-3 binary and NetCDF-4)
- CSV (IMD AWS bulletins, tabular model outputs)
- JSON (GeoJSON, REST API payloads)
- Real Operational APIs (Open-Meteo, ECMWF, GFS)
- Simulations (Synthetic physics-based profiles)
- Benchmark Demos (Packaged test fixtures)

Strictly distinguishes between REAL DATA, SIMULATED DATA, and DEMO DATA.
"""

from backend.app.data.sources.factory import (
    ForecastSourceFactory,
    ObservationSourceFactory,
    load_data_source_config,
)
from backend.app.data.sources.forecast_adapters import (
    CSVForecastAdapter,
    DemoForecastAdapter,
    JSONForecastAdapter,
    NetCDFForecastAdapter,
    OpenMeteoForecastAdapter,
    SimulatedForecastAdapter,
)
from backend.app.data.sources.interfaces import ForecastSource, ObservationSource
from backend.app.data.sources.netcdf_parser import (
    NetCDFDataset,
    PurePythonNetCDF3Reader,
    load_netcdf,
    write_test_netcdf3,
)
from backend.app.data.sources.observation_adapters import (
    CSVObservationAdapter,
    DemoObservationAdapter,
    JSONObservationAdapter,
    NetCDFObservationAdapter,
    OpenMeteoObservationAdapter,
    SimulatedObservationAdapter,
)
from backend.app.data.sources.provenance import DataCategory, DataProvenance

__all__ = [
    # Interfaces
    "ForecastSource",
    "ObservationSource",
    # Provenance
    "DataCategory",
    "DataProvenance",
    # NetCDF
    "NetCDFDataset",
    "load_netcdf",
    "write_test_netcdf3",
    "PurePythonNetCDF3Reader",
    # Forecast Adapters
    "NetCDFForecastAdapter",
    "CSVForecastAdapter",
    "JSONForecastAdapter",
    "OpenMeteoForecastAdapter",
    "SimulatedForecastAdapter",
    "DemoForecastAdapter",
    # Observation Adapters
    "NetCDFObservationAdapter",
    "CSVObservationAdapter",
    "JSONObservationAdapter",
    "OpenMeteoObservationAdapter",
    "SimulatedObservationAdapter",
    "DemoObservationAdapter",
    # Factories
    "ForecastSourceFactory",
    "ObservationSourceFactory",
    "load_data_source_config",
]
