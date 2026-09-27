from datetime import datetime
from typing import Dict, List, Optional
from backend.app.models.domain import RegimeClassificationResponse, WeatherRegime
from backend.app.services.regime.rule_based import RuleBasedRegimeClassifier
from backend.app.services.regime.schemas import RegimeClassificationResult, RegimeType, WeatherContext
from backend.app.services.regime.service import RegimeClassificationService


class WeatherRegimeService:
    """
    Identifies synoptic atmospheric regimes affecting the Indian subcontinent.
    Integrates the deterministic RuleBasedRegimeClassifier and supports
    dynamic context classification across stations.
    """

    def __init__(self, classifier_service: Optional[RegimeClassificationService] = None):
        self.classifier_service = classifier_service or RegimeClassificationService()

    def classify_context(self, context: WeatherContext) -> RegimeClassificationResult:
        """Classify specific multi-variable weather conditions."""
        return self.classifier_service.classify_context(context)

    def classify_spatial(self, contexts: List[WeatherContext]) -> List[RegimeClassificationResult]:
        """Classify a batch of spatial contexts."""
        return self.classifier_service.classify_spatial(contexts)

    def build_forecast_context(self, **kwargs):
        """Constructs an integrated ForecastContext."""
        return self.classifier_service.build_forecast_context(**kwargs)

    def get_reference_station_regimes(self) -> Dict[str, Any]:
        """Diagnoses current regimes across reference stations."""
        return self.classifier_service.get_reference_station_regimes()

    def get_current_regime(self) -> RegimeClassificationResponse:
        current_month = datetime.now().month

        # Climatological regime determination (can be replaced by real-time SOM/K-means cluster)
        if 6 <= current_month <= 9:
            regime = WeatherRegime.MONSOON_ACTIVE
            name = "Southwest Monsoon (Active Trough)"
            summary = (
                "Deep monsoon trough extends from Ganganagar to Bay of Bengal. "
                "Strong low-level southwesterly flow along the west coast and convective activity over Central India."
            )
            features = [
                "Off-shore trough active along Western Ghats",
                "Monsoon low-pressure system over Bay of Bengal",
                "Strong cross-equatorial moisture flux (35-45 knots at 850 hPa)",
            ]
            confidence = 0.88
        elif 10 <= current_month <= 11:
            regime = WeatherRegime.POST_MONSOON_CYCLONE
            name = "Post-Monsoon / Northeast Monsoon Transition"
            summary = (
                "Transition season with high cyclogenetic potential over the Bay of Bengal and Arabian Sea. "
                "Onset of easterly waves over peninsular India."
            )
            features = [
                "Easterly shear and high upper-level divergence",
                "Warm sea surface temperatures (>28.5°C) in Bay of Bengal",
            ]
            confidence = 0.82
        elif 12 <= current_month or current_month <= 2:
            regime = WeatherRegime.WESTERN_DISTURBANCE
            name = "Western Disturbance / Winter Jet"
            summary = (
                "Subtropical westerly jet stream traversing Northern India. "
                "Extratropical cyclonic disturbances causing precipitation in Himalayan and NW plains."
            )
            features = [
                "Upper-tropospheric trough at 500 hPa",
                "Subtropical westerly jet > 90 knots",
            ]
            confidence = 0.85
        elif 3 <= current_month <= 5:
            regime = WeatherRegime.HEATWAVE_SYNOPTIC
            name = "Pre-Monsoon / Synoptic Heatwave"
            summary = (
                "Persistent anticyclonic subsidence over central and northwest India. "
                "Dry northwesterly advection leading to intense diurnal heating."
            )
            features = [
                "Anticyclone over Rajasthan and Central India",
                "Absence of moisture advection in mid-troposphere",
                "Maximum temperatures exceeding 42-45°C in plains",
            ]
            confidence = 0.91
        else:
            regime = WeatherRegime.NEUTRAL
            name = "Neutral Synoptic Flow"
            summary = "No dominant macro-scale synoptic anomaly detected."
            features = ["Normal seasonal circulation"]
            confidence = 0.75

        return RegimeClassificationResponse(
            active_regime=regime,
            regime_name=name,
            confidence=confidence,
            synoptic_summary=summary,
            dominant_features=features,
            valid_date=datetime.now().strftime("%Y-%m-%d"),
        )
