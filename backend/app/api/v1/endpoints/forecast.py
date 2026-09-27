from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.models.domain import (
    GeoPoint,
    GriddedForecastResponse,
    PointForecastItem,
    PointForecastResponse,
    WeatherRegime,
    WeatherVariable,
)
from backend.app.services.simulated_provider import SimulatedForecastProvider
from backend.app.services.blender_service import AdaptiveSoftmaxBlender
from backend.app.services.regime.service import RegimeClassificationService
from backend.app.services.blending.engine import ForecastBlendingEngine
from backend.app.services.blending.schemas import (
    BlendedForecastResult,
    ForecastBlendRequest,
)
from backend.app.services.blending.store import BlendedForecastStore
from backend.app.data.stations import REFERENCE_STATIONS, get_all_stations, get_station_by_id
from backend.app.utils.geo import find_nearest_station
from backend.app.config.settings import settings

router = APIRouter()
provider = SimulatedForecastProvider()
blender = AdaptiveSoftmaxBlender()
regime_service = RegimeClassificationService()
blending_engine = ForecastBlendingEngine()


@router.get("/stations", response_model=List[GeoPoint])
def list_stations():
    """List all registered meteorological observatories across India."""
    return get_all_stations()


@router.get("/point", response_model=PointForecastResponse)
def get_point_forecast(
    station_id: Optional[str] = Query(None, description="Station code, e.g., DEL, BOM, BLR"),
    lat: Optional[float] = Query(None, description="Latitude in decimal degrees"),
    lon: Optional[float] = Query(None, description="Longitude in decimal degrees"),
    variable: WeatherVariable = Query(WeatherVariable.PRECIPITATION, description="Forecast variable"),
):
    """
    Get 7-day multi-model meteogram forecast for a specific location.
    Renders raw predictions from GFS, ECMWF, GraphCast, Pangu alongside
    the dynamically blended consensus and confidence bounds.
    """
    if station_id:
        try:
            station = get_station_by_id(station_id)
            target_lat, target_lon = station.lat, station.lon
            st_name = station.name
            st_id = station_id.upper()
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found.")
    elif lat is not None and lon is not None:
        closest_id, closest_st, dist = find_nearest_station(lat, lon)
        target_lat, target_lon = lat, lon
        st_name = f"Custom Coord ({lat:.2f}N, {lon:.2f}E)"
        st_id = f"COORD-{round(lat, 2)}_{round(lon, 2)}"
    else:
        # Default to Mumbai
        station = REFERENCE_STATIONS["BOM"]
        target_lat, target_lon = station.lat, station.lon
        st_name = station.name
        st_id = "BOM"

    lead_times = settings.lead_times_hours
    raw_forecasts = provider.get_point_forecast(target_lat, target_lon, variable, lead_times)

    now = datetime.now()
    units_map = {
        WeatherVariable.PRECIPITATION: "mm/day",
        WeatherVariable.TEMPERATURE_2M: "°C",
        WeatherVariable.WIND_SPEED_10M: "km/h",
    }

    time_series: List[PointForecastItem] = []
    for lead in lead_times:
        preds = {m: raw_forecasts[m][lead] for m in raw_forecasts}
        weights = blender.compute_weights(
            target_lat, target_lon, lead, WeatherRegime.MONSOON_ACTIVE, variable
        )
        blended_val, conf_10, conf_90 = blender.blend_point(preds, weights, variable)

        valid_time_str = (now + timedelta(hours=lead)).strftime("%Y-%m-%d %H:00")
        time_series.append(
            PointForecastItem(
                valid_time=valid_time_str,
                lead_time_hours=lead,
                raw_predictions=preds,
                blended_value=blended_val,
                confidence_interval_10th=conf_10,
                confidence_interval_90th=conf_90,
            )
        )

    # Diagnose regime classification for forecast context
    rain_24h = provider._get_base_signal(target_lat, target_lon, WeatherVariable.PRECIPITATION, 24)
    temp_24h = provider._get_base_signal(target_lat, target_lon, WeatherVariable.TEMPERATURE_2M, 24)
    wind_24h = provider._get_base_signal(target_lat, target_lon, WeatherVariable.WIND_SPEED_10M, 24)
    temp_48h = provider._get_base_signal(target_lat, target_lon, WeatherVariable.TEMPERATURE_2M, 48)
    temp_trend = round(temp_48h - temp_24h, 2)

    weather_ctx = regime_service.build_context_from_forecast(
        temperature=temp_24h,
        rainfall=rain_24h,
        wind_speed=wind_24h,
        forecast_trends={"temp_trend_24h": temp_trend},
        station_id=st_id,
        region=st_name,
    )
    regime_diag = regime_service.classify_context(weather_ctx)

    return PointForecastResponse(
        station_id=st_id,
        station_name=st_name,
        lat=target_lat,
        lon=target_lon,
        variable=variable,
        unit=units_map[variable],
        generated_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        time_series=time_series,
        regime_context=regime_diag,
    )


