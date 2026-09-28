from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.models.domain import HazardAlert
from backend.app.services.extremes.engine import ExtremeWeatherGuidanceEngine
from backend.app.services.extremes.scenarios import ExtremeScenarioProvider
from backend.app.services.extremes.schemas import (
    AlertCategory,
    ExtremeEventType,
    ExtremeWeatherGuidance,
    PointEvaluationRequest,
    RegionalThresholdConfig,
    ScenarioDefinition,
    SeverityLevel,
    ThresholdLevelConfig,
)
from backend.app.services.extremes.thresholds import ExtremeThresholdRegistry
from backend.app.services.simulated_provider import SimulatedForecastProvider
from backend.app.services.blender_service import AdaptiveSoftmaxBlender
from backend.app.services.extreme_service import ExtremeWeatherService

router = APIRouter()

# Instantiate core engines
provider = SimulatedForecastProvider()
blender = AdaptiveSoftmaxBlender()
legacy_extreme_service = ExtremeWeatherService(provider=provider, blender=blender)

threshold_registry = ExtremeThresholdRegistry()
guidance_engine = ExtremeWeatherGuidanceEngine(registry=threshold_registry)


# -----------------------------------------------------------------------------
# Structured Extreme Weather Guidance APIs
# -----------------------------------------------------------------------------

@router.get("/guidance", response_model=List[ExtremeWeatherGuidance])
def get_extreme_weather_guidance(
    lead_time_hours: int = Query(24, ge=0, le=168, description="Forecast lead time horizon in hours"),
    hazard_type: Optional[ExtremeEventType] = Query(None, description="Filter by hazard: heavy_rainfall, heat_wave, high_wind, cold_wave"),
    min_severity: Optional[SeverityLevel] = Query(None, description="Minimum severity: none, minor, moderate, severe, extreme"),
    region: Optional[str] = Query(None, description="Filter by region (e.g. western_ghats, coastal, plains)"),
):
    """
    Retrieves structured extreme weather guidance across India.
    Calculates probability/risk scores, severity levels, expected start/end times,
    affected regions, model consensus confidence, contributing models, and alert categories.
    Distinguishes forecast value, derived risk indicator, and alert threshold.
    """
    guidances = guidance_engine.scan_all_stations(
        lead_time_hours=lead_time_hours,
        hazard_filter=hazard_type,
        min_severity=min_severity,
    )
    if region:
        reg_clean = region.strip().lower()
        guidances = [g for g in guidances if reg_clean in g.affected_region.lower()]
    return guidances


@router.post("/evaluate", response_model=List[ExtremeWeatherGuidance])
def evaluate_point_guidance(request: PointEvaluationRequest):
    """
    On-demand evaluation of extreme weather hazards for a specific point, station, or custom forecast.
    Distinguishes forecast value, derived risk indicator, and alert threshold.
    """
    results: List[ExtremeWeatherGuidance] = []
    location = request.station_id or "Custom Location"
    region = request.region or "plains"
    lat = request.latitude or 19.07
    lon = request.longitude or 72.87

    # Evaluate Rainfall Hazard
    if request.rainfall is not None or (request.event_type == ExtremeEventType.HEAVY_RAINFALL):
        rain_val = request.rainfall if request.rainfall is not None else 65.0
        g_rain = guidance_engine.evaluate_point(
            event_type=ExtremeEventType.HEAVY_RAINFALL,
            forecast_value=rain_val,
            location_name=location,
            affected_region=region,
            latitude=lat,
            longitude=lon,
            lead_time_hours=request.lead_time_hours,
            station_id=request.station_id,
            model_forecasts=request.model_forecasts,
        )
        results.append(g_rain)

    # Evaluate Heat Wave Hazard
    if request.temperature is not None or (request.event_type == ExtremeEventType.HEAT_WAVE):
        temp_val = request.temperature if request.temperature is not None else 42.0
        g_temp = guidance_engine.evaluate_point(
            event_type=ExtremeEventType.HEAT_WAVE,
            forecast_value=temp_val,
            location_name=location,
            affected_region=region,
            latitude=lat,
            longitude=lon,
            lead_time_hours=request.lead_time_hours,
            station_id=request.station_id,
            model_forecasts=request.model_forecasts,
        )
        results.append(g_temp)

    # Evaluate High Wind Hazard
    if request.wind_speed is not None or (request.event_type == ExtremeEventType.HIGH_WIND):
        wind_val = request.wind_speed if request.wind_speed is not None else 55.0
        g_wind = guidance_engine.evaluate_point(
            event_type=ExtremeEventType.HIGH_WIND,
            forecast_value=wind_val,
            location_name=location,
            affected_region=region,
            latitude=lat,
            longitude=lon,
            lead_time_hours=request.lead_time_hours,
            station_id=request.station_id,
            model_forecasts=request.model_forecasts,
        )
        results.append(g_wind)

    if not results:
        # Default scan for specified event_type
        ev = request.event_type or ExtremeEventType.HEAVY_RAINFALL
        g_def = guidance_engine.evaluate_point(
            event_type=ev,
            forecast_value=0.0,
            location_name=location,
            affected_region=region,
            latitude=lat,
            longitude=lon,
            lead_time_hours=request.lead_time_hours,
            station_id=request.station_id,
        )
        results.append(g_def)

    return results


