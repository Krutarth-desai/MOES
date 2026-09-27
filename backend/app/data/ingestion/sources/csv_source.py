import csv
import logging
from pathlib import Path
from typing import List, Optional, Tuple
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    IngestionReport,
    StandardForecastRecord,
    ValidationIssue,
)
from backend.app.data.ingestion.sources.base import BaseForecastSource
from backend.app.data.ingestion.validator import RecordValidator

logger = logging.getLogger("moes.ingestion.csv")


class CSVForecastSource(BaseForecastSource):
    """
    Ingestion reader for CSV forecast files.
    Compatible with standard tabular meteorology exports, IMD station bulletins,
    and open NWP CSV dumps.
    """

    def __init__(self, name: str = "Generic CSV Forecast", source_type: ForecastSourceType = ForecastSourceType.NWP):
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
            with open(path, mode="r", encoding="utf-8-sig") as f:
                # Detect dialect
                sample = f.read(2048)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    dialect = csv.excel

                reader = csv.DictReader(f, dialect=dialect)

                # Clean column headers
                reader.fieldnames = [name.strip().lower() for name in (reader.fieldnames or [])]

                for idx, row in enumerate(reader, start=1):
                    report.total_records_read += 1

                    # Clean values and map empty sentinels
                    clean_row = {}
                    for k, v in row.items():
                        if k is None:
                            continue
                        val = v.strip() if isinstance(v, str) else v
                        if val in ("", "NA", "na", "null", "NULL", "nan", "NaN", "-999", "-999.0"):
                            val = None
                        clean_row[k] = val

                    # Supply model name if not present in row
                    if not clean_row.get("model_name") and not clean_row.get("source_name"):
                        clean_row["model_name"] = self.source_name

                    record, issues = RecordValidator.validate_and_clean_record(clean_row, row_index=idx)

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
                        logger.warning("Rejected row %d in %s: %s", idx, path.name, [i.message for i in issues])

        except Exception as e:
            logger.exception("Unexpected error while parsing CSV %s", source_path)
            report.issues.append(
                ValidationIssue(
                    field="file_parsing",
                    issue_type="CSV_PARSER_ERROR",
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
