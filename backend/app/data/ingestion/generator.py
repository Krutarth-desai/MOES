import csv
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from backend.app.data.stations import REFERENCE_STATIONS
from backend.app.config.settings import SAMPLE_DIR


def generate_ground_truth_signal(
    lat: float,
    lon: float,
    var: str,
    lead_h: int,
    regime: str = "monsoon_active",
) -> float:
    """
    Simulates underlying true atmospheric physics over the Indian subcontinent.
    """
    lead_phase = math.sin(lead_h * 0.05)

    if var == "rainfall":
        # Orographic peak over Western Ghats & Northeast
        west_ghats = math.exp(-((lon - 73.8) ** 2) / 1.5 - ((lat - 15.0) ** 2) / 30.0)
        northeast = math.exp(-((lon - 92.5) ** 2) / 3.0 - ((lat - 25.5) ** 2) / 4.0)
        arid_shield = 1.0 - 0.85 * math.exp(-((lon - 71.5) ** 2) / 12.0 - ((lat - 27.0) ** 2) / 15.0)

        rain = (55.0 * west_ghats + 70.0 * northeast + 10.0) * arid_shield
        val = max(0.0, rain + 8.0 * lead_phase)
        return round(val, 1)

    elif var == "temperature":
        # Hot in northwest plains, cooler in hills and peninsular coasts
        lat_gradient = (38.0 - lat) * 0.45
        desert_heat = 11.0 * math.exp(-((lon - 73.0) ** 2) / 25.0 - ((lat - 28.0) ** 2) / 20.0)
        coastal_moderation = -3.0 if (lon < 74.0 or lon > 84.0) and lat < 22.0 else 0.0
        val = 24.0 + lat_gradient + desert_heat + coastal_moderation + 1.2 * lead_phase
        return round(val, 1)

    elif var == "wind_speed":
        # Monsoonal Arabian Sea westerlies
        coastal_jet = 26.0 * math.exp(-((lon - 72.0) ** 2) / 8.0 - ((lat - 15.0) ** 2) / 40.0)
        val = 14.0 + coastal_jet + 3.5 * lead_phase
        return round(val, 1)

    elif var == "wind_direction":
        # Predominant South-Westerly monsoon flow (~220° - 250°)
        val = 230.0 + 15.0 * math.sin(lat * 0.5)
        return round(val % 360.0, 1)

    return 0.0


