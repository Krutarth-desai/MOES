from fastapi import APIRouter, Query
from backend.app.models.domain import ComparativeMetricsResponse, WeatherVariable
from backend.app.services.simulated_provider import SimulatedForecastProvider
from backend.app.services.blender_service import AdaptiveSoftmaxBlender
from backend.app.services.verification_service import ForecastVerificationService

router = APIRouter()
provider = SimulatedForecastProvider()
blender = AdaptiveSoftmaxBlender()
verifier = ForecastVerificationService(provider=provider, blender=blender)


@router.get("/skill-score", response_model=ComparativeMetricsResponse)
def get_skill_scorecard(
    variable: WeatherVariable = Query(WeatherVariable.PRECIPITATION),
    lead_time_hours: int = Query(48, description="Lead time in hours for verification"),
):
    """
    Evaluate multi-model verification metrics against ground truth.
    Demonstrates error reductions (MAE, RMSE) and higher CSI threat score
    achieved by the adaptive blending framework.
    """
    return verifier.evaluate_performance(variable=variable, lead_time_hours=lead_time_hours)
