import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config.settings import DATA_DIR
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    ForecastVariable,
    Season,
    StandardForecastRecord,
)
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.schema import ObservationRecord
from backend.app.data.stations import REFERENCE_STATIONS, get_all_stations, get_station_by_id
from backend.app.pipeline.interfaces import (
    DashboardNotifierInterface,
    ForecastSourceInterface,
    ObservationSourceInterface,
)
from backend.app.data.sources.provenance import DataCategory, DataProvenance
from backend.app.pipeline.schemas import PipelineExecutionReport
from backend.app.services.simulated_provider import SimulatedForecastProvider

logger = logging.getLogger("moes.pipeline.sources")


class FileForecastSource(ForecastSourceInterface):
    """
    Ingests forecast records from local CSV and JSON datasets
    (e.g., nwp_model_a.csv, nwp_model_b.csv, ensemble_forecast.csv, ai_forecast.json).
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or (DATA_DIR / "sample")
        self._pipeline = IngestionPipeline()
        self._models = [
            "NWP Model A",
            "NWP Model B",
            "Ensemble Forecast",
            "AI Forecast",
        ]
        self._provenance = DataProvenance.create_demo(
            provider=f"FileForecastSource ({self._data_dir})",
            description="Static benchmark demonstration forecast fixture from sample directory.",
        )

    @property
    def source_name(self) -> str:
        return f"FileForecastSource ({self._data_dir})"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._provenance

    @property
    def models_provided(self) -> List[str]:
        return self._models

    def fetch_forecasts(
        self,
        station_ids: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        lead_times: Optional[List[int]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[StandardForecastRecord], Dict[str, Any]]:
        self._pipeline.clear()
        reports = self._pipeline.ingest_directory(self._data_dir)
        records = self._pipeline.get_all_records()

        # Apply filtering if requested
        if station_ids:
            s_set = {s.upper() for s in station_ids}
            records = [r for r in records if r.station_id and r.station_id.upper() in s_set]

        if variables:
            v_set = {v.lower() for v in variables}
            records = [r for r in records if r.forecast_variable.value in v_set]

        if lead_times:
            lt_set = set(lead_times)
            records = [r for r in records if r.lead_time_hours in lt_set]

        metadata = {
            "source_type": "file",
            "directory": str(self._data_dir),
            "files_ingested": len(reports),
            "raw_records_found": len(records),
            "reports": [r.model_dump(mode="json") for r in reports],
        }
        return records, metadata


class SimulatedForecastSource(ForecastSourceInterface):
    """
    Generates physically consistent multi-model forecast records on demand
    using the SimulatedForecastProvider. Serves as a reliable source for testing
    and operational fallback.
    """

    def __init__(self, provider: Optional[SimulatedForecastProvider] = None):
        self._provider = provider or SimulatedForecastProvider()
        self._models = [
            "NWP Model A",
            "NWP Model B",
            "Ensemble Forecast",
            "AI Forecast",
        ]
        self._provenance = DataProvenance.create_simulated(
            provider="SimulatedForecastProvider (Realistic Physics Model)",
            description="Physics-based numerical simulation of GFS, ECMWF, GraphCast, and Pangu forecasts.",
        )

    @property
    def source_name(self) -> str:
        return "SimulatedForecastProvider (Realistic Physics Model)"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.SIMULATED_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._provenance

    @property
    def models_provided(self) -> List[str]:
        return self._models

    def fetch_forecasts(
        self,
        station_ids: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        lead_times: Optional[List[int]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[StandardForecastRecord], Dict[str, Any]]:
        ref_time = reference_time or datetime.now()
        target_stations = station_ids or list(REFERENCE_STATIONS.keys())
        target_variables = variables or ["rainfall", "temperature", "wind_speed", "wind_direction"]
        target_leads = lead_times or [6, 12, 24, 48]

        records: List[StandardForecastRecord] = []
        for sid in target_stations:
            st = get_station_by_id(sid)
            if not st:
                continue

            for lt in target_leads:
                valid_time = ref_time + timedelta(hours=lt)

                for var in target_variables:
                    var_clean = var.lower()
                    if "dir" in var_clean:
                        base_dir = (210.0 + (st.lat * 3.5) + (lt * 2.0)) % 360.0
                        m_a = round((base_dir + 5.0) % 360.0, 1)
                        m_b = round((base_dir - 4.0) % 360.0, 1)
                        ens = round((base_dir + 1.0) % 360.0, 1)
                        ai = round((base_dir - 2.0) % 360.0, 1)
                    else:
                        from backend.app.models.domain import WeatherVariable
                        w_var = (
                            WeatherVariable.PRECIPITATION if "rain" in var_clean
                            else (WeatherVariable.TEMPERATURE_2M if "temp" in var_clean
                                  else WeatherVariable.WIND_SPEED_10M)
                        )
                        pt = self._provider.get_point_forecast(st.lat, st.lon, w_var, [lt])
                        m_a = pt["gfs"].get(lt, 25.0)
                        m_b = pt["ecmwf"].get(lt, 25.0)
                        ens = pt["pangu"].get(lt, 25.0)
                        ai = pt["graphcast"].get(lt, 25.0)

                    model_pairs = [
                        ("NWP Model A", m_a),
                        ("NWP Model B", m_b),
                        ("Ensemble Forecast", ens),
                        ("AI Forecast", ai),
                    ]

                    # Map variable string to enum
                    var_enum = (
                        ForecastVariable.RAINFALL if "rain" in var
                        else (ForecastVariable.TEMPERATURE if "temp" in var
                              else (ForecastVariable.WIND_SPEED if "speed" in var or "wind" in var
                                    else ForecastVariable.WIND_DIRECTION))
                    )

                    unit = "°C" if var_enum == ForecastVariable.TEMPERATURE else ("mm" if var_enum == ForecastVariable.RAINFALL else ("km/h" if var_enum == ForecastVariable.WIND_SPEED else "degrees"))

                    for m_name, val in model_pairs:
                        records.append(
                            StandardForecastRecord(
                                source_name=m_name,
                                forecast_variable=var_enum,
                                forecast_value=round(val, 2),
                                raw_unit=unit,
                                latitude=st.lat,
                                longitude=st.lon,
                                station_id=sid,
                                region=st.region_type,
                                initialization_time=ref_time,
                                timestamp=valid_time,
                                lead_time_hours=lt,
                                season=Season.MONSOON,
                            )
                        )

        metadata = {
            "source_type": "simulated",
            "stations_count": len(target_stations),
            "variables_count": len(target_variables),
            "lead_times_count": len(target_leads),
            "generated_records": len(records),
        }
        return records, metadata


class HybridForecastSource(ForecastSourceInterface):
    """
    Composite forecast source that preferentially ingests from local files
    and supplements any missing stations or variables with simulated records.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._file_source = FileForecastSource(data_dir=data_dir)
        self._sim_source = SimulatedForecastSource()

    @property
    def source_name(self) -> str:
        return f"HybridForecastSource [Primary: {self._file_source.source_name} | Fallback: {self._sim_source.source_name}]"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._file_source.provenance

    @property
    def models_provided(self) -> List[str]:
        return self._sim_source.models_provided

    def fetch_forecasts(
        self,
        station_ids: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        lead_times: Optional[List[int]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[StandardForecastRecord], Dict[str, Any]]:
        # Try file source first
        file_records, file_meta = self._file_source.fetch_forecasts(
            station_ids=station_ids,
            variables=variables,
            lead_times=lead_times,
            reference_time=reference_time,
        )

        if len(file_records) >= 50:
            file_meta["strategy"] = "file_complete"
            return file_records, file_meta

        # Fallback or supplement with simulation
        logger.info("File records sparse (%d found). Supplementing with simulated provider.", len(file_records))
        sim_records, sim_meta = self._sim_source.fetch_forecasts(
            station_ids=station_ids,
            variables=variables,
            lead_times=lead_times,
            reference_time=reference_time,
        )

        combined = file_records + sim_records
        metadata = {
            "strategy": "hybrid_combined",
            "file_records_count": len(file_records),
            "sim_records_count": len(sim_records),
            "total_records": len(combined),
        }
        return combined, metadata


# -----------------------------------------------------------------------------
# Observation Sources
# -----------------------------------------------------------------------------

class FileObservationSource(ObservationSourceInterface):
    """
    Ingests ground-truth observations from local CSV and JSON files
    using ObservationIngestionService.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._data_dir = data_dir or (DATA_DIR / "sample")
        self._service = ObservationIngestionService()
        self._provenance = DataProvenance.create_demo(
            provider=f"FileObservationSource ({self._data_dir})",
            description="Static benchmark ground-truth observation sample files.",
        )

    @property
    def source_name(self) -> str:
        return f"FileObservationSource ({self._data_dir})"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._provenance

    def fetch_observations(
        self,
        station_ids: Optional[List[str]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ObservationRecord], Dict[str, Any]]:
        # Search for observation files in data_dir
        obs_files = [
            f for f in (list(self._data_dir.glob("*.csv")) + list(self._data_dir.glob("*.json")))
            if "obs" in f.name.lower() or "ground_truth" in f.name.lower()
        ]

        all_records: List[ObservationRecord] = []
        reports = []

        for f in obs_files:
            try:
                recs, rep = self._service.load_file(f)
                all_records.extend(recs)
                reports.append(rep)
            except Exception as e:
                logger.warning("Error ingesting observation file %s: %s", f.name, e)

        # Apply station filtering
        if station_ids:
            s_set = {s.upper() for s in station_ids}
            all_records = [r for r in all_records if r.station_id and r.station_id.upper() in s_set]

        metadata = {
            "source_type": "file_observations",
            "files_ingested": [f.name for f in obs_files],
            "total_records": len(all_records),
        }
        return all_records, metadata


class SimulatedObservationSource(ObservationSourceInterface):
    """
    Generates realistic observational measurements for reference stations.
    """

    def __init__(self):
        self._provenance = DataProvenance.create_simulated(
            provider="SimulatedObservationSource (AWS Station Telemetry)",
            description="Synthetic observational measurements generated for reference stations.",
        )

    @property
    def source_name(self) -> str:
        return "SimulatedObservationSource (AWS Station Telemetry)"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.SIMULATED_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._provenance

    def fetch_observations(
        self,
        station_ids: Optional[List[str]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ObservationRecord], Dict[str, Any]]:
        now = reference_time or datetime.now()
        target_stations = station_ids or list(REFERENCE_STATIONS.keys())

        records: List[ObservationRecord] = []
        for sid in target_stations:
            st = get_station_by_id(sid)
            if not st:
                continue

            records.append(
                ObservationRecord(
                    station_id=sid,
                    station_name=st.name,
                    latitude=st.lat,
                    longitude=st.lon,
                    timestamp=now,
                    temperature=28.5 if "Coastal" in st.region_type else 34.0,
                    rainfall=15.0 if "Western" in st.region_type else 0.0,
                    wind_speed=18.0,
                    wind_direction=240.0,
                    humidity=82.0,
                    pressure=1008.5,
                    region=st.region_type,
                    elevation_m=st.elevation_m,
                    source="SIMULATED_AWS",
                )
            )

        metadata = {
            "source_type": "simulated_observations",
            "stations_count": len(target_stations),
            "records_generated": len(records),
        }
        return records, metadata


class HybridObservationSource(ObservationSourceInterface):
    """
    Composite observation source that tries file ingestion first,
    falling back to simulated observations if no files exist.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self._file_source = FileObservationSource(data_dir=data_dir)
        self._sim_source = SimulatedObservationSource()

    @property
    def source_name(self) -> str:
        return f"HybridObservationSource [Primary: {self._file_source.source_name} | Fallback: {self._sim_source.source_name}]"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return self._file_source.provenance

    def fetch_observations(
        self,
        station_ids: Optional[List[str]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ObservationRecord], Dict[str, Any]]:
        file_recs, file_meta = self._file_source.fetch_observations(
            station_ids=station_ids,
            reference_time=reference_time,
        )

        if file_recs:
            file_meta["strategy"] = "file_complete"
            return file_recs, file_meta

        sim_recs, sim_meta = self._sim_source.fetch_observations(
            station_ids=station_ids,
            reference_time=reference_time,
        )
        metadata = {
            "strategy": "simulated_fallback",
            "sim_records_count": len(sim_recs),
            "total_records": len(sim_recs),
        }
        return sim_recs, metadata


# -----------------------------------------------------------------------------
# Dashboard Notifiers
# -----------------------------------------------------------------------------

class LocalJsonDashboardNotifier(DashboardNotifierInterface):
    """
    Persists latest pipeline run telemetry and summaries to JSON files
    for live dashboard rendering and historical tracking.
    """

    def __init__(self, processed_dir: Optional[Path] = None):
        self._processed_dir = processed_dir or (DATA_DIR / "processed")
        self._latest_file = self._processed_dir / "latest_pipeline_run.json"
        self._history_file = self._processed_dir / "pipeline_history.json"

    @property
    def notifier_name(self) -> str:
        return f"LocalJsonDashboardNotifier ({self._latest_file})"

    def notify(self, report: PipelineExecutionReport) -> bool:
        try:
            self._processed_dir.mkdir(parents=True, exist_ok=True)
            report_dict = report.model_dump(mode="json")

            # 1. Write latest pipeline run file
            with open(self._latest_file, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=str)

            # 2. Append to pipeline history file
            history: List[Dict[str, Any]] = []
            if self._history_file.exists():
                try:
                    with open(self._history_file, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    history = []

            # Keep last 50 execution runs in history
            history.append(report_dict)
            history = history[-50:]

            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, default=str)

            logger.info("Dashboard updated successfully via %s", self._latest_file)
            return True
        except Exception as e:
            logger.error("Failed to notify dashboard: %s", e)
            return False
