import logging
from typing import Any, Dict, List, Optional
from backend.app.services.extremes.schemas import (
    AlertCategory,
    ExtremeEventType,
    RegionalThresholdConfig,
    SeverityLevel,
    ThresholdLevelConfig,
)

logger = logging.getLogger("moes.extremes.thresholds")


class ExtremeThresholdRegistry:
    """
    Configurable, region-aware threshold registry for extreme weather hazards.
    
    Provides meteorological decision thresholds aligned with IMD (India Meteorological Department)
    and WMO standards, while allowing dynamic regional customizations and dataset overrides.
    """

    def __init__(self):
        self._thresholds: Dict[ExtremeEventType, Dict[str, ThresholdLevelConfig]] = {}
        self._load_default_thresholds()

    def _load_default_thresholds(self):
        """Initializes default meteorological thresholds by event type and regional climate zone."""
        # 1. Heavy Rainfall (mm / 24 hours)
        self._thresholds[ExtremeEventType.HEAVY_RAINFALL] = {
            "default": ThresholdLevelConfig(
                yellow_threshold=15.6,
                orange_threshold=64.5,
                red_threshold=115.6,
                unit="mm",
                description="IMD Standard: Yellow (15.6-64.4mm), Orange (64.5-115.5mm), Red (>=115.6mm)",
            ),
            "plains": ThresholdLevelConfig(
                yellow_threshold=15.6,
                orange_threshold=64.5,
                red_threshold=115.6,
                unit="mm",
                description="Standard plains drainage threshold",
            ),
            "western_ghats": ThresholdLevelConfig(
                yellow_threshold=35.0,
                orange_threshold=75.0,
                red_threshold=125.0,
                unit="mm",
                description="Western Ghats: higher orographic rainfall baseline with Red alert >=125.0mm",
            ),
            "hills": ThresholdLevelConfig(
                yellow_threshold=20.0,
                orange_threshold=50.0,
                red_threshold=90.0,
                unit="mm",
                description="Hilly / Himalayan slopes: heightened landslide and cloudburst vulnerability",
            ),
            "arid": ThresholdLevelConfig(
                yellow_threshold=10.0,
                orange_threshold=30.0,
                red_threshold=65.0,
                unit="mm",
                description="Arid Northwest: low soil permeability with flash-flood risk at lower rainfall",
            ),
            "coastal": ThresholdLevelConfig(
                yellow_threshold=25.0,
                orange_threshold=70.0,
                red_threshold=125.0,
                unit="mm",
                description="Coastal maritime zone: tidal interaction and urban waterlogging sensitivity",
            ),
        }

        # 2. Heat Wave (°C maximum temperature)
        self._thresholds[ExtremeEventType.HEAT_WAVE] = {
            "default": ThresholdLevelConfig(
                yellow_threshold=40.0,
                orange_threshold=42.0,
                red_threshold=45.0,
                unit="°C",
                description="IMD Plains standard: Yellow (40°C), Orange (42°C), Red (>=45°C)",
            ),
            "plains": ThresholdLevelConfig(
                yellow_threshold=40.0,
                orange_threshold=42.0,
                red_threshold=45.0,
                unit="°C",
                description="Standard plains thermal threshold",
            ),
            "coastal": ThresholdLevelConfig(
                yellow_threshold=36.0,
                orange_threshold=37.5,
                red_threshold=40.0,
                unit="°C",
                description="Coastal zone: lower temperature thresholds due to high relative humidity / heat index",
            ),
            "hills": ThresholdLevelConfig(
                yellow_threshold=30.0,
                orange_threshold=33.0,
                red_threshold=36.0,
                unit="°C",
                description="Hilly areas: mountain stations exhibit heatwave at significantly lower temperatures",
            ),
            "arid": ThresholdLevelConfig(
                yellow_threshold=42.0,
                orange_threshold=44.5,
                red_threshold=47.5,
                unit="°C",
                description="Desert/Arid plains: elevated summer baseline temperature",
            ),
        }

        # 3. High Wind (km/h sustained / squall gusts)
        self._thresholds[ExtremeEventType.HIGH_WIND] = {
            "default": ThresholdLevelConfig(
                yellow_threshold=39.0,
                orange_threshold=50.0,
                red_threshold=75.0,
                unit="km/h",
                description="IMD Squall/Gale standards: Yellow (39 km/h), Orange (50 km/h), Red (75 km/h)",
            ),
            "inland": ThresholdLevelConfig(
                yellow_threshold=35.0,
                orange_threshold=48.0,
                red_threshold=70.0,
                unit="km/h",
                description="Inland infrastructure wind tolerance",
            ),
            "coastal": ThresholdLevelConfig(
                yellow_threshold=45.0,
                orange_threshold=55.0,
                red_threshold=75.0,
                unit="km/h",
                description="Marine and coastal cyclone wind tolerance (Red Gale Warning >=75.0 km/h)",
            ),
            "hills": ThresholdLevelConfig(
                yellow_threshold=40.0,
                orange_threshold=55.0,
                red_threshold=75.0,
                unit="km/h",
                description="Mountain passes and ridge wind gusts",
            ),
        }

        # 4. Cold Wave (°C minimum temperature)
        self._thresholds[ExtremeEventType.COLD_WAVE] = {
            "default": ThresholdLevelConfig(
                yellow_threshold=10.0,
                orange_threshold=6.0,
                red_threshold=4.0,
                unit="°C",
                description="IMD Plains Cold Wave: Yellow (10°C), Orange (6°C), Red (<=4°C)",
            ),
            "plains": ThresholdLevelConfig(
                yellow_threshold=10.0,
                orange_threshold=6.0,
                red_threshold=4.0,
                unit="°C",
                description="Northern and Central plains cold wave criteria",
            ),
            "hills": ThresholdLevelConfig(
                yellow_threshold=2.0,
                orange_threshold=-1.0,
                red_threshold=-4.0,
                unit="°C",
                description="Sub-zero freeze warnings for mountain stations",
            ),
        }

        # 5. Severe Convective Storm / Squall (combined hourly intensity proxy)
        self._thresholds[ExtremeEventType.CONVECTIVE_STORM] = {
            "default": ThresholdLevelConfig(
                yellow_threshold=20.0,
                orange_threshold=40.0,
                red_threshold=65.0,
                unit="mm/h",
                description="Convective cloudburst / squall threshold",
            )
        }

    def get_thresholds(
        self,
        hazard_type: ExtremeEventType,
        region: Optional[str] = None,
    ) -> Tuple[ThresholdLevelConfig, str]:
        """
        Retrieves active threshold escalation levels for a given hazard and region.
        Falls back gracefully from region-specific configuration to 'default'.
        
        Returns:
            Tuple[ThresholdLevelConfig, source_description]
        """
        event_dict = self._thresholds.get(hazard_type)
        if not event_dict:
            # Fallback to default heavy rainfall if unknown
            event_dict = self._thresholds[ExtremeEventType.HEAVY_RAINFALL]
            return event_dict["default"], "Default Fallback"

        reg_key = region.strip().lower() if region else "default"
        # Match common geographic synonyms
        if "ghat" in reg_key:
            lookup_key = "western_ghats"
        elif "hill" in reg_key or "mount" in reg_key:
            lookup_key = "hills"
        elif "coast" in reg_key or "sea" in reg_key or "island" in reg_key:
            lookup_key = "coastal"
        elif "arid" in reg_key or "desert" in reg_key:
            lookup_key = "arid"
        elif "plain" in reg_key:
            lookup_key = "plains"
        else:
            lookup_key = reg_key

        if lookup_key in event_dict:
            return event_dict[lookup_key], f"Configured ({lookup_key.replace('_', ' ').title()})"
        return event_dict.get("default", list(event_dict.values())[0]), "IMD Default Standard"

    def set_custom_threshold(
        self,
        hazard_type: ExtremeEventType,
        region: str,
        levels: ThresholdLevelConfig,
    ):
        """Allows users, regional forecasters, or datasets to register customized alert boundaries."""
        if hazard_type not in self._thresholds:
            self._thresholds[hazard_type] = {}
        reg_clean = region.strip().lower()
        self._thresholds[hazard_type][reg_clean] = levels
        logger.info("Registered custom threshold for %s in region '%s': %s", hazard_type.value, reg_clean, levels)

    def get_all_thresholds(self) -> Dict[str, Dict[str, ThresholdLevelConfig]]:
        """Returns full active threshold registry."""
        return {
            hazard.value: {reg: conf for reg, conf in reg_dict.items()}
            for hazard, reg_dict in self._thresholds.items()
        }

    def reset_to_defaults(self):
        """Restores original IMD/WMO standard thresholds."""
        self._thresholds.clear()
        self._load_default_thresholds()
        logger.info("Restored default meteorological thresholds.")