# -----------------------------------------------------------------------------
# Configurable Threshold Management APIs
# -----------------------------------------------------------------------------

@router.get("/thresholds", response_model=Dict[str, Dict[str, ThresholdLevelConfig]])
def get_all_hazard_thresholds():
    """
    Retrieves active configurable thresholds across all hazards and regions.
    """
    return threshold_registry.get_all_thresholds()


@router.put("/thresholds", status_code=status.HTTP_200_OK)
def update_hazard_threshold(config: RegionalThresholdConfig):
    """
    Registers custom or dataset-specific alert thresholds for a specific region and hazard.
    """
    threshold_registry.set_custom_threshold(
        hazard_type=config.hazard_type,
        region=config.region,
        levels=config.levels,
    )
    return {
        "status": "success",
        "message": f"Updated {config.hazard_type.value} thresholds for region '{config.region}'",
        "levels": config.levels,
    }


@router.post("/thresholds/reset", status_code=status.HTTP_200_OK)
def reset_thresholds_to_defaults():
    """
    Resets all threshold configurations back to official IMD/WMO standards.
    """
    threshold_registry.reset_to_defaults()
    return {"status": "success", "message": "Restored default IMD/WMO meteorological thresholds."}


# -----------------------------------------------------------------------------
# Sample Demonstration Scenarios
# -----------------------------------------------------------------------------

@router.get("/scenarios", response_model=List[ScenarioDefinition])
def list_demonstration_scenarios():
    """
    Lists pre-packaged sample scenarios demonstrating:
    - Heavy rainfall (Western Ghats monsoon deluge)
    - Heat wave (Central India thermal extremes)
    - High wind (Coastal squalls and gales)
    - Normal conditions (Calm benign seasonal weather)
    """
    scenarios = ExtremeScenarioProvider.get_all_scenarios()
    # Evaluate guidance for each scenario
    for s in scenarios:
        ev_type = (
            ExtremeEventType.HEAVY_RAINFALL if s.variable == "rainfall"
            else (ExtremeEventType.HEAT_WAVE if s.variable == "temperature" else ExtremeEventType.HIGH_WIND)
        )
        s.guidance = guidance_engine.evaluate_point(
            event_type=ev_type,
            forecast_value=s.blended_value,
            location_name=s.location_name,
            affected_region=s.region,
            latitude=19.0,
            longitude=73.0,
            lead_time_hours=s.lead_time_hours,
            station_id=s.station_id,
            model_forecasts=s.model_forecasts,
        )
    return scenarios


@router.get("/scenarios/{scenario_name}", response_model=ScenarioDefinition)
def get_scenario_guidance(scenario_name: str):
    """
    Retrieves and evaluates a specific scenario:
    - heavy_rainfall
    - heat_wave
    - high_wind
    - normal_conditions
    """
    sc = ExtremeScenarioProvider.get_scenario_by_name(scenario_name)
    if not sc:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{scenario_name}' not found. Available: heavy_rainfall, heat_wave, high_wind, normal_conditions"
        )

    ev_type = (
        ExtremeEventType.HEAVY_RAINFALL if sc.variable == "rainfall"
        else (ExtremeEventType.HEAT_WAVE if sc.variable == "temperature" else ExtremeEventType.HIGH_WIND)
    )
    sc.guidance = guidance_engine.evaluate_point(
        event_type=ev_type,
        forecast_value=sc.blended_value,
        location_name=sc.location_name,
        affected_region=sc.region,
        latitude=19.0,
        longitude=73.0,
        lead_time_hours=sc.lead_time_hours,
        station_id=sc.station_id,
        model_forecasts=sc.model_forecasts,
    )
    return sc


# -----------------------------------------------------------------------------
# Backward-Compatible Alert Endpoint
# -----------------------------------------------------------------------------

@router.get("/alerts", response_model=List[HazardAlert])
def get_extreme_alerts(
    lead_time_hours: int = Query(24, description="Forecast horizon for hazard scanning (24, 48, 72, 96, 120)")
):
    """
    Retrieve active severe weather warnings (Red, Orange, Yellow) based on IMD criteria
    for heavy rainfall, heatwaves, and gale winds.
    """
    return guidance_engine.detect_alerts(lead_time_hours=lead_time_hours)
