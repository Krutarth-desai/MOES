import logging
from typing import Dict, List, Optional
from backend.app.data.stations import REFERENCE_STATIONS, GeoPoint
from backend.app.services.regime.base import BaseWeatherRegimeClassifier, WeatherRegimeClassifier
from backend.app.services.regime.rule_based import RuleBasedRegimeClassifier
from backend.app.services.regime.schemas import (
    ForecastContext,
    RegimeClassificationResult,
    RegimeType,
    WeatherContext,
)

logger = logging.getLogger("moes.regime.service")


class RegimeClassificationService:
    """
    High-level Weather Regime Diagnostic Service.
    Coordinates the active regime classifier (rule-based or ML),
    assembles WeatherContext from station or gridded feeds,
    and attaches diagnosed regimes to forecast workflows.
    """

    def __init__(self, classifier: Optional[WeatherRegimeClassifier] = None):
        self._classifier: WeatherRegimeClassifier = classifier or RuleBasedRegimeClassifier()

    @property
    def active_classifier(self) -> WeatherRegimeClassifier:
        return self._classifier

    def set_classifier(self, classifier: WeatherRegimeClassifier):
        """
        Allows dynamically plugging in an ML classifier (e.g. Random Forest or Neural Network)
        to replace or benchmark against the rule-based classifier.
        """
        logger.info("Switching regime classifier to: %s", classifier.classifier_name)
        self._classifier = classifier

    def classify_context(self, context: WeatherContext) -> RegimeClassificationResult:
        """Classify a single atmospheric context."""
        return self._classifier.classify(context)

    def classify_spatial(self, contexts: List[WeatherContext]) -> List[RegimeClassificationResult]:
        """Classify a batch of atmospheric contexts across spatial locations."""
        return self._classifier.classify_spatial(contexts)

    def classify_stations_snapshot(
        self,
        station_measurements: Dict[str, Dict[str, float]],
    ) -> Dict[str, RegimeClassificationResult]:
        """
        Classifies current regime across multiple registered observatories given
        their weather variables.
        """
        results: Dict[str, RegimeClassificationResult] = {}

        for sid, vals in station_measurements.items():
            st_info = REFERENCE_STATIONS.get(sid.upper())
            ctx = WeatherContext(
                temperature=vals.get("temperature", 28.0),
                rainfall=vals.get("rainfall", 0.0),
                wind_speed=vals.get("wind_speed", 10.0),
                wind_direction=vals.get("wind_direction"),
                humidity=vals.get("humidity"),
                pressure=vals.get("pressure"),
                recent_rainfall=vals.get("recent_rainfall", 0.0),
                forecast_trends=vals.get("forecast_trends", {}),
                station_id=sid.upper(),
                region=st_info.region_type if st_info else "India",
                elevation_m=st_info.elevation_m if st_info else 100.0,
            )
            results[sid.upper()] = self._classifier.classify(ctx)

        return results

    def build_context_from_forecast(
        self,
        temperature: float,
        rainfall: float,
        wind_speed: float,
        wind_direction: Optional[float] = None,
        humidity: Optional[float] = None,
        pressure: Optional[float] = None,
        recent_rainfall: float = 0.0,
        forecast_trends: Optional[Dict[str, float]] = None,
        station_id: Optional[str] = None,
        region: Optional[str] = None,
        elevation_m: Optional[float] = None,
    ) -> WeatherContext:
        """Convenience factory creating a validated WeatherContext."""
        return WeatherContext(
            temperature=temperature,
            rainfall=rainfall,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            humidity=humidity,
            pressure=pressure,
            recent_rainfall=recent_rainfall,
            forecast_trends=forecast_trends or {},
            station_id=station_id,
            region=region or "Indian Subcontinent",
            elevation_m=elevation_m or 100.0,
        )

    def build_forecast_context(
        self,
        station_id: Optional[str] = None,
        station_name: Optional[str] = None,
        latitude: float = 20.0,
        longitude: float = 78.0,
        lead_time_hours: int = 24,
        temperature: float = 28.0,
        rainfall: float = 0.0,
        wind_speed: float = 10.0,
        wind_direction: Optional[float] = None,
        humidity: Optional[float] = None,
        pressure: Optional[float] = None,
        recent_rainfall: float = 0.0,
        forecast_trends: Optional[Dict[str, float]] = None,
        region: Optional[str] = None,
        elevation_m: Optional[float] = None,
    ) -> ForecastContext:
        """
        Synthesizes raw forecast state into a full ForecastContext
        enriched with the diagnosed operational weather regime.
        """
        ctx = self.build_context_from_forecast(
            temperature=temperature,
            rainfall=rainfall,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            humidity=humidity,
            pressure=pressure,
            recent_rainfall=recent_rainfall,
            forecast_trends=forecast_trends,
            station_id=station_id,
            region=region,
            elevation_m=elevation_m,
        )
        diagnosis = self.classify_context(ctx)

        weather_vars: Dict[str, float] = {
            "temperature": round(temperature, 2),
            "rainfall": round(rainfall, 2),
            "wind_speed": round(wind_speed, 2),
            "recent_rainfall": round(recent_rainfall, 2),
        }
        if humidity is not None:
            weather_vars["humidity"] = round(humidity, 1)
        if pressure is not None:
            weather_vars["pressure"] = round(pressure, 1)
        if wind_direction is not None:
            weather_vars["wind_direction"] = round(wind_direction, 1)

        return ForecastContext(
            station_id=station_id,
            station_name=station_name,
            latitude=latitude,
            longitude=longitude,
            lead_time_hours=lead_time_hours,
            weather_variables=weather_vars,
            regime_classification=diagnosis,
        )

    def get_reference_station_regimes(self) -> Dict[str, Dict[str, Any]]:
        """
        Diagnoses current weather regime across all standard IMD reference observatories
        using active meteorological ground/forecast states.
        """
        # Baseline regional meteorological profiles for standard observatories
        default_snapshots = {
            "BOM": {"temperature": 29.5, "rainfall": 82.0, "wind_speed": 42.0, "humidity": 92.0, "pressure": 1004.2, "recent_rainfall": 140.0},
            "DEL": {"temperature": 43.5, "rainfall": 0.0, "wind_speed": 18.0, "humidity": 22.0, "pressure": 1008.0, "recent_rainfall": 0.0},
            "BLR": {"temperature": 26.0, "rainfall": 4.5, "wind_speed": 14.0, "humidity": 68.0, "pressure": 1012.0, "recent_rainfall": 12.0},
            "CCU": {"temperature": 32.0, "rainfall": 28.0, "wind_speed": 44.0, "humidity": 88.0, "pressure": 1002.5, "recent_rainfall": 45.0, "forecast_trends": {"pressure_tendency_12h": -2.8}},
            "MAA": {"temperature": 34.0, "rainfall": 0.0, "wind_speed": 22.0, "humidity": 72.0, "pressure": 1009.5, "recent_rainfall": 0.0},
            "HYD": {"temperature": 38.0, "rainfall": 0.0, "wind_speed": 15.0, "humidity": 30.0, "pressure": 1011.0, "recent_rainfall": 0.0},
            "GHY": {"temperature": 28.0, "rainfall": 95.0, "wind_speed": 20.0, "humidity": 95.0, "pressure": 1006.0, "recent_rainfall": 180.0},
            "SXR": {"temperature": 3.5, "rainfall": 12.0, "wind_speed": 18.0, "humidity": 80.0, "pressure": 1015.0, "recent_rainfall": 25.0, "forecast_trends": {"temp_trend_24h": -4.5}},
            "JAI": {"temperature": 45.2, "rainfall": 0.0, "wind_speed": 16.0, "humidity": 18.0, "pressure": 1006.0, "recent_rainfall": 0.0},
            "PUN": {"temperature": 27.5, "rainfall": 8.0, "wind_speed": 12.0, "humidity": 65.0, "pressure": 1011.5, "recent_rainfall": 15.0},
        }

        results = {}
        for sid, st in REFERENCE_STATIONS.items():
            vals = default_snapshots.get(sid, {
                "temperature": 28.0,
                "rainfall": 5.0,
                "wind_speed": 12.0,
                "humidity": 60.0,
                "pressure": 1010.0,
                "recent_rainfall": 10.0,
            })
            ctx = WeatherContext(
                temperature=vals.get("temperature", 28.0),
                rainfall=vals.get("rainfall", 0.0),
                wind_speed=vals.get("wind_speed", 10.0),
                wind_direction=vals.get("wind_direction", 240.0),
                humidity=vals.get("humidity"),
                pressure=vals.get("pressure"),
                recent_rainfall=vals.get("recent_rainfall", 0.0),
                forecast_trends=vals.get("forecast_trends", {}),
                station_id=sid,
                region=st.region_type,
                elevation_m=st.elevation_m,
            )
            diagnosis = self.classify_context(ctx)
            results[sid] = {
                "station_id": sid,
                "station_name": st.name,
                "lat": st.lat,
                "lon": st.lon,
                "elevation_m": st.elevation_m,
                "region_type": st.region_type,
                "weather_variables": vals,
                "regime_classification": diagnosis,
            }

        return results