@router.get("/grid", response_model=GriddedForecastResponse)
def get_gridded_forecast(
    variable: WeatherVariable = Query(WeatherVariable.PRECIPITATION),
    lead_time_hours: int = Query(24, description="Forecast lead time in hours (24, 48, 72, 96, 120, 144, 168)"),
    model_id: str = Query("blended", description="Model ID: blended, gfs, ecmwf, graphcast, or pangu"),
):
    """
    Retrieve gridded forecast field over India for GIS visualization.
    """
    now = datetime.now()
    valid_time_str = (now + timedelta(hours=lead_time_hours)).strftime("%Y-%m-%d %H:00")
    units_map = {
        WeatherVariable.PRECIPITATION: "mm/day",
        WeatherVariable.TEMPERATURE_2M: "°C",
        WeatherVariable.WIND_SPEED_10M: "km/h",
    }

    if model_id == "blended":
        # Compute blend across all models
        models = ["gfs", "ecmwf", "graphcast", "pangu"]
        model_grids = {m: provider.get_gridded_forecast(variable, lead_time_hours, m) for m in models}
        weights = blender.compute_weights(20.0, 78.0, lead_time_hours, WeatherRegime.MONSOON_ACTIVE, variable)
        grid_cells = blender.blend_grid(model_grids, weights, variable)
    else:
        grid_cells = provider.get_gridded_forecast(variable, lead_time_hours, model_id)

    vals = [c.value for c in grid_cells]
    min_v = min(vals) if vals else 0.0
    max_v = max(vals) if vals else 0.0
    mean_v = round(sum(vals) / len(vals), 1) if vals else 0.0

    return GriddedForecastResponse(
        variable=variable,
        unit=units_map[variable],
        lead_time_hours=lead_time_hours,
        model_id=model_id,
        valid_time=valid_time_str,
        min_value=min_v,
        max_value=max_v,
        mean_value=mean_v,
        grid_cells=grid_cells,
    )


# -------------------------------------------------------------------------
# Dynamic Forecast Blending Engine Endpoints
# -------------------------------------------------------------------------

@router.post("/blend", response_model=BlendedForecastResult, status_code=status.HTTP_200_OK)
def calculate_blended_forecast(request: ForecastBlendRequest):
    """
    Computes a dynamically blended forecast consensus across multiple models.
    Supports temperature, rainfall, wind_speed, and wind_direction.
    Wind direction uses circular/vector averaging (not naive arithmetic).
    Renormalizes weights if models are missing, rejects invalid atmospheric values,
    and returns itemized model contributions, weighted spread, and confidence bounds.
    """
    try:
        result = blending_engine.blend(
            variable=request.variable,
            lead_time_hours=request.lead_time_hours,
            station_id=request.station_id,
            latitude=request.latitude,
            longitude=request.longitude,
            timestamp=request.timestamp,
            region=request.region,
            weather_regime=request.weather_regime,
            model_forecasts=request.model_forecasts,
            model_weights=request.model_weights,
            persist=request.persist,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blending calculation failed: {str(e)}")


@router.get("/blended", response_model=BlendedForecastResult)
def get_blended_forecast_on_demand(
    variable: str = Query("temperature", description="Forecast variable: temperature, rainfall, wind_speed, wind_direction"),
    lead_time_hours: int = Query(24, ge=0, description="Lead time in hours"),
    station_id: Optional[str] = Query(None, description="Station ID (e.g. DEL, BOM, BLR)"),
    lat: Optional[float] = Query(None, description="Latitude in decimal degrees"),
    lon: Optional[float] = Query(None, description="Longitude in decimal degrees"),
    region: Optional[str] = Query(None, description="Geographical region"),
    weather_regime: Optional[str] = Query(None, description="Active weather regime context"),
    persist: bool = Query(True, description="Persist result into BlendedForecastStore"),
):
    """
    Retrieves dynamically blended multi-model forecast for a location and variable.
    """
    try:
        return blending_engine.blend(
            variable=variable,
            lead_time_hours=lead_time_hours,
            station_id=station_id,
            latitude=lat,
            longitude=lon,
            region=region,
            weather_regime=weather_regime,
            persist=persist,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Blending error: {str(e)}")


@router.get("/blended/history", response_model=List[BlendedForecastResult])
def get_blended_forecast_history(
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    variable: Optional[str] = Query(None, description="Filter by variable"),
    lead_time_hours: Optional[int] = Query(None, ge=0, description="Filter by lead time"),
    limit: int = Query(50, ge=1, le=500, description="Max records to return"),
):
    """
    Retrieves previously stored blended forecasts from the persistent store.
    """
    return blending_engine.store.query(
        station_id=station_id,
        variable=variable,
        lead_time_hours=lead_time_hours,
        limit=limit,
    )


@router.get("/blended/{forecast_id}", response_model=BlendedForecastResult)
def get_blended_forecast_by_id(forecast_id: str):
    """
    Retrieves an individual stored blended forecast record by its deterministic ID.
    """
    record = blending_engine.store.get_by_id(forecast_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Blended forecast '{forecast_id}' not found.")
    return record

