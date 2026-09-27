import math
from typing import Dict, List, Optional
from backend.app.models.domain import GridCell, WeatherVariable
from backend.app.services.provider_interface import BaseForecastProvider
from backend.app.data.grid import generate_domain_coordinates


class SimulatedForecastProvider(BaseForecastProvider):
    """
    Physically-grounded Simulated Forecast Provider for the Indian Subcontinent.
    
    Provides realistic, continuous spatial and temporal fields for:
    - GFS (NWP, NOAA)
    - ECMWF (NWP, IFS)
    - GraphCast (AI, DeepMind)
    - Pangu-Weather (AI, Huawei)
    along with ground truth benchmark for verification.
    
    Can be seamlessly swapped with real NWP / Open-Meteo / NetCDF pipelines.
    """

    def _get_base_signal(self, lat: float, lon: float, variable: WeatherVariable, lead_hours: int) -> float:
        """
        Underlying atmospheric state based on Indian geography and typical summer monsoon climatology.
        """
        # Time decay/variation across forecast horizon
        lead_phase = math.sin(lead_hours * 0.05)

        if variable == WeatherVariable.PRECIPITATION:
            # High rainfall over Western Ghats (lon ~73.5, lat 9-19)
            west_ghats_proximity = math.exp(-((lon - 73.8) ** 2) / 1.5 - ((lat - 15.0) ** 2) / 30.0)
            # High rainfall over Northeast India (lon ~91-94, lat 24-27)
            northeast_proximity = math.exp(-((lon - 92.5) ** 2) / 3.0 - ((lat - 25.5) ** 2) / 4.0)
            # Arid northwest rain shadow (lon ~71, lat 26)
            arid_factor = 1.0 - 0.8 * math.exp(-((lon - 71.0) ** 2) / 10.0 - ((lat - 27.0) ** 2) / 15.0)

            base_rain = (45.0 * west_ghats_proximity + 60.0 * northeast_proximity + 8.0) * arid_factor
            val = max(0.0, base_rain + 6.0 * lead_phase)
            return round(val, 1)

        elif variable == WeatherVariable.TEMPERATURE_2M:
            # Hot in northwest plains (lat ~28, lon ~75), cooler in Himalayas and southern oceans
            lat_effect = (38.0 - lat) * 0.5
            arid_heat = 10.0 * math.exp(-((lon - 73.0) ** 2) / 25.0 - ((lat - 28.0) ** 2) / 20.0)
            base_temp = 22.0 + lat_effect + arid_heat + 1.5 * lead_phase
            return round(base_temp, 1)

        elif variable == WeatherVariable.WIND_SPEED_10M:
            # Strong monsoonal westerlies in the Arabian Sea & Peninsular coast
            coastal_wind = 25.0 * math.exp(-((lon - 72.0) ** 2) / 8.0 - ((lat - 14.0) ** 2) / 40.0)
            base_wind = 14.0 + coastal_wind + 3.0 * lead_phase
            return round(base_wind, 1)

        return 0.0

    def get_point_forecast(
        self,
        lat: float,
        lon: float,
        variable: WeatherVariable,
        lead_times_hours: List[int],
    ) -> Dict[str, Dict[int, float]]:
        predictions: Dict[str, Dict[int, float]] = {
            "gfs": {},
            "ecmwf": {},
            "graphcast": {},
            "pangu": {},
        }

        for lead in lead_times_hours:
            true_signal = self._get_base_signal(lat, lon, variable, lead)

            # Realistic model biases and random perturbations:
            # 1. GFS: slight over-prediction in rain (+15%), slight cold bias in temp
            gfs_bias = 1.15 if variable == WeatherVariable.PRECIPITATION else -0.4
            gfs_err = math.sin(lat * 1.5 + lead * 0.2) * (1.5 if variable != WeatherVariable.PRECIPITATION else 4.0)
            predictions["gfs"][lead] = max(0.0, round(true_signal * gfs_bias + gfs_err, 1))

            # 2. ECMWF: well-calibrated physical model with slight damping at long leads
            ecmwf_err = math.cos(lon * 0.8 + lead * 0.15) * (0.8 if variable != WeatherVariable.PRECIPITATION else 2.5)
            predictions["ecmwf"][lead] = max(0.0, round(true_signal * 1.02 + ecmwf_err, 1))

            # 3. GraphCast: high accuracy at lead <= 48h, slight smoothing / under-forecasting peaks at 120h+
            gc_lead_penalty = 0.92 if lead >= 120 and variable == WeatherVariable.PRECIPITATION else 1.01
            gc_err = math.sin(lat * 0.7 + lon * 0.5) * (0.5 if variable != WeatherVariable.PRECIPITATION else 1.8)
            predictions["graphcast"][lead] = max(0.0, round(true_signal * gc_lead_penalty + gc_err, 1))

            # 4. Pangu: competitive AI model
            pangu_err = math.cos(lat * 1.1 - lon * 0.3) * (0.7 if variable != WeatherVariable.PRECIPITATION else 2.2)
            predictions["pangu"][lead] = max(0.0, round(true_signal * 0.98 + pangu_err, 1))

        return predictions

    def get_gridded_forecast(
        self,
        variable: WeatherVariable,
        lead_time_hours: int,
        model_id: str,
    ) -> List[GridCell]:
        coords = generate_domain_coordinates(resolution_deg=1.5)  # Fast spatial mesh
        cells = []

        for lat, lon in coords:
            base = self._get_base_signal(lat, lon, variable, lead_time_hours)
            # Apply model specific signature
            if model_id == "gfs":
                val = max(0.0, base * 1.12 + math.sin(lat) * 1.5)
            elif model_id == "ecmwf":
                val = max(0.0, base * 1.01 + math.cos(lon) * 1.0)
            elif model_id == "graphcast":
                val = max(0.0, base * 0.99 + math.sin(lat + lon) * 0.8)
            elif model_id == "pangu":
                val = max(0.0, base * 0.97 + math.cos(lat - lon) * 0.9)
            else:
                val = base
            cells.append(GridCell(lat=lat, lon=lon, value=round(val, 1)))

        return cells

    def get_ground_truth_point(
        self,
        lat: float,
        lon: float,
        variable: WeatherVariable,
        lead_time_hours: int,
    ) -> float:
        # Ground truth is the base atmospheric signal with minimal observational noise
        val = self._get_base_signal(lat, lon, variable, lead_time_hours)
        return max(0.0, round(val, 1))
