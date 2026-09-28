import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from backend.app.config.settings import CONFIG_DIR, DATA_DIR
from backend.app.data.sources.forecast_adapters import (
    CSVForecastAdapter,
    DemoForecastAdapter,
    JSONForecastAdapter,
    NetCDFForecastAdapter,
    OpenMeteoForecastAdapter,
    SimulatedForecastAdapter,
)
from backend.app.data.sources.interfaces import ForecastSource, ObservationSource
from backend.app.data.sources.observation_adapters import (
    CSVObservationAdapter,
    DemoObservationAdapter,
    JSONObservationAdapter,
    NetCDFObservationAdapter,
    OpenMeteoObservationAdapter,
    SimulatedObservationAdapter,
)
from backend.app.data.sources.provenance import DataCategory, DataProvenance

logger = logging.getLogger("moes.data.sources.factory")


def load_data_source_config() -> Dict[str, Any]:
    """
    Loads data source configuration from yaml or json config file if present,
    falling back to sensible environment defaults.
    """
    yaml_config = CONFIG_DIR / "data_sources.yaml"
    json_config = CONFIG_DIR / "data_sources.json"

    cfg: Dict[str, Any] = {}
    if yaml_config.exists():
        try:
            with open(yaml_config, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Error reading %s: %s", yaml_config, e)
    elif json_config.exists():
        try:
            with open(json_config, "r", encoding="utf-8") as f:
                cfg = json.load(f) or {}
        except Exception as e:
            logger.warning("Error reading %s: %s", json_config, e)

    return cfg


class ForecastSourceFactory:
    """
    Factory creating configured ForecastSource instances based on:
    1. Explicit function arguments
    2. Environment variables (MOES_FORECAST_SOURCE, MOES_FORECAST_PATH, MOES_DATA_CATEGORY)
    3. Configuration files (configs/data_sources.yaml)
    4. Default demo/hybrid fallback
    """

    @classmethod
    def create(
        cls,
        source_type: Optional[str] = None,
        path: Optional[Union[str, Path]] = None,
        category: Optional[Union[str, DataCategory]] = None,
        **kwargs: Any,
    ) -> ForecastSource:
        cfg = load_data_source_config().get("forecast_source", {})

        # Resolve type in priority: argument -> env var -> config file -> default
        st = (
            source_type
            or os.environ.get("MOES_FORECAST_SOURCE")
            or os.environ.get("FORECAST_SOURCE_TYPE")
            or cfg.get("type")
            or "demo"
        ).lower().strip()

        # Resolve path
        resolved_path = (
            Path(path)
            if path
            else Path(os.environ.get("MOES_FORECAST_PATH") or cfg.get("path") or (DATA_DIR / "sample"))
        )

        # Resolve data category override if specified
        cat_str = (
            str(category.value if isinstance(category, DataCategory) else category)
            if category
            else os.environ.get("MOES_DATA_CATEGORY") or cfg.get("category")
        )

        logger.info("Instantiating ForecastSource type '%s' from path '%s'", st, resolved_path)

        if st in ("netcdf", "real_netcdf", "nc"):
            prov = DataProvenance.create_real(
                provider="Operational NetCDF NWP",
                description=f"NetCDF forecast dataset loaded from {resolved_path}",
            )
            return NetCDFForecastAdapter(file_or_dir_path=resolved_path, provenance=prov)

        elif st in ("csv", "real_csv"):
            prov = (
                DataProvenance.create_real(provider="Operational CSV NWP Feed", description=f"CSV from {resolved_path}")
                if cat_str and "REAL" in cat_str.upper()
                else DataProvenance.create_demo(description=f"CSV forecast from {resolved_path}")
            )
            return CSVForecastAdapter(csv_path=resolved_path, provenance=prov)

        elif st in ("json", "real_json", "geojson"):
            prov = (
                DataProvenance.create_real(provider="Operational JSON NWP Feed", description=f"JSON from {resolved_path}")
                if cat_str and "REAL" in cat_str.upper()
                else DataProvenance.create_demo(description=f"JSON forecast from {resolved_path}")
            )
            return JSONForecastAdapter(json_path=resolved_path, provenance=prov)

        elif st in ("openmeteo", "real_api", "api"):
            return OpenMeteoForecastAdapter()

        elif st in ("simulated", "simulation", "synth"):
            return SimulatedForecastAdapter()

        elif st in ("demo", "demo_file", "sample"):
            return DemoForecastAdapter(sample_dir=resolved_path)

        elif st in ("hybrid", "default"):
            from backend.app.pipeline.sources import HybridForecastSource
            # HybridForecastSource complies with ForecastSource
            return HybridForecastSource(data_dir=resolved_path)  # type: ignore

        else:
            logger.warning("Unrecognized forecast source type '%s'. Falling back to DemoForecastAdapter.", st)
            return DemoForecastAdapter(sample_dir=resolved_path)


class ObservationSourceFactory:
    """
    Factory creating configured ObservationSource instances based on:
    1. Explicit function arguments
    2. Environment variables (MOES_OBSERVATION_SOURCE, MOES_OBSERVATION_PATH, MOES_DATA_CATEGORY)
    3. Configuration files (configs/data_sources.yaml)
    4. Default demo/hybrid fallback
    """

    @classmethod
    def create(
        cls,
        source_type: Optional[str] = None,
        path: Optional[Union[str, Path]] = None,
        category: Optional[Union[str, DataCategory]] = None,
        **kwargs: Any,
    ) -> ObservationSource:
        cfg = load_data_source_config().get("observation_source", {})

        st = (
            source_type
            or os.environ.get("MOES_OBSERVATION_SOURCE")
            or os.environ.get("OBSERVATION_SOURCE_TYPE")
            or cfg.get("type")
            or "demo"
        ).lower().strip()

        resolved_path = (
            Path(path)
            if path
            else Path(os.environ.get("MOES_OBSERVATION_PATH") or cfg.get("path") or (DATA_DIR / "sample"))
        )

        cat_str = (
            str(category.value if isinstance(category, DataCategory) else category)
            if category
            else os.environ.get("MOES_DATA_CATEGORY") or cfg.get("category")
        )

        logger.info("Instantiating ObservationSource type '%s' from path '%s'", st, resolved_path)

        if st in ("netcdf", "real_netcdf", "nc"):
            prov = DataProvenance.create_real(
                provider="IMD Gridded NetCDF Observation",
                description=f"NetCDF ground-truth observation loaded from {resolved_path}",
            )
            return NetCDFObservationAdapter(nc_path=resolved_path, provenance=prov)

        elif st in ("csv", "real_csv"):
            prov = (
                DataProvenance.create_real(provider="IMD AWS Network", description=f"AWS CSV from {resolved_path}")
                if cat_str and "REAL" in cat_str.upper()
                else DataProvenance.create_demo(description=f"Observation CSV from {resolved_path}")
            )
            return CSVObservationAdapter(csv_path=resolved_path, provenance=prov)

        elif st in ("json", "real_json"):
            prov = (
                DataProvenance.create_real(provider="AWS Telemetry JSON", description=f"Observation JSON from {resolved_path}")
                if cat_str and "REAL" in cat_str.upper()
                else DataProvenance.create_demo(description=f"Observation JSON from {resolved_path}")
            )
            return JSONObservationAdapter(json_path=resolved_path, provenance=prov)

        elif st in ("openmeteo", "real_api", "api"):
            return OpenMeteoObservationAdapter()

        elif st in ("simulated", "simulation", "synth"):
            return SimulatedObservationAdapter()

        elif st in ("demo", "demo_file", "sample"):
            return DemoObservationAdapter(sample_dir=resolved_path)

        elif st in ("hybrid", "default"):
            from backend.app.pipeline.sources import HybridObservationSource
            return HybridObservationSource(data_dir=resolved_path)  # type: ignore

        else:
            logger.warning("Unrecognized observation source type '%s'. Falling back to DemoObservationAdapter.", st)
            return DemoObservationAdapter(sample_dir=resolved_path)
