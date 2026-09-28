from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from backend.app.models.domain import (
    ModelWeightItem,
    RegionalWeightSummary,
    SpatialWeightMapResponse,
    WeatherRegime,
    WeatherVariable,
)
from backend.app.services.blender_service import AdaptiveSoftmaxBlender

router = APIRouter()
blender = AdaptiveSoftmaxBlender()

REGIONS = [
    {"name": "Western Ghats & Konkan", "lat": 16.0, "lon": 73.8, "elev": 900.0},
    {"name": "Northeast India (Assam & Meghalaya)", "lat": 25.5, "lon": 91.8, "elev": 1200.0},
    {"name": "Indo-Gangetic Plains", "lat": 28.6, "lon": 77.2, "elev": 210.0},
    {"name": "Arid Northwest (Rajasthan)", "lat": 26.5, "lon": 72.0, "elev": 250.0},
    {"name": "Peninsular Plateau", "lat": 13.0, "lon": 77.5, "elev": 900.0},
    {"name": "Eastern Coastal Belt", "lat": 20.0, "lon": 85.5, "elev": 30.0},
]

MODEL_DISPLAY = {
    "gfs": "NOAA GFS (NWP)",
    "ecmwf": "ECMWF IFS (NWP)",
    "graphcast": "DeepMind GraphCast (AI)",
    "pangu": "Pangu-Weather (AI)",
}


@router.get("/map", response_model=SpatialWeightMapResponse)
def get_model_weights(
    variable: WeatherVariable = Query(WeatherVariable.PRECIPITATION),
    lead_time_hours: int = Query(24, description="Forecast lead time (24, 48, 72, 96, 120, 144, 168)"),
    regime: WeatherRegime = Query(WeatherRegime.MONSOON_ACTIVE),
):
    """
    Retrieve spatial distribution of model weights across Indian meteorological sub-regions.
    Explains the adaptive balance between physics-based NWP and AI models.
    """
    regional_summaries: List[RegionalWeightSummary] = []

    for r in REGIONS:
        weights = blender.compute_weights(
            lat=r["lat"],
            lon=r["lon"],
            lead_time_hours=lead_time_hours,
            regime=regime,
            variable=variable,
            elevation_m=r["elev"],
        )

        dominant_m = max(weights.items(), key=lambda x: x[1])[0]

        items = [
            ModelWeightItem(
                model_id=m,
                model_name=MODEL_DISPLAY[m],
                weight=w,
                historical_skill_score=round(0.65 + w * 0.3, 2),
            )
            for m, w in weights.items()
        ]

        regional_summaries.append(
            RegionalWeightSummary(
                region_name=r["name"],
                lead_time_hours=lead_time_hours,
                dominant_model=MODEL_DISPLAY[dominant_m],
                weights=items,
            )
        )

    return SpatialWeightMapResponse(
        variable=variable,
        lead_time_hours=lead_time_hours,
        detected_regime=regime,
        regional_weights=regional_summaries,
    )


# -------------------------------------------------------------
# Adaptive Model Weight Engine Integration
# -------------------------------------------------------------
from backend.app.services.weighting import (
    AdaptiveWeightEngine,
    AdaptiveWeightOutput,
    ModelWeightMappingEngine,
    PointWeightRequest,
    RegionalSummaryResponse,
    RegionWeightSummary,
    SpatialWeightGridResponse,
    WeightCalculationRequest,
    WeightGridCell,
)
from backend.app.services.weighting.mapping import _cached_weight_grid

weight_engine = AdaptiveWeightEngine()
mapping_engine = ModelWeightMappingEngine(weight_engine=weight_engine)


@router.post("/calculate", response_model=AdaptiveWeightOutput)
def calculate_adaptive_weights(request: WeightCalculationRequest):
    """
    Dynamically calculate normalized model blending weights using verified historical skill.
    
    Considers:
    - Verified forecast error & categorical extreme threat scores
    - Forecast lead time
    - Geographic region
    - Season
    - Current weather regime
    - Target forecast variable
    
    Outputs:
    - Weight for each model strictly summing to 1.0
    - Model-level derivation explanations
    - Active safeguards (min/max floors, sample shrinkage, unseen fallbacks)
    """
    return weight_engine.calculate_weights(
        models=request.models,
        variable=request.variable,
        lead_time_hours=request.lead_time_hours,
        region=request.region,
        season=request.season,
        weather_regime=request.weather_regime,
        historical_performance=request.historical_performance,
        min_weight=request.min_weight,
        max_weight=request.max_weight,
    )


