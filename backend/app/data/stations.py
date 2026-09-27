from typing import Dict, List
from backend.app.models.domain import GeoPoint

REFERENCE_STATIONS: Dict[str, GeoPoint] = {
    "DEL": GeoPoint(
        lat=28.6139,
        lon=77.2090,
        name="New Delhi (Safdarjung)",
        elevation_m=216.0,
        region_type="plains",
    ),
    "BOM": GeoPoint(
        lat=19.0760,
        lon=72.8777,
        name="Mumbai (Santacruz)",
        elevation_m=14.0,
        region_type="coastal_west",
    ),
    "BLR": GeoPoint(
        lat=12.9716,
        lon=77.5946,
        name="Bengaluru",
        elevation_m=920.0,
        region_type="peninsular_plateau",
    ),
    "CCU": GeoPoint(
        lat=22.5726,
        lon=88.3639,
        name="Kolkata (Alipore)",
        elevation_m=9.0,
        region_type="coastal_east",
    ),
    "MAA": GeoPoint(
        lat=13.0827,
        lon=80.2707,
        name="Chennai (Meenambakkam)",
        elevation_m=16.0,
        region_type="coastal_coromandel",
    ),
    "SXR": GeoPoint(
        lat=34.0837,
        lon=74.7973,
        name="Srinagar",
        elevation_m=1585.0,
        region_type="himalayan",
    ),
    "JDH": GeoPoint(
        lat=26.2389,
        lon=73.0243,
        name="Jodhpur",
        elevation_m=231.0,
        region_type="arid_west",
    ),
    "SHL": GeoPoint(
        lat=25.5788,
        lon=91.8933,
        name="Shillong / Cherrapunji",
        elevation_m=1496.0,
        region_type="northeast_hills",
    ),
    "NAG": GeoPoint(
        lat=21.1458,
        lon=79.0882,
        name="Nagpur",
        elevation_m=310.0,
        region_type="central_india",
    ),
    "COK": GeoPoint(
        lat=9.9312,
        lon=76.2673,
        name="Kochi",
        elevation_m=5.0,
        region_type="coastal_west",
    ),
}


def get_all_stations() -> List[GeoPoint]:
    return list(REFERENCE_STATIONS.values())


def get_station_by_id(station_id: str) -> GeoPoint:
    sid = station_id.upper()
    if sid in REFERENCE_STATIONS:
        return REFERENCE_STATIONS[sid]
    raise KeyError(f"Station ID '{station_id}' not found in registered observatories.")
