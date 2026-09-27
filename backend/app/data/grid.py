from typing import List, Tuple
from backend.app.config.settings import settings


def generate_domain_coordinates(resolution_deg: float = 1.0) -> List[Tuple[float, float]]:
    """
    Generate lat/lon coordinate pairs covering the Indian subcontinent domain.
    Defaults to 1.0 degree for lightweight JSON delivery in web UI,
    configurable down to 0.25 degree for high-resolution processing.
    """
    domain = settings.domain
    lats = []
    lat = domain.min_lat
    while lat <= domain.max_lat:
        lats.append(round(lat, 2))
        lat += resolution_deg

    lons = []
    lon = domain.min_lon
    while lon <= domain.max_lon:
        lons.append(round(lon, 2))
        lon += resolution_deg

    grid = []
    for cur_lat in lats:
        for cur_lon in lons:
            # Filter loosely to South Asia / Indian landmass & immediate seas
            grid.append((cur_lat, cur_lon))

    return grid
