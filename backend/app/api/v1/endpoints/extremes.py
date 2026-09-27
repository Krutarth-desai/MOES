from typing import List
from fastapi import APIRouter, Query
from backend.app.models.domain import HazardAlert
from backend.app.services.simulated_provider import SimulatedForecastProvider
from backend.app.services.blender_service import AdaptiveSoftmaxBlender
from backend.app.services.extreme_service import ExtremeWeatherService

router = APIRouter()
provider = SimulatedForecastProvider()
blender = AdaptiveSoftmaxBlender()
extreme_service = ExtremeWeatherService(provider=provider, blender=blender)


@router.get("/alerts", response_model=List[HazardAlert])
def get_extreme_alerts(
    lead_time_hours: int = Query(24, description="Forecast horizon for hazard scanning (24, 48, 72, 96, 120)")
):
    """
    Retrieve active severe weather warnings (Red, Orange, Yellow) based on IMD criteria
    for heavy rainfall, heatwaves, and gale winds.
    """
    return extreme_service.detect_alerts(lead_time_hours=lead_time_hours)
