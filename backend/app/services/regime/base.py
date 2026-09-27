from abc import ABC, abstractmethod
from typing import List
from backend.app.services.regime.schemas import RegimeClassificationResult, WeatherContext


class WeatherRegimeClassifier(ABC):
    """
    Abstract interface for Weather Regime Classifiers.
    Enables rule-based classifiers to be replaced or ensembled with
    supervised ML classifiers (Random Forest, LightGBM, SOM, or Neural Networks)
    without modifying consuming services or API routes.
    """

    @property
    @abstractmethod
    def classifier_name(self) -> str:
        """Identifier for the classifier implementation."""
        pass

    @abstractmethod
    def classify(self, context: WeatherContext) -> RegimeClassificationResult:
        """
        Classify an atmospheric situation into an operational regime.
        
        Args:
            context: Multi-variable weather state (temperature, rainfall, wind,
                     pressure, humidity, recent rainfall, forecast trends).
                     
        Returns:
            RegimeClassificationResult: Diagnosed regime, confidence, and supporting indicators.
        """
        pass

    @abstractmethod
    def classify_spatial(self, contexts: List[WeatherContext]) -> List[RegimeClassificationResult]:
        """
        Classify a batch of spatial contexts (e.g. across multiple meteorological stations).
        """
        pass


# Backward-compatible alias
BaseWeatherRegimeClassifier = WeatherRegimeClassifier