@router.get("/dynamic", response_model=AdaptiveWeightOutput)
def calculate_dynamic_weights_get(
    variable: str = Query("rainfall", description="Target variable"),
    lead_time_hours: int = Query(24, description="Forecast lead time in hours"),
    region: Optional[str] = Query(None, description="Geographic region"),
    season: Optional[str] = Query(None, description="Season"),
    weather_regime: Optional[str] = Query(None, description="Weather regime"),
    models: Optional[List[str]] = Query(
        default=["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI/ML Forecast"],
        description="Forecast models to blend"
    ),
):
    """
    Convenience GET endpoint to inspect dynamic adaptive weights for standard operational models.
    """
    return weight_engine.calculate_weights(
        models=models,
        variable=variable,
        lead_time_hours=lead_time_hours,
        region=region,
        season=season,
        weather_regime=weather_regime,
    )


# -------------------------------------------------------------
# Model Weight Mapping & Geographic Grid APIs
# -------------------------------------------------------------

@router.get("/grid", response_model=SpatialWeightGridResponse)
def get_geographic_weight_grid(
    variable: str = Query("rainfall", description="Target variable: rainfall, temperature, wind_speed"),
    lead_time_hours: int = Query(24, ge=0, le=168, description="Forecast lead time in hours"),
    season: str = Query("monsoon", description="Season: monsoon, post_monsoon, winter, pre_monsoon"),
    weather_regime: str = Query("normal", description="Weather regime: normal, heavy_rain, heat_wave, high_wind, convective_storm"),
    resolution_deg: float = Query(3.0, ge=1.0, le=5.0, description="Spatial resolution in degrees (1.0 to 5.0)"),
    models: Optional[List[str]] = Query(None, description="Forecast models to blend"),
):
    """
    Returns full geographic weight-grid data across India suitable for interactive map rendering.

    Results are LRU-cached — identical parameter sets return instantly on subsequent calls.

    For each (lat, lon, variable, lead_time, season, regime):
    - Identifies dominant model with color coding
    - Computes weights for each contributing model
    - Computes weight distribution entropy and spread
    - Produces region-level reliability summaries

    Governance rule: Does NOT label any model as 'best' globally. Communicates context-dependent reliability.
    """
    active_models = models or ["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI/ML Forecast"]
    return _cached_weight_grid(
        variable=variable,
        lead_time_hours=lead_time_hours,
        season=season,
        weather_regime=weather_regime,
        grid_resolution_deg=resolution_deg,
        models_tuple=tuple(active_models),
    )


@router.get("/regional-summary", response_model=RegionalSummaryResponse)
def get_regional_weight_summary(
    variable: str = Query("rainfall", description="Target variable"),
    lead_time_hours: int = Query(24, ge=0, le=168, description="Forecast lead time in hours"),
    season: str = Query("monsoon", description="Season"),
    weather_regime: str = Query("normal", description="Weather regime"),
    models: Optional[List[str]] = Query(None, description="Forecast models to blend"),
):
    """
    Returns region-level model reliability summaries formatted as:
    
    Region A:
    Model A = 0.52
    Model B = 0.28
    Model C = 0.20
    """
    summaries = mapping_engine.generate_regional_summaries(
        variable=variable,
        lead_time_hours=lead_time_hours,
        season=season,
        weather_regime=weather_regime,
        models=models,
    )
    all_text = "\n\n".join(s.summary_formatted for s in summaries)
    return RegionalSummaryResponse(
        variable=variable,
        lead_time_hours=lead_time_hours,
        season=season,
        weather_regime=weather_regime,
        summaries=summaries,
        all_formatted_text=all_text,
    )


@router.post("/point", response_model=WeightGridCell)
def get_point_weight(request: PointWeightRequest):
    """
    Calculates model weights, dominant model, and distribution entropy at an arbitrary coordinate.
    """
    return mapping_engine.compute_cell_weights(
        lat=request.latitude,
        lon=request.longitude,
        variable=request.variable,
        lead_time_hours=request.lead_time_hours,
        season=request.season or "monsoon",
        weather_regime=request.weather_regime or "normal",
        models=request.models,
    )

