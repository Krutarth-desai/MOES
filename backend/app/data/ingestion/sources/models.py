from pathlib import Path
from typing import List, Tuple
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    IngestionReport,
    StandardForecastRecord,
)
from backend.app.data.ingestion.sources.base import BaseForecastSource
from backend.app.data.ingestion.sources.csv_source import CSVForecastSource
from backend.app.data.ingestion.sources.json_source import JSONForecastSource


class NWPModelASource(BaseForecastSource):
    """
    NWP Model A (Global Physics Model - GFS-like).
    High spatial responsiveness; slight positive wet bias on convective rainfall.
    """

    @property
    def source_name(self) -> str:
        return "NWP Model A (GFS-like)"

    @property
    def source_type(self) -> ForecastSourceType:
        return ForecastSourceType.NWP

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        reader = CSVForecastSource(name=self.source_name, source_type=self.source_type)
        return reader.load(source_path)


class NWPModelBSource(BaseForecastSource):
    """
    NWP Model B (Global Physics Model - ECMWF-like).
    High synoptic consistency; conservative peak convective extremes.
    """

    @property
    def source_name(self) -> str:
        return "NWP Model B (ECMWF-like)"

    @property
    def source_type(self) -> ForecastSourceType:
        return ForecastSourceType.NWP

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        reader = CSVForecastSource(name=self.source_name, source_type=self.source_type)
        return reader.load(source_path)


class EnsembleForecastSource(BaseForecastSource):
    """
    Multi-Member Ensemble Forecast (EPS / GEFS-like).
    Probabilistic ensemble mean with uncertainty spread.
    """

    @property
    def source_name(self) -> str:
        return "Ensemble Forecast (GEFS/EPS-like)"

    @property
    def source_type(self) -> ForecastSourceType:
        return ForecastSourceType.ENSEMBLE

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        reader = CSVForecastSource(name=self.source_name, source_type=self.source_type)
        return reader.load(source_path)


class AIForecastSource(BaseForecastSource):
    """
    Deep Neural Weather Model (GraphCast / Pangu-like).
    High short-range non-linear skill; rapid inference; spatial smoothing at long leads.
    """

    @property
    def source_name(self) -> str:
        return "AI/ML Forecast (GraphCast-like)"

    @property
    def source_type(self) -> ForecastSourceType:
        return ForecastSourceType.AI

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        # AI models commonly output GeoJSON or JSON feature dictionaries
        if str(source_path).endswith(".json"):
            reader = JSONForecastSource(name=self.source_name, source_type=self.source_type)
        else:
            reader = CSVForecastSource(name=self.source_name, source_type=self.source_type)
        return reader.load(source_path)


class ObservationSource(BaseForecastSource):
    """
    Ground Truth Meteorological Observation Reference (IMD Gridded / AWS).
    Used for historical skill calibration and benchmark verification.
    """

    @property
    def source_name(self) -> str:
        return "Ground Truth Observation (IMD Benchmark)"

    @property
    def source_type(self) -> ForecastSourceType:
        return ForecastSourceType.OBSERVATION

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        reader = CSVForecastSource(name=self.source_name, source_type=self.source_type)
        return reader.load(source_path)
