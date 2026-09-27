from typing import Tuple
from backend.app.models.domain import AlertSeverity, HazardType


def classify_rainfall_severity(daily_rain_mm: float) -> Tuple[AlertSeverity, HazardType, str]:
    """
    Classify 24h precipitation according to official IMD categorization.
    """
    if daily_rain_mm >= 204.5:
        return (
            AlertSeverity.RED,
            HazardType.EXTREMELY_HEAVY_RAIN,
            "Take Action: Extremely heavy rain (>204.4mm). High risk of flash flooding and landslides.",
        )
    elif daily_rain_mm >= 115.6:
        return (
            AlertSeverity.ORANGE,
            HazardType.VERY_HEAVY_RAIN,
            "Be Prepared: Very heavy rain (115.6-204.4mm). Disruption to transport and waterlogging expected.",
        )
    elif daily_rain_mm >= 64.5:
        return (
            AlertSeverity.ORANGE,
            HazardType.HEAVY_RAIN,
            "Be Updated: Heavy rain (64.5-115.5mm). Localized localized inundation possible.",
        )
    elif daily_rain_mm >= 15.6:
        return (
            AlertSeverity.YELLOW,
            HazardType.HEAVY_RAIN,
            "Watch: Moderate rain (15.6-64.4mm). Normal seasonal showers.",
        )
    else:
        return (
            AlertSeverity.GREEN,
            HazardType.HEAVY_RAIN,
            "No Warning: Dry or light rain (<15.6mm).",
        )


def classify_temperature_severity(t_max_c: float, departure_c: float = 0.0) -> Tuple[AlertSeverity, HazardType, str]:
    """
    Classify maximum surface temperature according to IMD heatwave criteria for plains.
    """
    if t_max_c >= 47.0 or departure_c >= 6.4:
        return (
            AlertSeverity.RED,
            HazardType.HEATWAVE,
            "Extreme Warning: Severe heatwave conditions. High health risk for vulnerable populations.",
        )
    elif t_max_c >= 45.0 or (t_max_c >= 40.0 and departure_c >= 4.5):
        return (
            AlertSeverity.ORANGE,
            HazardType.HEATWAVE,
            "Alert: Heatwave conditions prevailing. Avoid prolonged sun exposure during peak hours.",
        )
    elif t_max_c >= 40.0:
        return (
            AlertSeverity.YELLOW,
            HazardType.HEATWAVE,
            "Advisory: Unusually warm conditions approaching heatwave threshold.",
        )
    else:
        return (
            AlertSeverity.GREEN,
            HazardType.HEATWAVE,
            "Normal thermal regime.",
        )


def classify_wind_severity(wind_speed_kmh: float) -> Tuple[AlertSeverity, HazardType, str]:
    """
    Classify wind speed according to IMD marine & inland squall/gale criteria.
    """
    if wind_speed_kmh >= 75.0:
        return (
            AlertSeverity.RED,
            HazardType.GALE_WIND,
            "Cyclonic Gale Force Wind: High danger to temporary structures, trees, and power lines.",
        )
    elif wind_speed_kmh >= 50.0:
        return (
            AlertSeverity.ORANGE,
            HazardType.GALE_WIND,
            "Squally Wind: Fishermen advised not to venture into deep sea. Wind gusts up to 74 km/h.",
        )
    elif wind_speed_kmh >= 39.0:
        return (
            AlertSeverity.YELLOW,
            HazardType.GALE_WIND,
            "Strong Breeze: Gusty winds likely.",
        )
    else:
        return (
            AlertSeverity.GREEN,
            HazardType.GALE_WIND,
            "Normal surface winds.",
        )
