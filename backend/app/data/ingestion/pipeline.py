import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Type
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    ForecastVariable,
    IngestionReport,
    StandardForecastRecord,
)
from backend.app.data.ingestion.sources.base import BaseForecastSource
from backend.app.data.ingestion.sources.models import (
    AIForecastSource,
    EnsembleForecastSource,
    NWPModelASource,
    NWPModelBSource,
    ObservationSource,
)

logger = logging.getLogger("moes.ingestion.pipeline")


class IngestionPipeline:
    """
    Master Ingestion and Preprocessing Pipeline.
    Coordinates multiple diverse forecast sources (NWP, Ensemble, AI, Observations),
    executes unit normalization, applies validation rules, imputes missing values,
    and stores records ready for downstream blending and verification.
    """

    def __init__(self):
        self._sources: Dict[str, BaseForecastSource] = {
            "nwp_model_a": NWPModelASource(),
            "nwp_model_b": NWPModelBSource(),
            "ensemble_forecast": EnsembleForecastSource(),
            "ai_forecast": AIForecastSource(),
            "ground_truth": ObservationSource(),
        }
        self._records_store: List[StandardForecastRecord] = []
        self._reports_history: List[IngestionReport] = []

    def register_source(self, key: str, source_instance: BaseForecastSource):
        """Register a custom or third-party forecast source."""
        self._sources[key.lower()] = source_instance
        logger.info("Registered new forecast source: '%s' (%s)", key, source_instance.source_name)

    def ingest_file(
        self,
        file_path: Path,
        source_key: Optional[str] = None,
    ) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        """
        Ingest a single forecast file using the designated or auto-inferred source.
        """
        path = Path(file_path)

        # Auto-detect source key from file stem if not provided
        if not source_key:
            stem = path.stem.lower()
            for key in self._sources:
                if key in stem:
                    source_key = key
                    break

        source = self._sources.get(source_key.lower()) if source_key else None
        if not source:
            # Fallback to default CSV or JSON reader based on extension
            if path.suffix.lower() == ".json":
                source = AIForecastSource()
            else:
                source = NWPModelASource()

        logger.info("Starting ingestion for %s via source handler '%s'", path.name, source.source_name)
        records, report = source.load(path)

        self._records_store.extend(records)
        self._reports_history.append(report)

        return records, report

    def ingest_directory(self, dir_path: Path) -> List[IngestionReport]:
        """
        Scan a directory and ingest all CSV and JSON forecast files.
        """
        folder = Path(dir_path)
        reports = []
        if not folder.exists() or not folder.is_dir():
            logger.warning("Directory %s does not exist or is not a directory", dir_path)
            return reports

        # Ingest forecast files (ignoring observation datasets)
        files = [
            f for f in (list(folder.glob("*.csv")) + list(folder.glob("*.json")))
            if not f.stem.lower().startswith("observation")
        ]
        for f in files:
            _, report = self.ingest_file(f)
            reports.append(report)

        return reports

    def get_all_records(self) -> List[StandardForecastRecord]:
        return self._records_store

    def query_records(
        self,
        variable: Optional[ForecastVariable] = None,
        lead_time_hours: Optional[int] = None,
        source_name: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[StandardForecastRecord]:
        """
        Filter ingested records by variable, lead time, source, or region.
        """
        results = self._records_store

        if variable:
            results = [r for r in results if r.forecast_variable == variable]
        if lead_time_hours is not None:
            results = [r for r in results if r.lead_time_hours == lead_time_hours]
        if source_name:
            results = [r for r in results if source_name.lower() in r.source_name.lower()]
        if region:
            results = [r for r in results if region.lower() in r.region.lower()]

        return results

    def clear(self):
        """Reset in-memory storage."""
        self._records_store.clear()
        self._reports_history.clear()