def build_sample_datasets():
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    init_time = datetime(2026, 7, 15, 0, 0, 0)
    lead_times = [24, 48, 72, 96, 120, 144, 168]
    variables = ["temperature", "rainfall", "wind_speed", "wind_direction"]

    stations_list = list(REFERENCE_STATIONS.items())

    # 1. Ground Truth Dataset
    gt_rows: List[Dict[str, Any]] = []

    # 2. NWP Model A (GFS-like)
    nwp_a_rows: List[Dict[str, Any]] = []

    # 3. NWP Model B (ECMWF-like)
    nwp_b_rows: List[Dict[str, Any]] = []

    # 4. Ensemble Forecast (GEFS/EPS-like)
    ens_rows: List[Dict[str, Any]] = []

    # 5. AI/ML Forecast (GraphCast-like JSON)
    ai_records: List[Dict[str, Any]] = []

    for sid, st in stations_list:
        for lead in lead_times:
            valid_dt = init_time + timedelta(hours=lead)
            valid_str = valid_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            init_str = init_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            for var in variables:
                truth = generate_ground_truth_signal(st.lat, st.lon, var, lead)

                # Ground Truth
                gt_rows.append({
                    "timestamp": valid_str,
                    "latitude": st.lat,
                    "longitude": st.lon,
                    "forecast_variable": var,
                    "forecast_value": truth,
                    "forecast_initialization_time": init_str,
                    "lead_time": lead,
                    "model_name": "Ground Truth Observation",
                    "region": st.region_type or "India",
                    "season": "monsoon",
                    "weather_regime": "monsoon_active",
                    "station_id": sid,
                    "unit": "C" if var == "temperature" else ("mm" if var == "rainfall" else ("km/h" if var == "wind_speed" else "deg")),
                })

                # NWP Model A: Systematic wet bias on rain (+20%), cold bias in plains (-1.5°C), good wind
                if var == "rainfall":
                    val_a = round(truth * 1.20 + 3.0 * math.sin(lead * 0.3), 1)
                elif var == "temperature":
                    val_a = round(truth - 1.4 + 0.8 * math.cos(lead * 0.2), 1)
                elif var == "wind_speed":
                    val_a = round(truth * 1.05 + 1.2 * math.sin(st.lat), 1)
                else:
                    val_a = round((truth + 8.0) % 360.0, 1)

                nwp_a_rows.append({
                    "timestamp": valid_str,
                    "latitude": st.lat,
                    "longitude": st.lon,
                    "forecast_variable": var,
                    "forecast_value": val_a,
                    "forecast_initialization_time": init_str,
                    "lead_time": lead,
                    "model_name": "NWP Model A (GFS-like)",
                    "region": st.region_type or "India",
                    "season": "monsoon",
                    "weather_regime": "monsoon_active",
                    "station_id": sid,
                    "unit": "C" if var == "temperature" else ("mm" if var == "rainfall" else ("km/h" if var == "wind_speed" else "deg")),
                })

                # NWP Model B: Well-calibrated temp, conservative rain peaks (-15% on extremes)
                if var == "rainfall":
                    val_b = round(truth * 0.88 + 1.5 * math.cos(lead * 0.4), 1)
                elif var == "temperature":
                    val_b = round(truth + 0.2 + 0.4 * math.sin(lead * 0.1), 1)
                elif var == "wind_speed":
                    val_b = round(truth * 0.98 + 0.8 * math.cos(st.lon), 1)
                else:
                    val_b = round((truth - 5.0) % 360.0, 1)

                nwp_b_rows.append({
                    "timestamp": valid_str,
                    "latitude": st.lat,
                    "longitude": st.lon,
                    "forecast_variable": var,
                    "forecast_value": val_b,
                    "forecast_initialization_time": init_str,
                    "lead_time": lead,
                    "model_name": "NWP Model B (ECMWF-like)",
                    "region": st.region_type or "India",
                    "season": "monsoon",
                    "weather_regime": "monsoon_active",
                    "station_id": sid,
                    "unit": "C" if var == "temperature" else ("mm" if var == "rainfall" else ("km/h" if var == "wind_speed" else "deg")),
                })

                # Ensemble Forecast: Smoothed mean, higher spread at Day 4-7
                decay_smooth = 1.0 - 0.08 * (lead / 168.0)
                if var == "rainfall":
                    val_ens = round(truth * 0.95 * decay_smooth + 2.0, 1)
                elif var == "temperature":
                    val_ens = round(truth * 0.99, 1)
                elif var == "wind_speed":
                    val_ens = round(truth * 0.96, 1)
                else:
                    val_ens = round(truth % 360.0, 1)

                ens_rows.append({
                    "timestamp": valid_str,
                    "latitude": st.lat,
                    "longitude": st.lon,
                    "forecast_variable": var,
                    "forecast_value": val_ens,
                    "forecast_initialization_time": init_str,
                    "lead_time": lead,
                    "model_name": "Ensemble Forecast (GEFS/EPS-like)",
                    "region": st.region_type or "India",
                    "season": "monsoon",
                    "weather_regime": "monsoon_active",
                    "station_id": sid,
                    "unit": "C" if var == "temperature" else ("mm" if var == "rainfall" else ("km/h" if var == "wind_speed" else "deg")),
                })

                # AI/ML Forecast: Exceptional skill at 24-48h, slight smoothing on rain peaks at 120h+
                if lead <= 48:
                    ai_err_factor = 0.995
                    ai_noise = 0.2
                else:
                    ai_err_factor = 0.91 if var == "rainfall" else 0.98
                    ai_noise = 1.1

                if var == "rainfall":
                    val_ai = max(0.0, round(truth * ai_err_factor + ai_noise * math.sin(lead), 1))
                elif var == "temperature":
                    val_ai = round(truth * ai_err_factor + ai_noise * 0.3, 1)
                elif var == "wind_speed":
                    val_ai = round(truth * 0.99 + 0.4 * math.cos(lead), 1)
                else:
                    val_ai = round((truth + 2.0) % 360.0, 1)

                ai_records.append({
                    "timestamp": valid_str,
                    "latitude": st.lat,
                    "longitude": st.lon,
                    "forecast_variable": var,
                    "forecast_value": val_ai,
                    "forecast_initialization_time": init_str,
                    "lead_time": lead,
                    "model_name": "AI/ML Forecast (GraphCast-like)",
                    "region": st.region_type or "India",
                    "season": "monsoon",
                    "weather_regime": "monsoon_active",
                    "station_id": sid,
                    "unit": "C" if var == "temperature" else ("mm" if var == "rainfall" else ("km/h" if var == "wind_speed" else "deg")),
                })

    # Inject intentional unit conversion & validation edge cases for pipeline testing:
    # 1. In NWP Model A: add a row with temperature in Kelvin
    nwp_a_rows.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 28.6139,
        "longitude": 77.2090,
        "forecast_variable": "temperature",
        "forecast_value": 308.15,  # 308.15 K = 35.0 °C
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 24,
        "model_name": "NWP Model A (GFS-like)",
        "region": "Indo-Gangetic Plains",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "DEL",
        "unit": "K",  # Kelvin unit
    })
    # 2. In NWP Model A: add a row with negative rainfall (should be clamped to 0.0)
    nwp_a_rows.append({
        "timestamp": (init_time + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 26.2389,
        "longitude": 73.0243,
        "forecast_variable": "rainfall",
        "forecast_value": -4.5,  # Negative rain
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 48,
        "model_name": "NWP Model A (GFS-like)",
        "region": "Arid Northwest",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "JDH",
        "unit": "mm",
    })
    # 3. In NWP Model B: add a row with wind speed in knots
    nwp_b_rows.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 19.0760,
        "longitude": 72.8777,
        "forecast_variable": "wind_speed",
        "forecast_value": 30.0,  # 30 kt = 55.56 km/h
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 24,
        "model_name": "NWP Model B (ECMWF-like)",
        "region": "Western Ghats",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "BOM",
        "unit": "kt",  # Knots unit
    })
    # 4. In Ensemble Forecast: add a row with missing rainfall value
    ens_rows.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 12.9716,
        "longitude": 77.5946,
        "forecast_variable": "rainfall",
        "forecast_value": "",  # Missing value
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 24,
        "model_name": "Ensemble Forecast (GEFS/EPS-like)",
        "region": "Peninsular Plateau",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "BLR",
        "unit": "mm",
    })
    # 5. In AI Forecast JSON: add a record with rainfall in inches and compass bearing
    ai_records.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 25.5788,
        "longitude": 91.8933,
        "forecast_variable": "rainfall",
        "forecast_value": 2.5,  # 2.5 inches = 63.5 mm
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 24,
        "model_name": "AI/ML Forecast (GraphCast-like)",
        "region": "Northeast Hills",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "SHL",
        "unit": "in",  # Inches unit
    })
    ai_records.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 25.5788,
        "longitude": 91.8933,
        "forecast_variable": "wind_direction",
        "forecast_value": "SW",  # Compass bearing string
        "forecast_initialization_time": init_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lead_time": 24,
        "model_name": "AI/ML Forecast (GraphCast-like)",
        "region": "Northeast Hills",
        "season": "monsoon",
        "weather_regime": "monsoon_active",
        "station_id": "SHL",
        "unit": "deg",
    })

    # Write CSV files
    fieldnames = [
        "timestamp", "latitude", "longitude", "forecast_variable",
        "forecast_value", "forecast_initialization_time", "lead_time",
        "model_name", "region", "season", "weather_regime", "station_id", "unit"
    ]

    def write_csv(filepath: Path, rows: List[Dict[str, Any]]):
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(SAMPLE_DIR / "ground_truth.csv", gt_rows)
    write_csv(SAMPLE_DIR / "nwp_model_a.csv", nwp_a_rows)
    write_csv(SAMPLE_DIR / "nwp_model_b.csv", nwp_b_rows)
    write_csv(SAMPLE_DIR / "ensemble_forecast.csv", ens_rows)

    # Write JSON file
    with open(SAMPLE_DIR / "ai_forecast.json", mode="w", encoding="utf-8") as f:
        json.dump({"source": "AI/ML Forecast (GraphCast)", "records": ai_records}, f, indent=2)

    return {
        "ground_truth_count": len(gt_rows),
        "nwp_model_a_count": len(nwp_a_rows),
        "nwp_model_b_count": len(nwp_b_rows),
        "ensemble_forecast_count": len(ens_rows),
        "ai_forecast_count": len(ai_records),
    }


if __name__ == "__main__":
    counts = build_sample_datasets()
    print("Sample datasets generated successfully:")
    for k, v in counts.items():
        print(f"  - {k}: {v} records")
