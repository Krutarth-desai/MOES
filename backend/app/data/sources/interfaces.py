from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.data.ingestion.schema import IngestionReport, StandardForecastRecord
from backend.app.data.observation.schema import ObservationIngestionReport, ObservationRecord
from backend.app.data.sources.provenance import DataCategory, DataProvenance


class ForecastSource(ABC):
    """
    Standard interface for all meteorological forecast data providers.
    Supports NetCDF, CSV, JSON formats, REST APIs, simulations, and benchmark datasets.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this forecast source or API."""
        pass

    @property
    @abstractmethod
    def data_category(self) -> DataCategory:
        """Category: REAL_DATA, SIMULATED_DATA, or DEMO_DATA."""
        pass

    @property
    @abstractmethod
    def provenance(self) -> DataProvenance:
        """Detailed provenance, methodology, and legal/scientific disclaimer."""
        pass

    @property
    @abstractmethod
    def models_provided(self) -> List[str]:
        """List of forecast model names supplied by this source."""
        pass

    @abstractmethod
    def fetch_forecasts(
        self,
        station_ids: Optional[List[str]] = None,
        variables: Optional[List[str]] = None,
        lead_times: Optional[List[int]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[StandardForecastRecord], Dict[str, Any]]:
        """
        Retrieves forecast records for the requested parameters.
        Returns:
            Tuple of (records_list, metadata_dict)
        """
        pass

    def load_file(self, file_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        """
        Optional helper method for file-based adapters (NetCDF, CSV, JSON).
        Default implementation returns empty list and clean report.
        """
        report = IngestionReport(
            source_name=self.source_name,
            source_type=self.provenance.category.value,  # type: ignore
            source_file=str(file_path),
        )
        report.mark_complete()
        return [], report


class ObservationSource(ABC):
    """
    Standard interface for meteorological ground-truth observation providers.
    Supports NetCDF reanalysis, IMD AWS CSV, JSON telemetry feeds, sensors, and archives.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this observation source."""
        pass

    @property
    @abstractmethod
    def data_category(self) -> DataCategory:
        """Category: REAL_DATA, SIMULATED_DATA, or DEMO_DATA."""
        pass

    @property
    @abstractmethod
    def provenance(self) -> DataProvenance:
        """Detailed provenance, sensor network metadata, and disclaimer."""
        pass

    @abstractmethod
    def fetch_observations(
        self,
        station_ids: Optional[List[str]] = None,
        reference_time: Optional[datetime] = None,
    ) -> Tuple[List[ObservationRecord], Dict[str, Any]]:
        """
        Retrieves observational weather records.
        Returns:
            Tuple of (records_list, metadata_dict)
        """
        pass

    def load_file(self, file_path: Path) -> Tuple[List[ObservationRecord], ObservationIngestionReport]:
        """
        Optional helper method for file-based adapters (NetCDF, CSV, JSON).
        Default implementation returns empty list and clean report.
        """
        report = ObservationIngestionReport(
            source_name=self.source_name,
            source_file=str(file_path),
        )
        report.mark_complete()
        return [], report
