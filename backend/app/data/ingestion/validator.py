from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from backend.app.data.ingestion.schema import (
    ForecastVariable,
    QualityFlag,
    Season,
    StandardForecastRecord,
    ValidationIssue,
    WeatherRegime,
)
from backend.app.data.ingestion.normalizer import PHYSICAL_LIMITS, UnitNormalizer


# Regional Climatological Defaults for Imputation (Indian domain)
CLIMATOLOGICAL_DEFAULTS = {
    ForecastVariable.TEMPERATURE: 28.0,   # °C
    ForecastVariable.RAINFALL: 0.0,       # mm
    ForecastVariable.WIND_SPEED: 12.0,    # km/h
    ForecastVariable.WIND_DIRECTION: 240.0, # Monsoonal south-westerly
}

# Indian Subcontinent Bounding Box
INDIA_DOMAIN = {
    "min_lat": 6.0,
    "max_lat": 38.5,
    "min_lon": 68.0,
    "max_lon": 98.5,
}


class RecordValidator:
    """
    Validates, repairs, and imputes forecast records.
    """

    @classmethod
    def parse_datetime(cls, dt_val: Any) -> Optional[datetime]:
        if isinstance(dt_val, datetime):
            return dt_val
        if not dt_val:
            return None
        dt_str = str(dt_val).strip()

        # Try common meteorological datetime formats
        formats = [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%Y%m%d%H",
            "%Y%m%d%H%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(dt_str, fmt)
            except ValueError:
                continue

        # Try fromisoformat fallback
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            return None

    @classmethod
    def infer_season(cls, dt: datetime) -> Season:
        m = dt.month
        if 6 <= m <= 9:
            return Season.MONSOON
        elif 10 <= m <= 11:
            return Season.POST_MONSOON
        elif 12 <= m or m <= 2:
            return Season.WINTER
        else:
            return Season.PRE_MONSOON

    @classmethod
    def validate_and_clean_record(
        cls,
        raw_dict: Dict[str, Any],
        row_index: Optional[int] = None,
    ) -> Tuple[Optional[StandardForecastRecord], List[ValidationIssue]]:
        """
        Validate, normalize units, impute missing values, and construct a StandardForecastRecord.
        """
        issues: List[ValidationIssue] = []

        # 1. Resolve Variable
        raw_var = raw_dict.get("forecast_variable") or raw_dict.get("variable") or raw_dict.get("param")
        if not raw_var:
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="forecast_variable",
                    issue_type="MISSING_FIELD",
                    message="Missing 'forecast_variable' field",
                    action_taken="REJECTED",
                )
            )
            return None, issues

        variable = UnitNormalizer.resolve_variable(raw_var)
        if not variable:
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="forecast_variable",
                    issue_type="UNKNOWN_VARIABLE",
                    message=f"Unrecognized forecast variable: '{raw_var}'",
                    action_taken="REJECTED",
                )
            )
            return None, issues

        # 2. Coordinates Validation
        try:
            lat = float(raw_dict.get("latitude") or raw_dict.get("lat") or 0.0)
            lon = float(raw_dict.get("longitude") or raw_dict.get("lon") or 0.0)
        except (ValueError, TypeError):
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="coordinates",
                    issue_type="INVALID_COORDINATES",
                    message="Invalid latitude or longitude format",
                    action_taken="REJECTED",
                )
            )
            return None, issues

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="coordinates",
                    issue_type="OUT_OF_BOUNDS",
                    message=f"Coordinates ({lat}, {lon}) out of planetary bounds",
                    action_taken="REJECTED",
                )
            )
            return None, issues

        # 3. Temporal Validation (initialization_time, lead_time_hours, timestamp)
        raw_init = raw_dict.get("forecast_initialization_time") or raw_dict.get("initialization_time") or raw_dict.get("init_time")
        init_time = cls.parse_datetime(raw_init) or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # Lead time
        lead_time_val = raw_dict.get("lead_time") or raw_dict.get("lead_time_hours") or raw_dict.get("step_hours")
        lead_time = 0
        if lead_time_val is not None:
            try:
                lead_time = max(0, int(float(lead_time_val)))
            except (ValueError, TypeError):
                lead_time = 0

        # Valid timestamp
        raw_ts = raw_dict.get("timestamp") or raw_dict.get("valid_time") or raw_dict.get("time")
        timestamp = cls.parse_datetime(raw_ts)
        if not timestamp:
            timestamp = init_time + timedelta(hours=lead_time)
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="timestamp",
                    issue_type="DERIVED_TIMESTAMP",
                    message=f"Timestamp inferred as init_time ({init_time}) + {lead_time}h",
                    action_taken="CONVERTED",
                    resolved_value=timestamp.isoformat(),
                )
            )

        # 4. Value Normalization & Missing Imputation
        raw_val = raw_dict.get("forecast_value") or raw_dict.get("value")
        raw_unit = raw_dict.get("unit") or raw_dict.get("raw_unit")
        quality_flag = QualityFlag.VALID

        norm_val, norm_issue = UnitNormalizer.normalize_value(variable, raw_val, raw_unit)
        if norm_issue:
            norm_issue.record_index = row_index
            issues.append(norm_issue)

        if norm_val is None:
            # Impute missing value
            imputed_val = CLIMATOLOGICAL_DEFAULTS.get(variable, 0.0)
            quality_flag = QualityFlag.IMPUTED
            norm_val = imputed_val
            issues.append(
                ValidationIssue(
                    record_index=row_index,
                    field="forecast_value",
                    issue_type="MISSING_VALUE",
                    message=f"Missing value for {variable.value} imputed with climatological prior ({imputed_val})",
                    action_taken="IMPUTED",
                    original_value=raw_val,
                    resolved_value=imputed_val,
                )
            )
        else:
            # Physical bounds check
            min_lim, max_lim = PHYSICAL_LIMITS[variable]
            if norm_val < min_lim or norm_val > max_lim:
                clamped_val = max(min_lim, min(max_lim, norm_val))
                quality_flag = QualityFlag.CLAMPED
                issues.append(
                    ValidationIssue(
                        record_index=row_index,
                        field="forecast_value",
                        issue_type="OUT_OF_BOUNDS",
                        message=f"{variable.value} ({norm_val}) exceeded physical limits [{min_lim}, {max_lim}], clamped to {clamped_val}",
                        action_taken="CLAMPED",
                        original_value=norm_val,
                        resolved_value=clamped_val,
                    )
                )
                norm_val = clamped_val

        # 5. Metadata fields
        source_name = str(raw_dict.get("model_name") or raw_dict.get("source_name") or "Unknown Source").strip()
        region = str(raw_dict.get("region") or "Indian Subcontinent").strip()

        # Season
        raw_season = raw_dict.get("season")
        if raw_season and str(raw_season).lower() in [s.value for s in Season]:
            season = Season(str(raw_season).lower())
        else:
            season = cls.infer_season(timestamp)

        # Weather regime
        raw_regime = raw_dict.get("weather_regime")
        weather_regime = None
        if raw_regime and str(raw_regime).lower() in [r.value for r in WeatherRegime]:
            weather_regime = WeatherRegime(str(raw_regime).lower())

        station_id = raw_dict.get("station_id")

        record = StandardForecastRecord(
            timestamp=timestamp,
            latitude=lat,
            longitude=lon,
            forecast_variable=variable,
            forecast_value=norm_val,
            initialization_time=init_time,
            lead_time_hours=lead_time,
            source_name=source_name,
            region=region,
            season=season,
            weather_regime=weather_regime,
            raw_value=float(raw_val) if isinstance(raw_val, (int, float)) else None,
            raw_unit=str(raw_unit) if raw_unit else None,
            quality_flag=quality_flag,
            station_id=str(station_id) if station_id else None,
        )

        return record, issues
