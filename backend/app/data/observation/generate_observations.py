import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from backend.app.data.stations import REFERENCE_STATIONS
from backend.app.data.ingestion.generator import generate_ground_truth_signal
from backend.app.config.settings import SAMPLE_DIR


def generate_sample_observations() -> Path:
    """
    Generates realistic ground-truth meteorological observation records
    at Indian observatories, synchronized with forecast valid times.
    """
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    init_time = datetime(2026, 7, 15, 0, 0, 0)
    lead_times = [24, 48, 72, 96, 120, 144, 168]

    obs_rows: List[Dict[str, Any]] = []

    for sid, st in REFERENCE_STATIONS.items():
        for lead in lead_times:
            valid_dt = init_time + timedelta(hours=lead)
            valid_str = valid_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Ground truth values for all 4 variables
            t_truth = generate_ground_truth_signal(st.lat, st.lon, "temperature", lead)
            r_truth = generate_ground_truth_signal(st.lat, st.lon, "rainfall", lead)
            ws_truth = generate_ground_truth_signal(st.lat, st.lon, "wind_speed", lead)
            wd_truth = generate_ground_truth_signal(st.lat, st.lon, "wind_direction", lead)

            obs_rows.append({
                "timestamp": valid_str,
                "latitude": st.lat,
                "longitude": st.lon,
                "temperature": t_truth,
                "rainfall": r_truth,
                "wind_speed": ws_truth,
                "wind_direction": wd_truth,
                "station_id": sid,
                "station_name": st.name,
                "elevation_m": st.elevation_m,
                "source": "IMD_OBSERVATIONAL_NETWORK",
            })

    # Add intentional test cases:
    # 1. Row with missing wind direction
    obs_rows.append({
        "timestamp": (init_time + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 28.6139,
        "longitude": 77.2090,
        "temperature": 34.2,
        "rainfall": 1.2,
        "wind_speed": 14.5,
        "wind_direction": "",  # Missing wind direction
        "station_id": "DEL_TEST",
        "station_name": "New Delhi Test Station",
        "elevation_m": 216.0,
        "source": "IMD_AWS_AUTOMATIC",
    })

    # 2. Row with negative rainfall (testing validation clamping)
    obs_rows.append({
        "timestamp": (init_time + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 19.0760,
        "longitude": 72.8777,
        "temperature": 29.8,
        "rainfall": -2.5,  # Negative rain
        "wind_speed": 22.0,
        "wind_direction": 240.0,
        "station_id": "BOM_TEST",
        "station_name": "Mumbai Marine Station",
        "elevation_m": 14.0,
        "source": "IMD_RADAR_RETRIEVAL",
    })

    # 3. Row with a +15 minute time offset (testing window matching)
    obs_rows.append({
        "timestamp": (init_time + timedelta(hours=24, minutes=15)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latitude": 12.9716,
        "longitude": 77.5946,
        "temperature": 25.4,
        "rainfall": 18.2,
        "wind_speed": 16.0,
        "wind_direction": 260.0,
        "station_id": "BLR_OFFSET",
        "station_name": "Bengaluru HAL Airport",
        "elevation_m": 920.0,
        "source": "AIRPORT_MET_OFFICE",
    })

    csv_path = SAMPLE_DIR / "observations.csv"
    json_path = SAMPLE_DIR / "observations.json"

    fieldnames = [
        "timestamp", "latitude", "longitude", "temperature",
        "rainfall", "wind_speed", "wind_direction", "station_id",
        "station_name", "elevation_m", "source"
    ]

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(obs_rows)

    with open(json_path, mode="w", encoding="utf-8") as f:
        json.dump({"network": "IMD Operational Surface Network", "observations": obs_rows}, f, indent=2)

    return csv_path


if __name__ == "__main__":
    p = generate_sample_observations()
    print(f"Sample observations created successfully at {p}")
