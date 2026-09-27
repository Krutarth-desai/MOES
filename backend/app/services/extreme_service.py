from datetime import datetime, timedelta
from typing import List
from backend.app.models.domain import AlertSeverity, HazardAlert, HazardType, WeatherVariable
from backend.app.data.stations import get_all_stations
from backend.app.services.provider_interface import BaseForecastProvider
from backend.app.services.blender_interface import BaseBlender
from backend.app.models.domain import WeatherRegime
from backend.app.utils.meteorology import (
    classify_rainfall_severity,
    classify_temperature_severity,
    classify_wind_severity,
)


class ExtremeWeatherService:
    """
    Evaluates multi-model blended predictions against official IMD thresholds
    to generate actionable severe weather hazard advisories.
    """

    def __init__(self, provider: BaseForecastProvider, blender: BaseBlender):
        self.provider = provider
        self.blender = blender

    def detect_alerts(self, lead_time_hours: int = 24) -> List[HazardAlert]:
        stations = get_all_stations()
        alerts: List[HazardAlert] = []
        now = datetime.now()
        valid_from = (now + timedelta(hours=lead_time_hours - 12)).strftime("%Y-%m-%d %H:00")
        valid_to = (now + timedelta(hours=lead_time_hours + 12)).strftime("%Y-%m-%d %H:00")

        for station in stations:
            # Check 1: Rainfall Alert
            rain_raw = self.provider.get_point_forecast(
                station.lat, station.lon, WeatherVariable.PRECIPITATION, [lead_time_hours]
            )
            raw_dict_rain = {m: rain_raw[m][lead_time_hours] for m in rain_raw}
            weights_rain = self.blender.compute_weights(
                station.lat, station.lon, lead_time_hours, WeatherRegime.MONSOON_ACTIVE, WeatherVariable.PRECIPITATION
            )
            blended_rain, _, _ = self.blender.blend_point(
                raw_dict_rain, weights_rain, WeatherVariable.PRECIPITATION
            )

            severity_rain, hazard_type_rain, rec_rain = classify_rainfall_severity(blended_rain)
            if severity_rain in (AlertSeverity.ORANGE, AlertSeverity.RED):
                # Calculate probability of exceeding 64.5 mm
                hits = sum(1 for v in raw_dict_rain.values() if v >= 64.5)
                prob = round(hits / len(raw_dict_rain), 2)
                alerts.append(
                    HazardAlert(
                        id=f"alert-rain-{station.name[:3].lower()}-{lead_time_hours}h",
                        hazard_type=hazard_type_rain,
                        severity=severity_rain,
                        title=f"{severity_rain.value.upper()} WARNING: Heavy Rainfall Alert for {station.name}",
                        description=f"Expected 24h cumulative rainfall of {blended_rain} mm (Multi-model consensus probability: {int(prob*100)}%).",
                        location_name=station.name,
                        state="Meteorological Subdivision",
                        lat=station.lat,
                        lon=station.lon,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        exceedance_probability=prob,
                        recommended_action=rec_rain,
                    )
                )

            # Check 2: Temperature / Heatwave Alert
            temp_raw = self.provider.get_point_forecast(
                station.lat, station.lon, WeatherVariable.TEMPERATURE_2M, [lead_time_hours]
            )
            raw_dict_temp = {m: temp_raw[m][lead_time_hours] for m in temp_raw}
            weights_temp = self.blender.compute_weights(
                station.lat, station.lon, lead_time_hours, WeatherRegime.HEATWAVE_SYNOPTIC, WeatherVariable.TEMPERATURE_2M
            )
            blended_temp, _, _ = self.blender.blend_point(
                raw_dict_temp, weights_temp, WeatherVariable.TEMPERATURE_2M
            )

            severity_temp, hazard_type_temp, rec_temp = classify_temperature_severity(blended_temp)
            if severity_temp in (AlertSeverity.ORANGE, AlertSeverity.RED):
                hits_heat = sum(1 for v in raw_dict_temp.values() if v >= 42.0)
                prob_heat = round(hits_heat / len(raw_dict_temp), 2)
                alerts.append(
                    HazardAlert(
                        id=f"alert-temp-{station.name[:3].lower()}-{lead_time_hours}h",
                        hazard_type=hazard_type_temp,
                        severity=severity_temp,
                        title=f"{severity_temp.value.upper()} WARNING: Heatwave Conditions for {station.name}",
                        description=f"Expected maximum temperature reaching {blended_temp}°C.",
                        location_name=station.name,
                        state="Meteorological Subdivision",
                        lat=station.lat,
                        lon=station.lon,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        exceedance_probability=prob_heat,
                        recommended_action=rec_temp,
                    )
                )

            # Check 3: High Wind / Gale Alert
            wind_raw = self.provider.get_point_forecast(
                station.lat, station.lon, WeatherVariable.WIND_SPEED_10M, [lead_time_hours]
            )
            raw_dict_wind = {m: wind_raw[m][lead_time_hours] for m in wind_raw}
            weights_wind = self.blender.compute_weights(
                station.lat, station.lon, lead_time_hours, WeatherRegime.MONSOON_ACTIVE, WeatherVariable.WIND_SPEED_10M
            )
            blended_wind, _, _ = self.blender.blend_point(
                raw_dict_wind, weights_wind, WeatherVariable.WIND_SPEED_10M
            )

            severity_wind, hazard_type_wind, rec_wind = classify_wind_severity(blended_wind)
            if severity_wind in (AlertSeverity.ORANGE, AlertSeverity.RED):
                alerts.append(
                    HazardAlert(
                        id=f"alert-wind-{station.name[:3].lower()}-{lead_time_hours}h",
                        hazard_type=hazard_type_wind,
                        severity=severity_wind,
                        title=f"{severity_wind.value.upper()} WARNING: High Wind / Squall Alert for {station.name}",
                        description=f"Predicted sustained surface wind speeds up to {blended_wind} km/h.",
                        location_name=station.name,
                        state="Coastal / Inland Zone",
                        lat=station.lat,
                        lon=station.lon,
                        valid_from=valid_from,
                        valid_to=valid_to,
                        exceedance_probability=0.85,
                        recommended_action=rec_wind,
                    )
                )

        return alerts
