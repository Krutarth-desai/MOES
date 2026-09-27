import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from backend.app.data.observation.schema import (
    ObservationIngestionReport,
    ObservationRecord,
    ObservationValidationIssue,
)
from backend.app.data.ingestion.validator import RecordValidator
from backend.app.data.ingestion.normalizer import PHYSICAL_LIMITS, ForecastVariable

logger = logging.getLogger("moes.observation.ingestion")


class ObservationIngestionService:
    """
    Ingests and validates ground-truth meteorological observation datasets.
    Handles CSV and JSON files with multi-variable measurements (temperature, rainfall,
    wind speed, and wind direction).
    """

    @classmethod
    def clean_float(
        cls,
        val: Any,
        var_type: ForecastVariable,
        record_idx: Optional[int],
        issues: List[ObservationValidationIssue],
        station_id: Optional[str] = None,
    ) -> Optional[float]:
        """
        Parse, bounds-check, and clamp physical weather variables.
        """
        if val is None or val == "" or str(val).strip().lower() in ("na", "nan", "null", "-999", "-999.0"):
            return None

        try:
            num = float(val)
        except (ValueError, TypeError):
            issues.append(
                ObservationValidationIssue(
                    record_index=record_idx,
                    station_id=station_id,
                    field=var_type.value,
                    issue_type="PARSING_ERROR",
                    message=f"Cannot parse value '{val}' as float",
                    action_taken="DROPPED",
                    original_value=val,
                )
            )
            return None

        # Check physical non-negativity for rainfall and wind speed
        if var_type == ForecastVariable.RAINFALL and num < 0.0:
            issues.append(
                ObservationValidationIssue(
                    record_index=record_idx,
                    station_id=station_id,
                    field="rainfall",
                    issue_type="OUT_OF_BOUNDS",
                    message=f"Negative rainfall ({num} mm) clamped to 0.0 mm",
                    action_taken="CLAMPED",
                    original_value=num,
                    resolved_value=0.0,
                )
            )
            return 0.0

        if var_type == ForecastVariable.WIND_SPEED and num < 0.0:
            issues.append(
                ObservationValidationIssue(
                    record_index=record_idx,
                    station_id=station_id,
                    field="wind_speed",
                    issue_type="OUT_OF_BOUNDS",
                    message=f"Negative wind speed ({num} km/h) clamped to 0.0 km/h",
                    action_taken="CLAMPED",
                    original_value=num,
                    resolved_value=0.0,
                )
            )
            return 0.0

        if var_type == ForecastVariable.WIND_DIRECTION:
            normalized_deg = num % 360.0
            if normalized_deg < 0:
                normalized_deg += 360.0
            return round(normalized_deg, 2)

        # General physical boundary limits
        min_lim, max_lim = PHYSICAL_LIMITS[var_type]
        if num < min_lim or num > max_lim:
            clamped = max(min_lim, min(max_lim, num))
            issues.append(
                ObservationValidationIssue(
                    record_index=record_idx,
                    station_id=station_id,
                    field=var_type.value,
                    issue_type="OUT_OF_BOUNDS",
                    message=f"{var_type.value} ({num}) exceeded physical bounds [{min_lim}, {max_lim}], clamped to {clamped}",
                    action_taken="CLAMPED",
                    original_value=num,
                    resolved_value=clamped,
                )
            )
            return round(clamped, 2)

        return round(num, 2)

    @classmethod
    def parse_record_dict(
        cls,
        raw_row: Dict[str, Any],
        row_index: Optional[int] = None,
    ) -> Tuple[Optional[ObservationRecord], List[ObservationValidationIssue]]:
        issues: List[ObservationValidationIssue] = []

        # 1. Parse Timestamp
        raw_ts = raw_row.get("timestamp") or raw_row.get("valid_time") or raw_row.get("datetime") or raw_row.get("date")
        timestamp = RecordValidator.parse_datetime(raw_ts)
        if not timestamp:
            issues.append(
                ObservationValidationIssue(
                    record_index=row_index,
                    field="timestamp",
                    issue_type="MISSING_TIMESTAMP",
                    message="Missing or unparseable observation timestamp",
                    action_taken="DROPPED",
                    original_value=raw_ts,
                )
            )
            return None, issues

        # 2. Parse Coordinates
        try:
            lat = float(raw_row.get("latitude") or raw_row.get("lat") or 0.0)
            lon = float(raw_row.get("longitude") or raw_row.get("lon") or 0.0)
        except (ValueError, TypeError):
            issues.append(
                ObservationValidationIssue(
                    record_index=row_index,
                    field="coordinates",
                    issue_type="INVALID_COORDINATES",
                    message="Invalid latitude or longitude",
                    action_taken="DROPPED",
                )
            )
            return None, issues

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            issues.append(
                ObservationValidationIssue(
                    record_index=row_index,
                    field="coordinates",
                    issue_type="OUT_OF_BOUNDS",
                    message=f"Coordinates ({lat}, {lon}) out of global bounds",
                    action_taken="DROPPED",
                )
            )
            return None, issues

        st_id = raw_row.get("station_id")
        st_name = raw_row.get("station_name")
        elev = None
        if raw_row.get("elevation_m") is not None:
            try:
                elev = float(raw_row["elevation_m"])
            except ValueError:
                pass

        # 3. Clean Multi-Variable Weather Measurements
        quality_flags: Dict[str, str] = {}

        temp = cls.clean_float(
            raw_row.get("temperature") or raw_row.get("temp"),
            ForecastVariable.TEMPERATURE,
            row_index,
            issues,
            st_id,
        )
        quality_flags["temperature"] = "VALID" if temp is not None else "MISSING"

        rain = cls.clean_float(
            raw_row.get("rainfall") or raw_row.get("rain") or raw_row.get("precipitation"),
            ForecastVariable.RAINFALL,
            row_index,
            issues,
            st_id,
        )
        quality_flags["rainfall"] = "VALID" if rain is not None else "MISSING"

        w_speed = cls.clean_float(
            raw_row.get("wind_speed") or raw_row.get("ws"),
            ForecastVariable.WIND_SPEED,
            row_index,
            issues,
            st_id,
        )
        quality_flags["wind_speed"] = "VALID" if w_speed is not None else "MISSING"

        w_dir = cls.clean_float(
            raw_row.get("wind_direction") or raw_row.get("wd"),
            ForecastVariable.WIND_DIRECTION,
            row_index,
            issues,
            st_id,
        )
        quality_flags["wind_direction"] = "VALID" if w_dir is not None else "MISSING"

        record = ObservationRecord(
            timestamp=timestamp,
            latitude=lat,
            longitude=lon,
            temperature=temp,
            rainfall=rain,
            wind_speed=w_speed,
            wind_direction=w_dir,
            station_id=str(st_id) if st_id else None,
            station_name=str(st_name) if st_name else None,
            elevation_m=elev,
            source=str(raw_row.get("source") or "IMD_GROUND_TRUTH"),
            quality_flags=quality_flags,
        )

        return record, issues

    def load_file(self, file_path: Path) -> Tuple[List[ObservationRecord], ObservationIngestionReport]:
        path = Path(file_path)
        report = ObservationIngestionReport(
            source_name="Observation Pipeline",
            source_file=str(path),
        )

        if not path.exists():
            report.issues.append(
                ObservationValidationIssue(
                    field="source_file",
                    issue_type="FILE_NOT_FOUND",
                    message=f"Observation file not found: {path}",
                    action_taken="DROPPED",
                )
            )
            report.mark_complete()
            return [], report

        records: List[ObservationRecord] = []

        try:
            if path.suffix.lower() == ".json":
                with open(path, mode="r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                rows = raw_data if isinstance(raw_data, list) else raw_data.get("observations", raw_data.get("records", []))
            else:
                with open(path, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    reader.fieldnames = [fn.strip().lower() for fn in (reader.fieldnames or [])]
                    rows = list(reader)

            for idx, raw_dict in enumerate(rows, start=1):
                report.total_records_read += 1
                record, issues = self.parse_record_dict(raw_dict, row_index=idx)
                if issues:
                    report.issues.extend(issues)

                if record:
                    records.append(record)
                    has_missing = any(v == "MISSING" for v in record.quality_flags.values())
                    if has_missing:
                        report.records_with_missing_vars += 1
                    report.valid_records_count += 1
                else:
                    report.rejected_records_count += 1

        except Exception as e:
            logger.exception("Failed to ingest observation file %s", path)
            report.issues.append(
                ObservationValidationIssue(
                    field="file_reading",
                    issue_type="PARSER_EXCEPTION",
                    message=str(e),
                    action_taken="DROPPED",
                )
            )

        report.mark_complete()
        logger.info(
            "Ingested observations from %s: %d total, %d valid, %d with missing vars, %d rejected (%.1f ms)",
            path.name,
            report.total_records_read,
            report.valid_records_count,
            report.records_with_missing_vars,
            report.rejected_records_count,
            report.duration_ms,
        )
        return records, report
