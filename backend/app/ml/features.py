import math
from typing import Dict, Any
from backend.app.models.domain import WeatherRegime, WeatherVariable


def extract_blending_features(
    lat: float,
    lon: float,
    lead_time_hours: int,
    regime: WeatherRegime,
    variable: WeatherVariable,
    elevation_m: float = 100.0,
    month: int = 7,  # Default to July (monsoon peak)
) -> Dict[str, Any]:
    """
    Extract standardized feature vector for the dynamic weight meta-learner.
    """
    # Cyclical day of year / month encoding
    month_rad = 2.0 * math.pi * (month - 1) / 12.0
    sin_month = math.sin(month_rad)
    cos_month = math.cos(month_rad)

    # Orographic / terrain indicator
    is_high_altitude = 1.0 if elevation_m > 800.0 else 0.0

    # Regional classification
    is_coastal = 1.0 if (lon < 73.5 or lon > 85.0) and (lat < 23.0) else 0.0
    is_himalayan = 1.0 if lat > 28.0 and lon > 74.0 else 0.0

    return {
        "lat": lat,
        "lon": lon,
        "lead_time_hours": lead_time_hours,
        "norm_lead_time": lead_time_hours / 168.0,
        "sin_month": sin_month,
        "cos_month": cos_month,
        "elevation_m": elevation_m,
        "is_high_altitude": is_high_altitude,
        "is_coastal": is_coastal,
        "is_himalayan": is_himalayan,
        "regime": regime.value,
        "variable": variable.value,
    }
