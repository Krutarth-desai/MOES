import json
import logging
from pathlib import Path
from typing import List, Tuple
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    IngestionReport,
    StandardForecastRecord,
    ValidationIssue,
)
from backend.app.data.ingestion.sources.base import BaseForecastSource
from backend.app.data.ingestion.validator import RecordValidator

logger = logging.getLogger("moes.ingestion.json")


class JSONForecastSource(BaseForecastSource):
    """
    Ingestion reader for JSON & GeoJSON forecast datasets.
    Handles flat arrays, nested dictionary envelopes, and GeoJSON FeatureCollections.
    """

    def __init__(self, name: str = "Generic JSON Forecast", source_type: ForecastSourceType = ForecastSourceType.AI):
        self._name = name
        self._type = source_type

    @property
    def source_name(self) -> str:
        return self._name

    @property
    def source_type(self) -> ForecastSourceType:
        return self._type

    def load(self, source_path: Path) -> Tuple[List[StandardForecastRecord], IngestionReport]:
        path = Path(source_path)
        report = IngestionReport(
            source_name=self.source_name,
            source_type=self.source_type,
            source_file=str(path),
        )

        if not path.exists():
            report.issues.append(
                ValidationIssue(
                    field="source_file",
                    issue_type="FILE_NOT_FOUND",
                    message=f"File not found: {source_path}",
                    action_taken="REJECTED",
                )
            )
            report.mark_complete()
            logger.error("Ingestion failed: File %s not found", source_path)
            return [], report

        records: List[StandardForecastRecord] = []

        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            # Extract raw item list from diverse JSON layouts
            raw_items = []
            if isinstance(data, list):
                raw_items = data
            elif isinstance(data, dict):
                if "records" in data and isinstance(data["records"], list):
                    raw_items = data["records"]
                elif "forecasts" in data and isinstance(data["forecasts"], list):
                    raw_items = data["forecasts"]
                elif "data" in data and isinstance(data["data"], list):
                    raw_items = data["data"]
                elif "features" in data and isinstance(data["features"], list):
                    # GeoJSON FeatureCollection
                    for feat in data["features"]:
                        props = feat.get("properties", {})
                        geom = feat.get("geometry", {})
                        coords = geom.get("coordinates", [])
                        if len(coords) >= 2:
                            props["longitude"] = coords[0]
                            props["latitude"] = coords[1]
                        raw_items.append(props)
                else:
                    raw_items = [data]

            for idx, raw_dict in enumerate(raw_items, start=1):
                report.total_records_read += 1

                # Supply model name if missing
                if not raw_dict.get("model_name") and not raw_dict.get("source_name"):
                    raw_dict["model_name"] = self.source_name

                record, issues = RecordValidator.validate_and_clean_record(raw_dict, row_index=idx)

                if issues:
                    report.issues.extend(issues)

                if record:
                    records.append(record)
                    if any(i.action_taken == "IMPUTED" for i in issues):
                        report.imputed_records_count += 1
                    else:
                        report.valid_records_count += 1
                else:
                    report.rejected_records_count += 1
                    logger.warning("Rejected JSON record %d in %s", idx, path.name)

        except Exception as e:
            logger.exception("Unexpected error parsing JSON %s", source_path)
            report.issues.append(
                ValidationIssue(
                    field="file_parsing",
                    issue_type="JSON_PARSER_ERROR",
                    message=str(e),
                    action_taken="ABORTED",
                )
            )

        report.mark_complete()
        logger.info(
            "Ingested %s: %d total, %d valid, %d imputed, %d rejected (took %.1f ms)",
            self.source_name,
            report.total_records_read,
            report.valid_records_count,
            report.imputed_records_count,
            report.rejected_records_count,
            report.duration_ms,
        )

        return records, report
