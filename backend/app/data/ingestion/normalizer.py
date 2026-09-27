import math
from typing import Optional, Tuple
from backend.app.data.ingestion.schema import ForecastVariable, ValidationIssue

COMPASS_POINTS = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}

VARIABLE_ALIASES = {
    # Temperature aliases
    "temperature": ForecastVariable.TEMPERATURE,
    "temp": ForecastVariable.TEMPERATURE,
    "t2m": ForecastVariable.TEMPERATURE,
    "2t": ForecastVariable.TEMPERATURE,
    "air_temp": ForecastVariable.TEMPERATURE,
    "temperature_2m": ForecastVariable.TEMPERATURE,
    # Rainfall aliases
    "rainfall": ForecastVariable.RAINFALL,
    "rain": ForecastVariable.RAINFALL,
    "precipitation": ForecastVariable.RAINFALL,
    "precip": ForecastVariable.RAINFALL,
    "tp": ForecastVariable.RAINFALL,
    "prate": ForecastVariable.RAINFALL,
    # Wind speed aliases
    "wind_speed": ForecastVariable.WIND_SPEED,
    "windspeed": ForecastVariable.WIND_SPEED,
    "ws": ForecastVariable.WIND_SPEED,
    "si10": ForecastVariable.WIND_SPEED,
    "wind_speed_10m": ForecastVariable.WIND_SPEED,
    # Wind direction aliases
    "wind_direction": ForecastVariable.WIND_DIRECTION,
    "winddirection": ForecastVariable.WIND_DIRECTION,
    "wdir": ForecastVariable.WIND_DIRECTION,
    "wd": ForecastVariable.WIND_DIRECTION,
}

PHYSICAL_LIMITS = {
    ForecastVariable.TEMPERATURE: (-60.0, 65.0),
    ForecastVariable.RAINFALL: (0.0, 2000.0),
    ForecastVariable.WIND_SPEED: (0.0, 400.0),
    ForecastVariable.WIND_DIRECTION: (0.0, 360.0),
}


