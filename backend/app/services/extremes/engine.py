import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.data.stations import REFERENCE_STATIONS, get_all_stations, get_station_by_id
from backend.app.models.domain import AlertSeverity, HazardAlert, HazardType, WeatherRegime, WeatherVariable
from backend.app.services.blending.engine import ForecastBlendingEngine
from backend.app.services.extremes.schemas import (
    AlertCategory,
    AlertThresholdInfo,
    DerivedRiskIndicator,
    ExtremeEventType,
    ExtremeWeatherGuidance,
    SeverityLevel,
    ThresholdLevelConfig,
)
from backend.app.services.extremes.thresholds import ExtremeThresholdRegistry
from backend.app.services.simulated_provider import SimulatedForecastProvider

logger = logging.getLogger("moes.extremes.engine")


class ExtremeWeatherGuidanceEngine:
    """
    Operational Extreme Weather Guidance Engine.
    
    Synthesizes multi-model blended predictions and configurable regional thresholds to:
    1. Detect severe events: Heavy Rainfall, Heat Wave, High Wind, and Cold Wave.
    2. Calculate probabilistic risk indicators (with non-deterministic disclaimers).
    3. Determine severity levels and recommended color-coded alert categories.
    4. Compute expected onset and cessation time windows.
    5. Itemize contributing models, consensus confidence, and actionable advisories.
    
    CRITICAL ARCHITECTURAL GUARANTEE:
    Maintains strict separation between:
    - Forecast Value (predicted physical quantity)
    - Derived Risk Indicator (probabilistic potential / vulnerability index)
    - Alert Threshold (decision boundary applied)
    """

    def __init__(
        self,
        registry: Optional[ExtremeThresholdRegistry] = None,
        provider: Optional[SimulatedForecastProvider] = None,
        blending_engine: Optional[ForecastBlendingEngine] = None,
    ):
        self.registry = registry or ExtremeThresholdRegistry()
        self.provider = provider or SimulatedForecastProvider()
        self.blending_engine = blending_engine or ForecastBlendingEngine()

    def evaluate_point(
        self,
        event_type: ExtremeEventType,
        forecast_value: float,
        location_name: str,
        affected_region: str,
        latitude: float,
        longitude: float,
        lead_time_hours: int = 24,
        station_id: Optional[str] = None,
        model_forecasts: Optional[Dict[str, float]] = None,
        model_weights: Optional[Dict[str, float]] = None,
        reference_time: Optional[datetime] = None,
    ) -> ExtremeWeatherGuidance:
        """
        Evaluates a specific meteorological prediction against regional thresholds to generate structured guidance.
        """
        now = reference_time or datetime.now()
        onset_dt = now + timedelta(hours=max(0, lead_time_hours - 6))
        cessation_dt = now + timedelta(hours=lead_time_hours + 18)

        # 1. Retrieve Configurable Regional Thresholds
        threshold_config, threshold_src = self.registry.get_thresholds(event_type, affected_region)

        # 2. Determine Severity Level & Alert Category
        cat, sev, active_thresh = self._classify_event(event_type, forecast_value, threshold_config)

        # 3. Model Inputs & Confidence Assessment
        models_dict = model_forecasts or {
            "NWP Model A": round(forecast_value * 1.05, 1),
            "NWP Model B": round(forecast_value * 0.96, 1),
            "Ensemble Forecast": round(forecast_value * 0.98, 1),
            "AI Forecast": round(forecast_value * 1.01, 1),
        }
        contributing_models = list(models_dict.keys())

        # Confidence: inverse to normalized dispersion across model forecasts
        confidence = self._compute_confidence(list(models_dict.values()), forecast_value)

        # 4. Compute Derived Risk Indicator (Distinguished from Forecast Value & Alert Threshold)
        risk_indicator = self._compute_risk_indicator(
            event_type=event_type,
            forecast_value=forecast_value,
            threshold_config=threshold_config,
            model_forecasts=models_dict,
            model_weights=model_weights,
            active_threshold=active_thresh,
            severity_level=sev,
        )

        # 5. Alert Threshold Metadata Container
        all_levels = {
            "yellow": threshold_config.yellow_threshold,
            "orange": threshold_config.orange_threshold,
            "red": threshold_config.red_threshold,
        }
        threshold_info = AlertThresholdInfo(
            applied_threshold=active_thresh,
            alert_category=cat,
            threshold_unit=threshold_config.unit,
            threshold_source=threshold_src,
            all_threshold_levels=all_levels,
        )

        # 6. Construct Actionable Advisories & Headlines
        headline, detailed, actions = self._generate_advisory_text(
            event_type=event_type,
            severity=sev,
            category=cat,
            location=location_name,
            region=affected_region,
            forecast_value=forecast_value,
            unit=threshold_config.unit,
            risk_indicator=risk_indicator,
            lead_time_hours=lead_time_hours,
        )

        event_id = f"GUIDE-{event_type.value[:4].upper()}-{station_id or 'GRID'}-{lead_time_hours}H-{uuid.uuid4().hex[:6]}"

        return ExtremeWeatherGuidance(
            event_id=event_id,
            event_type=event_type,
            location_name=location_name,
            affected_region=affected_region,
            station_id=station_id,
            latitude=round(latitude, 4),
            longitude=round(longitude, 4),
            expected_start_time=onset_dt.strftime("%Y-%m-%dT%H:00:00Z"),
            expected_end_time=cessation_dt.strftime("%Y-%m-%dT%H:00:00Z"),
            lead_time_hours=lead_time_hours,
            severity_level=sev,
            recommended_alert_category=cat,
            confidence=round(confidence, 2),
            forecast_value=round(forecast_value, 1),
            forecast_unit=threshold_config.unit,
            derived_risk_indicator=risk_indicator,
            alert_threshold=threshold_info,
            contributing_models=contributing_models,
            individual_model_forecasts=models_dict,
            model_weights=model_weights,
            advisory_headline=headline,
            detailed_guidance=detailed,
            recommended_actions=actions,
            created_at=datetime.now(),
        )

    def scan_all_stations(
        self,
        lead_time_hours: int = 24,
        hazard_filter: Optional[ExtremeEventType] = None,
        min_severity: Optional[SeverityLevel] = None,
    ) -> List[ExtremeWeatherGuidance]:
        """
        Scans all registered meteorological stations across India to detect active extreme events.
        """
        stations = get_all_stations()
        results: List[ExtremeWeatherGuidance] = []
        now = datetime.now()

        severity_rank = {
            SeverityLevel.NONE: 0,
            SeverityLevel.MINOR: 1,
            SeverityLevel.MODERATE: 2,
            SeverityLevel.SEVERE: 3,
            SeverityLevel.EXTREME: 4,
        }
        min_rank = severity_rank.get(min_severity, 0) if min_severity else 0

        for sid, st in REFERENCE_STATIONS.items():
            # 1. Rainfall scan
            if not hazard_filter or hazard_filter == ExtremeEventType.HEAVY_RAINFALL:
                rain_res = self.blending_engine.blend(
                    variable="rainfall",
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    latitude=st.lat,
                    longitude=st.lon,
                    region=st.region_type or "plains",
                    persist=False,
                )
                guidance_rain = self.evaluate_point(
                    event_type=ExtremeEventType.HEAVY_RAINFALL,
                    forecast_value=rain_res.blended_value,
                    location_name=st.name,
                    affected_region=st.region_type or "plains",
                    latitude=st.lat,
                    longitude=st.lon,
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    model_forecasts=rain_res.individual_forecasts,
                    model_weights=rain_res.model_weights,
                    reference_time=now,
                )
                if severity_rank[guidance_rain.severity_level] >= min_rank:
                    results.append(guidance_rain)

            # 2. Temperature / Heatwave scan
            if not hazard_filter or hazard_filter == ExtremeEventType.HEAT_WAVE:
                temp_res = self.blending_engine.blend(
                    variable="temperature",
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    latitude=st.lat,
                    longitude=st.lon,
                    region=st.region_type or "plains",
                    persist=False,
                )
                guidance_temp = self.evaluate_point(
                    event_type=ExtremeEventType.HEAT_WAVE,
                    forecast_value=temp_res.blended_value,
                    location_name=st.name,
                    affected_region=st.region_type or "plains",
                    latitude=st.lat,
                    longitude=st.lon,
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    model_forecasts=temp_res.individual_forecasts,
                    model_weights=temp_res.model_weights,
                    reference_time=now,
                )
                if severity_rank[guidance_temp.severity_level] >= min_rank:
                    results.append(guidance_temp)

            # 3. High Wind scan
            if not hazard_filter or hazard_filter == ExtremeEventType.HIGH_WIND:
                wind_res = self.blending_engine.blend(
                    variable="wind_speed",
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    latitude=st.lat,
                    longitude=st.lon,
                    region=st.region_type or "plains",
                    persist=False,
                )
                guidance_wind = self.evaluate_point(
                    event_type=ExtremeEventType.HIGH_WIND,
                    forecast_value=wind_res.blended_value,
                    location_name=st.name,
                    affected_region=st.region_type or "plains",
                    latitude=st.lat,
                    longitude=st.lon,
                    lead_time_hours=lead_time_hours,
                    station_id=sid,
                    model_forecasts=wind_res.individual_forecasts,
                    model_weights=wind_res.model_weights,
                    reference_time=now,
                )
                if severity_rank[guidance_wind.severity_level] >= min_rank:
                    results.append(guidance_wind)

        return results

    def detect_alerts(self, lead_time_hours: int = 24) -> List[HazardAlert]:
        """
        Backward-compatible interface returning HazardAlert domain objects.
        """
        guidances = self.scan_all_stations(lead_time_hours=lead_time_hours)
        alerts: List[HazardAlert] = []

        cat_to_severity = {
            AlertCategory.GREEN: AlertSeverity.GREEN,
            AlertCategory.YELLOW: AlertSeverity.YELLOW,
            AlertCategory.ORANGE: AlertSeverity.ORANGE,
            AlertCategory.RED: AlertSeverity.RED,
        }
        event_to_hazard = {
            ExtremeEventType.HEAVY_RAINFALL: HazardType.HEAVY_RAIN,
            ExtremeEventType.HEAT_WAVE: HazardType.HEATWAVE,
            ExtremeEventType.HIGH_WIND: HazardType.GALE_WIND,
        }

        for g in guidances:
            if g.recommended_alert_category in (AlertCategory.ORANGE, AlertCategory.RED):
                ht = event_to_hazard.get(g.event_type, HazardType.HEAVY_RAIN)
                sev = cat_to_severity[g.recommended_alert_category]

                alerts.append(
                    HazardAlert(
                        id=g.event_id,
                        hazard_type=ht,
                        severity=sev,
                        title=g.advisory_headline,
                        description=g.detailed_guidance,
                        location_name=g.location_name,
                        state=g.affected_region,
                        lat=g.latitude,
                        lon=g.longitude,
                        valid_from=g.expected_start_time,
                        valid_to=g.expected_end_time,
                        exceedance_probability=g.derived_risk_indicator.probability_score,
                        recommended_action="; ".join(g.recommended_actions[:2]),
                    )
                )

        return alerts

    # -----------------------------------------------------------------
    # Private Diagnostic & Classification Helpers
    # -----------------------------------------------------------------

    def _classify_event(
        self,
        event_type: ExtremeEventType,
        val: float,
        thresholds: ThresholdLevelConfig,
    ) -> Tuple[AlertCategory, SeverityLevel, float]:
        """Classifies prediction value against threshold boundaries."""
        if event_type == ExtremeEventType.COLD_WAVE:
            # Lower temperature triggers higher severity
            if val <= thresholds.red_threshold:
                return AlertCategory.RED, SeverityLevel.EXTREME, thresholds.red_threshold
            elif val <= thresholds.orange_threshold:
                return AlertCategory.ORANGE, SeverityLevel.SEVERE, thresholds.orange_threshold
            elif val <= thresholds.yellow_threshold:
                return AlertCategory.YELLOW, SeverityLevel.MODERATE, thresholds.yellow_threshold
            return AlertCategory.GREEN, SeverityLevel.NONE, thresholds.yellow_threshold
        else:
            # Higher value triggers higher severity (Rainfall, Heatwave, Wind)
            if val >= thresholds.red_threshold:
                return AlertCategory.RED, SeverityLevel.EXTREME, thresholds.red_threshold
            elif val >= thresholds.orange_threshold:
                return AlertCategory.ORANGE, SeverityLevel.SEVERE, thresholds.orange_threshold
            elif val >= thresholds.yellow_threshold:
                return AlertCategory.YELLOW, SeverityLevel.MODERATE, thresholds.yellow_threshold
            return AlertCategory.GREEN, SeverityLevel.NONE, thresholds.yellow_threshold

    def _compute_risk_indicator(
        self,
        event_type: ExtremeEventType,
        forecast_value: float,
        threshold_config: ThresholdLevelConfig,
        model_forecasts: Dict[str, float],
        model_weights: Optional[Dict[str, float]],
        active_threshold: float,
        severity_level: SeverityLevel,
    ) -> DerivedRiskIndicator:
        """
        Calculates multi-model exceedance probability and composite risk index.
        Explicitly distinguishes derived risk indicator from physical forecast value.
        """
        models = list(model_forecasts.keys())
        if not models:
            return DerivedRiskIndicator(
                probability_score=0.10,
                composite_risk_score=5.0,
                risk_level="Low",
            )

        # Count exceedances of active alert threshold
        hits = 0
        total_w = 0.0
        weighted_hits = 0.0

        for m, v in model_forecasts.items():
            w = model_weights.get(m, 1.0 / len(models)) if model_weights else (1.0 / len(models))
            total_w += w
            is_hit = (v <= active_threshold) if event_type == ExtremeEventType.COLD_WAVE else (v >= active_threshold)
            if is_hit:
                hits += 1
                weighted_hits += w

        prob_score = round(weighted_hits / total_w if total_w > 0 else (hits / len(models)), 2)
        prob_score = max(0.02, min(0.98, prob_score))

        # Composite risk calculation
        sev_multiplier = {
            SeverityLevel.NONE: 0.1,
            SeverityLevel.MINOR: 0.3,
            SeverityLevel.MODERATE: 0.55,
            SeverityLevel.SEVERE: 0.80,
            SeverityLevel.EXTREME: 0.95,
        }[severity_level]

        # Magnitude ratio relative to orange threshold
        norm_ref = max(1.0, threshold_config.orange_threshold)
        mag_ratio = max(0.1, min(1.5, forecast_value / norm_ref))

        composite_score = round(min(100.0, (prob_score * 45.0 + sev_multiplier * 40.0 + mag_ratio * 15.0)), 1)

        if composite_score >= 75.0:
            risk_label = "Critical"
        elif composite_score >= 50.0:
            risk_label = "High"
        elif composite_score >= 25.0:
            risk_label = "Moderate"
        else:
            risk_label = "Low"

        return DerivedRiskIndicator(
            probability_score=prob_score,
            composite_risk_score=composite_score,
            risk_level=risk_label,
            disclaimer="Probabilistic advisory indicator representing multi-model consensus; not a guaranteed deterministic outcome.",
        )

    def _compute_confidence(self, model_values: List[float], blended_value: float) -> float:
        """Computes multi-model agreement confidence score [0.0, 1.0]."""
        if len(model_values) <= 1:
            return 0.85

        variance = sum((v - blended_value) ** 2 for v in model_values) / len(model_values)
        spread = math.sqrt(variance)
        rel_dispersion = spread / (abs(blended_value) + 1.0)

        # Exponential decay of confidence with increasing inter-model spread
        conf = math.exp(-rel_dispersion * 3.5)
        return max(0.15, min(0.98, conf))

    def _generate_advisory_text(
        self,
        event_type: ExtremeEventType,
        severity: SeverityLevel,
        category: AlertCategory,
        location: str,
        region: str,
        forecast_value: float,
        unit: str,
        risk_indicator: DerivedRiskIndicator,
        lead_time_hours: int,
    ) -> Tuple[str, str, List[str]]:
        """Constructs meteorological guidance narrative and targeted emergency actions."""
        cat_name = category.value.upper()
        prob_pct = int(risk_indicator.probability_score * 100)

        if event_type == ExtremeEventType.HEAVY_RAINFALL:
            headline = f"{cat_name} ALERT: Heavy Rainfall Guidance for {location}"
            detailed = (
                f"Multi-model consensus forecasts 24h cumulative precipitation of {forecast_value} {unit} "
                f"at {lead_time_hours}h lead time. Derived exceedance probability: {prob_pct}% "
                f"(Composite risk score: {risk_indicator.composite_risk_score}/100, {risk_indicator.risk_level} Risk). "
                f"Regional vulnerability for {region} applied."
            )
            actions = [
                "Avoid low-lying areas and unpaved river crossings prone to flash flooding.",
                "Ensure urban storm drainage channels are clear of debris.",
                "Fishermen and small craft advised to remain in port during intense spells.",
            ] if category in (AlertCategory.ORANGE, AlertCategory.RED) else [
                "Monitor local IMD weather bulletins for potential convective intensification."
            ]

        elif event_type == ExtremeEventType.HEAT_WAVE:
            headline = f"{cat_name} ALERT: Heatwave Guidance for {location}"
            detailed = (
                f"Ensemble consensus predicts maximum surface temperature reaching {forecast_value} {unit} "
                f"at {lead_time_hours}h lead time. Derived heatwave probability: {prob_pct}% "
                f"({risk_indicator.risk_level} thermal risk). Sensitive population caution required."
            )
            actions = [
                "Avoid direct sun exposure between 12:00 PM and 4:00 PM.",
                "Maintain hydration and administer oral rehydration solutions to vulnerable individuals.",
                "Provide shaded rest areas and drinking water at outdoor industrial and agricultural work sites.",
            ] if category in (AlertCategory.ORANGE, AlertCategory.RED) else [
                "Stay hydrated and avoid strenuous outdoor exercise during peak heat hours."
            ]

        elif event_type == ExtremeEventType.HIGH_WIND:
            headline = f"{cat_name} ALERT: High Wind & Squall Guidance for {location}"
            detailed = (
                f"Multi-model predictions indicate sustained surface winds up to {forecast_value} {unit} "
                f"at {lead_time_hours}h lead time. Gale probability: {prob_pct}% ({risk_indicator.risk_level} Risk)."
            )
            actions = [
                "Secure temporary structures, loose metal sheets, and construction scaffolding.",
                "Total suspension of coastal small craft and marine operations advised.",
                "Beware of falling branches and live overhead electrical wires.",
            ] if category in (AlertCategory.ORANGE, AlertCategory.RED) else [
                "Secure lightweight garden furniture and outdoor objects."
            ]

        else:
            headline = f"{cat_name} NOTICE: Weather Guidance for {location}"
            detailed = f"Forecast prediction of {forecast_value} {unit} evaluated. Risk level: {risk_indicator.risk_level}."
            actions = ["Maintain standard situational awareness."]

        return headline, detailed, actions
