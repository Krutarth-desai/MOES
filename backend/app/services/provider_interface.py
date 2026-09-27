from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from backend.app.models.domain import GridCell, WeatherVariable


class BaseForecastProvider(ABC):
    """
    Abstract Interface for Forecast Data Providers.
    
    Implementations can connect to:
    - Live Open-Meteo APIs (GFS / ECMWF / AI models)
    - Local NetCDF / Zarr operational archives
    - NCMRWF / IMD data feeds
    - Simulated realistic multi-model benchmark feeds
    """

    @abstractmethod
    def get_point_forecast(
        self,
        lat: float,
        lon: float,
        variable: WeatherVariable,
        lead_times_hours: List[int],
    ) -> Dict[str, Dict[int, float]]:
        """
        Retrieve forecast predictions from all active models for a single geographic point.
        
        Returns:
            Dict mapping model_id -> {lead_time_hours: predicted_value}
            e.g.:
            {
                "gfs": {24: 12.5, 48: 15.0, ...},
                "ecmwf": {24: 10.2, 48: 14.1, ...},
                "graphcast": {24: 11.0, 48: 13.8, ...},
                "pangu": {24: 9.8, 48: 13.2, ...}
            }
        """
        pass

    @abstractmethod
    def get_gridded_forecast(
        self,
        variable: WeatherVariable,
        lead_time_hours: int,
        model_id: str,
    ) -> List[GridCell]:
        """
        Retrieve gridded spatial forecast fields across the Indian domain for a given model.
        """
        pass

    @abstractmethod
    def get_ground_truth_point(
        self,
        lat: float,
        lon: float,
        variable: WeatherVariable,
        lead_time_hours: int,
    ) -> Optional[float]:
        """
        Retrieve observed or high-resolution reanalysis benchmark ground truth for verification.
        """
        pass
