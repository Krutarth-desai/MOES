from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, Query
from backend.app.models.domain import RegimeClassificationResponse
from backend.app.services.regime import (
    ForecastContext,
    RegimeClassificationResult,
    RegimeClassificationService,
    RegimeType,
    WeatherContext,
)
from backend.app.services.regime_service import WeatherRegimeService

router = APIRouter()
regime_service = WeatherRegimeService()
classification_service = regime_service.classifier_service


@router.get("/current", response_model=RegimeClassificationResponse)
def get_current_regime():
    """
    Get active synoptic weather regime, synoptic drivers, and meteorological context.
    """
    return regime_service.get_current_regime()


@router.post("/classify", response_model=RegimeClassificationResult)
def classify_weather_situation(context: WeatherContext):
    """
    Classify an atmospheric situation into an operational regime.
    
    Evaluates:
    - temperature
    - rainfall
    - humidity (if available)
    - wind speed
    - pressure (if available)
    - recent rainfall (antecedent saturation)
    - forecast trends (temperature, barometric tendency)
    
    Returns:
    - regime name
    - confidence (0.0 to 1.0)
    - supporting indicators (meteorological threshold exceedances)
    """
    return classification_service.classify_context(context)


@router.post("/classify/batch", response_model=List[RegimeClassificationResult])
def classify_spatial_batch(contexts: List[WeatherContext]):
    """
    Classify a batch of spatial contexts (e.g. across multiple stations or grid points).
    """
    return classification_service.classify_spatial(contexts)


@router.get("/stations", response_model=Dict[str, Any])
def get_station_regimes():
    """
    Diagnoses current weather regime across all standard IMD reference observatories in India.
    """
    return classification_service.get_reference_station_regimes()


@router.get("/types")
def list_regime_types():
    """
    Lists all supported operational weather regimes and their meteorological criteria.
    """
    return {
        "supported_regimes": [
            {
                "regime_type": RegimeType.NORMAL.value,
                "description": "Benign seasonal conditions within climatological envelopes.",
                "key_variables": ["temperature", "rainfall", "wind_speed"],
                "hazard_level": "NORMAL",
            },
            {
                "regime_type": RegimeType.HEAVY_RAIN.value,
                "description": "Intense or prolonged precipitation meeting IMD Heavy/Extremely Heavy rainfall criteria (>= 64.5 mm/24h or antecedent saturation).",
                "key_variables": ["rainfall", "recent_rainfall", "humidity"],
                "hazard_level": "MODERATE to EXTREME",
            },
            {
                "regime_type": RegimeType.CONVECTIVE_STORM.value,
                "description": "Rapid convective intensification characterized by concurrent squally winds, localized cloudburst, rapid barometric drop, or cold-pool outflow.",
                "key_variables": ["rainfall", "wind_speed", "pressure", "forecast_trends", "humidity"],
                "hazard_level": "SEVERE",
            },
            {
                "regime_type": RegimeType.HEAT_WAVE.value,
                "description": "Severe thermal stress exceeding IMD Heatwave thresholds (>= 40°C in plains, >= 30°C in hills) accompanied by dry air or rising trends.",
                "key_variables": ["temperature", "humidity", "forecast_trends", "elevation_m"],
                "hazard_level": "MODERATE to EXTREME",
            },
            {
                "regime_type": RegimeType.HIGH_WIND.value,
                "description": "Sustained surface winds exceeding gale or storm force thresholds (>= 48 km/h).",
                "key_variables": ["wind_speed", "wind_direction"],
                "hazard_level": "MODERATE to EXTREME",
            },
            {
                "regime_type": RegimeType.COLD_SPELL.value,
                "description": "Cold wave conditions with severe minimum temperature departures (<= 7°C in plains, <= 0°C in hills, or rapid plunge).",
                "key_variables": ["temperature", "forecast_trends", "elevation_m"],
                "hazard_level": "MODERATE to SEVERE",
            },
            {
                "regime_type": RegimeType.DRY_EXTREME_DRY.value,
                "description": "Severe atmospheric moisture deficit and precipitation drought (0 mm rain, low antecedent rain, relative humidity <= 25%).",
                "key_variables": ["rainfall", "recent_rainfall", "humidity", "temperature"],
                "hazard_level": "MODERATE to SEVERE",
            },
        ],
        "active_classifier": classification_service.active_classifier.classifier_name,
    }


@router.post("/forecast-context", response_model=ForecastContext)
def create_forecast_context(
    station_id: str = Query("BOM", description="Station identifier"),
    lead_time_hours: int = Query(24, description="Forecast lead time in hours"),
    temperature: float = Query(..., description="Surface temperature (°C)"),
    rainfall: float = Query(0.0, description="Cumulative rainfall (mm)"),
    wind_speed: float = Query(10.0, description="Wind speed (km/h)"),
    humidity: float = Query(None, description="Relative humidity (%)"),
    pressure: float = Query(None, description="MSLP in hPa"),
    recent_rainfall: float = Query(0.0, description="Past 3-7 day rainfall in mm"),
):
    """
    Builds an integrated ForecastContext by synthesizing atmospheric variables
    and diagnosing the operational weather regime.
    """
    return classification_service.build_forecast_context(
        station_id=station_id,
        lead_time_hours=lead_time_hours,
        temperature=temperature,
        rainfall=rainfall,
        wind_speed=wind_speed,
        humidity=humidity,
        pressure=pressure,
        recent_rainfall=recent_rainfall,
    )
