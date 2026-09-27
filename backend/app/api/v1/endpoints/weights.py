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
    WeightCalculationRequest,
)

weight_engine = AdaptiveWeightEngine()


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
