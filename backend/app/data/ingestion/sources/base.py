from abc import ABC, abstractmethod
from typing import List, Tuple
from pathlib import Path
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    IngestionReport,
    StandardForecastRecord,
)


class BaseForecastSource(ABC):
    """
    Common ForecastSource Interface.
    Enables modular plug-and-play ingestion for:
    - NWP Model A (e.g. GFS)
    - NWP Model B (e.g. ECMWF IFS)
    - Ensemble Forecasts (e.g. GEFS / EPS)
    - AI/ML Forecasts (e.g. GraphCast / Pangu)
    - Ground Truth Observations (e.g. IMD Gridded / AWS)
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable identifier for this model / source."""
        pass

    @property
    @abstractmethod
    def source_type(self) -> ForecastSourceType:
        """Model category: NWP, ENSEMBLE, AI, or OBSERVATION."""
        pass

    @abstractmethod
    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        """
        Load, validate, normalize units, and return canonical forecast records.
        """
        pass
