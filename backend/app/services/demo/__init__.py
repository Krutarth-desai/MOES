"""SIH Presentation Demo Mode Package.

Provides deterministic scenarios demonstrating the full operational pipeline
for presentations and jury reviews.
"""

from backend.app.services.demo.schemas import (
    DemoScenarioId,
    DemoStageInfo,
    ModelPredictionItem,
    GeographicImpactZone,
    DemoScenarioResult,
)
from backend.app.services.demo.engine import SIHDemoEngine

__all__ = [
    "DemoScenarioId",
    "DemoStageInfo",
    "ModelPredictionItem",
    "GeographicImpactZone",
    "DemoScenarioResult",
    "SIHDemoEngine",
]
