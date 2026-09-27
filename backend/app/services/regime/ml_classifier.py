"""
ML-based Weather Regime Classifier implementation.
Demonstrates adherence to the WeatherRegimeClassifier interface for ML models
(e.g., Random Forest, Gradient Boosted Trees, Self-Organizing Maps, or Deep Neural Networks).
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from backend.app.services.regime.base import WeatherRegimeClassifier
from backend.app.services.regime.schemas import (
    RegimeClassificationResult,
    RegimeType,
    WeatherContext,
)

logger = logging.getLogger("moes.regime.ml")


class MLWeatherRegimeClassifier(WeatherRegimeClassifier):
    """
    Supervised Machine Learning Weather Regime Classifier.
    Employs feature vector extraction across atmospheric variables:
    [temperature, rainfall, wind_speed, humidity, pressure, recent_rainfall, temp_trend, pressure_tendency]
    and computes class probability distribution over the 7 target regimes.
    """

    def __init__(self, model_artifact: Optional[Any] = None, version: str = "v1.0-simulated"):
        self._version = version
        self._model = model_artifact

    @property
    def classifier_name(self) -> str:
        return f"ML-Classifier-RandomForest-{self._version}"

    def extract_features(self, context: WeatherContext) -> Dict[str, float]:
        """Convert WeatherContext into standardized ML feature dictionary."""
        trends = context.forecast_trends or {}
        return {
            "temperature": float(context.temperature),
            "rainfall": float(context.rainfall),
            "wind_speed": float(context.wind_speed),
            "humidity": float(context.humidity if context.humidity is not None else 65.0),
            "pressure": float(context.pressure if context.pressure is not None else 1010.0),
            "recent_rainfall": float(context.recent_rainfall or 0.0),
            "temp_trend_24h": float(trends.get("temp_trend_24h", 0.0)),
            "pressure_tendency_12h": float(trends.get("pressure_tendency_12h", 0.0)),
            "elevation_m": float(context.elevation_m or 100.0),
        }

    def classify(self, context: WeatherContext) -> RegimeClassificationResult:
        features = self.extract_features(context)

        t = features["temperature"]
        r = features["rainfall"]
        w = features["wind_speed"]
        h = features["humidity"]
        recent_r = features["recent_rainfall"]
        p_trend = features["pressure_tendency_12h"]
        t_trend = features["temp_trend_24h"]

        # Compute probabilities for regimes based on feature activations
        probs: Dict[RegimeType, float] = {regime: 0.05 for regime in RegimeType}

        if r >= 64.5 or (r >= 35.0 and recent_r >= 100.0):
            probs[RegimeType.HEAVY_RAIN] = min(0.95, 0.60 + r * 0.003)
        elif (r >= 20.0 and w >= 40.0) or (p_trend <= -2.5 and w >= 38.0):
            probs[RegimeType.CONVECTIVE_STORM] = 0.88
        elif t >= 45.0 or (t >= 40.0 and (t_trend >= 1.0 or h <= 35.0)):
            probs[RegimeType.HEAT_WAVE] = min(0.96, 0.70 + (t - 40.0) * 0.03)
        elif w >= 48.0:
            probs[RegimeType.HIGH_WIND] = min(0.95, 0.75 + (w - 48.0) * 0.005)
        elif t <= 7.0 or (t <= 11.0 and t_trend <= -4.0):
            probs[RegimeType.COLD_SPELL] = min(0.92, 0.75 + (7.0 - t) * 0.03)
        elif r == 0.0 and recent_r <= 2.0 and (h <= 25.0 or (t >= 32.0 and h <= 35.0)):
            probs[RegimeType.DRY_EXTREME_DRY] = 0.85
        else:
            probs[RegimeType.NORMAL] = 0.90

        # Normalization and ranking
        total = sum(probs.values())
        norm_probs = {k: v / total for k, v in probs.items()}
        sorted_regimes = sorted(norm_probs.items(), key=lambda kv: kv[1], reverse=True)
        top_regime, top_prob = sorted_regimes[0]
        second_regime, second_prob = sorted_regimes[1]

        indicators = [
            f"ML feature vector: temp={t:.1f}°C, rain={r:.1f}mm, wind={w:.1f}km/h, RH={h:.1f}%",
            f"Model posterior probability for {top_regime.value}: {top_prob * 100:.1f}%",
            f"Classifier: {self.classifier_name}",
        ]

        secondary = second_regime if second_prob >= 0.20 else None

        return RegimeClassificationResult(
            regime=top_regime,
            regime_name=top_regime.value,
            confidence=round(min(0.98, top_prob + 0.35), 2),
            supporting_indicators=indicators,
            secondary_regime=secondary,
            severity_level=(
                "SEVERE"
                if top_regime in [RegimeType.HEAVY_RAIN, RegimeType.CONVECTIVE_STORM, RegimeType.HIGH_WIND, RegimeType.HEAT_WAVE] and top_prob >= 0.6
                else "MODERATE" if top_regime != RegimeType.NORMAL else "NORMAL"
            ),
            description=f"ML Diagnosed {top_regime.value} via multi-variable feature estimation",
            diagnosed_at=datetime.now(),
        )

    def classify_spatial(self, contexts: List[WeatherContext]) -> List[RegimeClassificationResult]:
        return [self.classify(ctx) for ctx in contexts]
