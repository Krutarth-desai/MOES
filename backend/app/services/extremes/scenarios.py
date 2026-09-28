from typing import Dict, List, Optional
from backend.app.services.extremes.schemas import AlertCategory, ScenarioDefinition


class ExtremeScenarioProvider:
    """
    Provides pre-packaged meteorological scenarios demonstrating the guidance engine:
    1. Heavy Rainfall (Monsoon convective deluge)
    2. Heat Wave (Extreme summer thermal anomaly)
    3. High Wind (Cyclonic squall / marine gale)
    4. Normal Conditions (Calm benign seasonal weather)
    """

    @classmethod
    def get_all_scenarios(cls) -> List[ScenarioDefinition]:
        return [
            cls.get_heavy_rainfall_scenario(),
            cls.get_heat_wave_scenario(),
            cls.get_high_wind_scenario(),
            cls.get_normal_conditions_scenario(),
        ]

    @classmethod
    def get_scenario_by_name(cls, name: str) -> Optional[ScenarioDefinition]:
        key = name.strip().lower().replace("-", "_").replace(" ", "_")
        scenarios = {s.category: s for s in cls.get_all_scenarios()}
        return scenarios.get(key)

    @classmethod
    def get_heavy_rainfall_scenario(cls) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id="scenario-heavy-rainfall-bom",
            name="Monsoon Convective Deluge (Western Ghats / Mumbai)",
            category="heavy_rainfall",
            description="Active monsoon low-pressure system creating intense orographic precipitation over the Konkan coast and Western Ghats.",
            station_id="BOM",
            location_name="Mumbai (Santacruz)",
            region="western_ghats",
            lead_time_hours=24,
            variable="rainfall",
            model_forecasts={
                "NWP Model A": 142.0,
                "NWP Model B": 128.5,
                "Ensemble Forecast": 134.0,
                "AI Forecast": 139.5,
            },
            blended_value=135.5,
            expected_alert_category=AlertCategory.RED,
        )

    @classmethod
    def get_heat_wave_scenario(cls) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id="scenario-heat-wave-nag",
            name="Severe Heat Wave (Central India / Vidarbha)",
            category="heat_wave",
            description="Intense dry north-westerly advection causing acute daytime heating with maximum temperatures exceeding 46°C.",
            station_id="NAG",
            location_name="Nagpur (Sonegaon)",
            region="plains",
            lead_time_hours=48,
            variable="temperature",
            model_forecasts={
                "NWP Model A": 45.8,
                "NWP Model B": 46.5,
                "Ensemble Forecast": 46.0,
                "AI Forecast": 46.8,
            },
            blended_value=46.3,
            expected_alert_category=AlertCategory.RED,
        )

    @classmethod
    def get_high_wind_scenario(cls) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id="scenario-high-wind-bbi",
            name="Coastal Squall & Gale Force Winds (Bay of Bengal / Odisha)",
            category="high_wind",
            description="Deep depression in the Bay of Bengal generating sustained gale-force coastal winds and turbulent offshore seas.",
            station_id="BBI",
            location_name="Bhubaneswar",
            region="coastal",
            lead_time_hours=24,
            variable="wind_speed",
            model_forecasts={
                "NWP Model A": 82.0,
                "NWP Model B": 74.5,
                "Ensemble Forecast": 77.0,
                "AI Forecast": 79.5,
            },
            blended_value=78.2,
            expected_alert_category=AlertCategory.RED,
        )

    @classmethod
    def get_normal_conditions_scenario(cls) -> ScenarioDefinition:
        return ScenarioDefinition(
            scenario_id="scenario-normal-blr",
            name="Normal Benign Weather (Peninsular Plateau / Bengaluru)",
            category="normal_conditions",
            description="Stable atmospheric conditions with light seasonal showers and comfortable temperatures well below any hazard thresholds.",
            station_id="BLR",
            location_name="Bengaluru",
            region="plains",
            lead_time_hours=24,
            variable="rainfall",
            model_forecasts={
                "NWP Model A": 4.5,
                "NWP Model B": 2.0,
                "Ensemble Forecast": 3.2,
                "AI Forecast": 2.8,
            },
            blended_value=3.1,
            expected_alert_category=AlertCategory.GREEN,
        )
