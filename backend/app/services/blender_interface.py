from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from backend.app.models.domain import GridCell, WeatherRegime, WeatherVariable


class BaseBlender(ABC):
    """
    Abstract interface for forecast blending and adaptive weighting algorithms.
    """

    @abstractmethod
    def compute_weights(
        self,
        lat: float,
        lon: float,
        lead_time_hours: int,
        regime: WeatherRegime,
        variable: WeatherVariable,
        elevation_m: float = 100.0,
    ) -> Dict[str, float]:
        """
        Compute normalized model weights summing to 1.0.
        """
        pass

    @abstractmethod
    def blend_point(
        self,
        raw_predictions: Dict[str, float],
        weights: Dict[str, float],
        variable: WeatherVariable,
    ) -> Tuple[float, float, float]:
        """
        Produce (blended_value, conf_10th, conf_90th).
        """
        pass

    @abstractmethod
    def blend_grid(
        self,
        model_grids: Dict[str, List[GridCell]],
        weights: Dict[str, float],
        variable: WeatherVariable,
    ) -> List[GridCell]:
        """
        Produce blended spatial grid from multiple model grid fields.
        """
        pass
