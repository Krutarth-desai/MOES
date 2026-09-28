from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.app.data.ingestion.schema import StandardForecastRecord
from backend.app.data.observation.schema import ObservationRecord
from backend.app.data.sources.interfaces import ForecastSource, ObservationSource
from backend.app.data.sources.provenance import DataCategory, DataProvenance
from backend.app.pipeline.schemas import PipelineExecutionReport


class ForecastSourceInterface(ForecastSource):
    """
    Modular interface for forecast data providers.
    Allows prototype CSV/JSON file readers and simulated feeds to be seamlessly
    swapped out for real operational meteorological APIs (IMD GTS, NOAA GFS NOMADS,
    ECMWF Open Data, Open-Meteo, NetCDF, etc.).
    """

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return DataProvenance.create_demo(provider=self.source_name, description="Pipeline forecast data source")


class ObservationSourceInterface(ObservationSource):
    """
    Modular interface for ground-truth weather observation providers.
    Allows prototype CSV/JSON datasets to be swapped out for real IMD Automatic
    Weather Stations (AWS), WMO GTS Metar/Synop feeds, NetCDF archives, or state disaster network sensors.
    """

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.DEMO_DATA

    @property
    def provenance(self) -> DataProvenance:
        return DataProvenance.create_demo(provider=self.source_name, description="Pipeline observation data source")

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the observation data source or API."""
        pass

    @abstractmethod
    def fetch_observations(
        self,
        station_ids: Optional[List[str]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ObservationRecord], Dict[str, Any]]:
        """
        Retrieves ground-truth meteorological observation records.
        Returns:
            Tuple of (records_list, metadata_dict)
        """
        pass


class DashboardNotifierInterface(ABC):
    """
    Modular interface for publishing pipeline run status and telemetry
    to operational dashboards, local stores, webhooks, or messaging buses.
    """

    @property
    @abstractmethod
    def notifier_name(self) -> str:
        """Name of the dashboard notifier."""
        pass

    @abstractmethod
    def notify(self, report: PipelineExecutionReport) -> bool:
        """
        Publishes the execution report to the downstream consumer.
        Returns True on successful delivery.
        """
        pass