class UnitNormalizer:
    """
    Standardizes units and variable names into canonical meteorological formats.
    """

    @classmethod
    def resolve_variable(cls, var_str: str) -> Optional[ForecastVariable]:
        cleaned = str(var_str).strip().lower().replace("-", "_").replace(" ", "_")
        return VARIABLE_ALIASES.get(cleaned)

    @classmethod
    def normalize_temperature(cls, val: float, unit: Optional[str]) -> Tuple[float, Optional[ValidationIssue]]:
        unit_clean = str(unit).strip().upper() if unit else "C"
        converted = val
        issue = None

        if unit_clean in ("K", "KELVIN"):
            converted = val - 273.15
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted temperature from Kelvin ({val} K) to Celsius ({round(converted, 2)} °C)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )
        elif unit_clean in ("F", "FAHRENHEIT"):
            converted = (val - 32.0) * (5.0 / 9.0)
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted temperature from Fahrenheit ({val} °F) to Celsius ({round(converted, 2)} °C)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )

        return round(converted, 2), issue

    @classmethod
    def normalize_rainfall(cls, val: float, unit: Optional[str]) -> Tuple[float, Optional[ValidationIssue]]:
        unit_clean = str(unit).strip().lower() if unit else "mm"
        converted = val
        issue = None

        if unit_clean in ("m", "meter", "meters"):
            converted = val * 1000.0
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted rainfall from meters ({val} m) to mm ({round(converted, 2)} mm)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )
        elif unit_clean in ("in", "inch", "inches"):
            converted = val * 25.4
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted rainfall from inches ({val} in) to mm ({round(converted, 2)} mm)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )
        elif unit_clean in ("cm", "centimeter"):
            converted = val * 10.0
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted rainfall from cm ({val} cm) to mm ({round(converted, 2)} mm)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )

        # Enforce non-negativity constraint for physical precipitation
        if converted < 0.0:
            original = converted
            converted = 0.0
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="PHYSICAL_VIOLATION",
                message=f"Negative rainfall ({original} mm) clamped to 0.0 mm",
                action_taken="CLAMPED",
                original_value=original,
                resolved_value=0.0,
            )

        return round(converted, 2), issue

    @classmethod
    def normalize_wind_speed(cls, val: float, unit: Optional[str]) -> Tuple[float, Optional[ValidationIssue]]:
        unit_clean = str(unit).strip().lower() if unit else "km/h"
        converted = val
        issue = None

        if unit_clean in ("m/s", "mps", "meter_per_second"):
            converted = val * 3.6
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted wind speed from m/s ({val} m/s) to km/h ({round(converted, 2)} km/h)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )
        elif unit_clean in ("kt", "knot", "knots"):
            converted = val * 1.852
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted wind speed from knots ({val} kt) to km/h ({round(converted, 2)} km/h)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )
        elif unit_clean in ("mph", "mile_per_hour"):
            converted = val * 1.60934
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="UNIT_CONVERSION",
                message=f"Converted wind speed from mph ({val} mph) to km/h ({round(converted, 2)} km/h)",
                action_taken="CONVERTED",
                original_value=val,
                resolved_value=round(converted, 2),
            )

        if converted < 0.0:
            converted = 0.0
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="PHYSICAL_VIOLATION",
                message="Negative wind speed clamped to 0.0 km/h",
                action_taken="CLAMPED",
                original_value=val,
                resolved_value=0.0,
            )

        return round(converted, 2), issue

    @classmethod
    def normalize_wind_direction(cls, val: Any, unit: Optional[str]) -> Tuple[float, Optional[ValidationIssue]]:
        issue = None
        # Handle compass bearing strings, e.g. "NE", "SSW"
        if isinstance(val, str):
            clean_str = val.strip().upper()
            if clean_str in COMPASS_POINTS:
                deg = COMPASS_POINTS[clean_str]
                return deg, ValidationIssue(
                    field="forecast_value",
                    issue_type="BEARING_CONVERSION",
                    message=f"Converted compass bearing '{clean_str}' to {deg}°",
                    action_taken="CONVERTED",
                    original_value=val,
                    resolved_value=deg,
                )
            try:
                num_val = float(clean_str)
            except ValueError:
                return 0.0, ValidationIssue(
                    field="forecast_value",
                    issue_type="PARSE_ERROR",
                    message=f"Unable to parse wind direction '{val}', defaulting to 0°",
                    action_taken="IMPUTED",
                    original_value=val,
                    resolved_value=0.0,
                )
        else:
            num_val = float(val)

        # Modulo 360 degrees
        normalized = num_val % 360.0
        if normalized < 0:
            normalized += 360.0

        if normalized != num_val:
            issue = ValidationIssue(
                field="forecast_value",
                issue_type="OUT_OF_BOUNDS",
                message=f"Wind direction {num_val}° normalized to {round(normalized, 1)}°",
                action_taken="CLAMPED",
                original_value=num_val,
                resolved_value=round(normalized, 1),
            )

        return round(normalized, 1), issue

    @classmethod
    def normalize_value(
        cls,
        variable: ForecastVariable,
        raw_val: Any,
        raw_unit: Optional[str] = None
    ) -> Tuple[Optional[float], Optional[ValidationIssue]]:
        """
        Main entry point for unit normalization per forecast variable.
        """
        if raw_val is None or raw_val == "" or (isinstance(raw_val, float) and math.isnan(raw_val)):
            return None, ValidationIssue(
                field="forecast_value",
                issue_type="MISSING_VALUE",
                message=f"Missing raw value for {variable.value}",
                action_taken="FLAGGED",
            )

        try:
            num_val = float(raw_val) if not isinstance(raw_val, str) or raw_val.replace('.', '', 1).replace('-', '', 1).isdigit() else raw_val
        except (ValueError, TypeError):
            num_val = raw_val

        if variable == ForecastVariable.TEMPERATURE:
            return cls.normalize_temperature(float(num_val), raw_unit)
        elif variable == ForecastVariable.RAINFALL:
            return cls.normalize_rainfall(float(num_val), raw_unit)
        elif variable == ForecastVariable.WIND_SPEED:
            return cls.normalize_wind_speed(float(num_val), raw_unit)
        elif variable == ForecastVariable.WIND_DIRECTION:
            return cls.normalize_wind_direction(num_val, raw_unit)

        return float(num_val), None
