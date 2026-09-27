import math
from typing import Optional, Tuple
from backend.app.data.stations import REFERENCE_STATIONS, GeoPoint


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate great-circle distance between two geographic coordinates in kilometers.
    """
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def find_nearest_station(lat: float, lon: float) -> Tuple[str, GeoPoint, float]:
    """
    Find the closest registered station to given lat/lon.
    Returns (station_id, station_point, distance_km).
    """
    closest_id = None
    closest_station = None
    min_dist = float("inf")

    for sid, station in REFERENCE_STATIONS.items():
        dist = haversine_distance_km(lat, lon, station.lat, station.lon)
        if dist < min_dist:
            min_dist = dist
            closest_id = sid
            closest_station = station

    return closest_id, closest_station, min_dist
