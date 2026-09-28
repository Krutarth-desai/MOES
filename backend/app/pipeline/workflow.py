import logging
import math
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config.settings import DATA_DIR
from backend.app.data.ingestion.schema import (
    ForecastSourceType,
    ForecastVariable,
    Season,
    StandardForecastRecord,
    WeatherRegime,
)
from backend.app.data.observation.matcher import MatchedPair, SpatialTemporalMatcher
from backend.app.data.observation.schema import ObservationRecord
from backend.app.data.stations import REFERENCE_STATIONS, get_all_stations, get_station_by_id
from backend.app.pipeline.interfaces import (
    DashboardNotifierInterface,
    ForecastSourceInterface,
    ObservationSourceInterface,
)
from backend.app.pipeline.schemas import (
    PipelineConfig,
    PipelineExecutionReport,
    PipelineTelemetry,
    StepResult,
)
from backend.app.pipeline.sources import (
    HybridForecastSource,
    HybridObservationSource,
    LocalJsonDashboardNotifier,
)
from backend.app.pipeline.store import PipelineRunStore
from backend.app.services.blending.engine import ForecastBlendingEngine
from backend.app.services.blending.schemas import BlendedForecastResult
from backend.app.services.blending.store import BlendedForecastStore
from backend.app.services.explainability.engine import ForecastExplainabilityEngine
from backend.app.services.extremes.engine import ExtremeWeatherGuidanceEngine
from backend.app.services.extremes.schemas import ExtremeEventType, ExtremeWeatherGuidance, SeverityLevel
from backend.app.services.regime.base import WeatherRegimeClassifier
from backend.app.services.regime.rule_based import RuleBasedRegimeClassifier
from backend.app.services.regime.schemas import WeatherContext
from backend.app.services.regime.service import RegimeClassificationService
from backend.app.services.verification.service import ForecastMetricsService
from backend.app.services.verification.store import SkillScoreStore
from backend.app.services.weighting.engine import AdaptiveWeightEngine

logger = logging.getLogger("moes.pipeline.workflow")

PHYSICAL_BOUNDS = {
    "temperature": (-60.0, 65.0),
    "rainfall": (0.0, 1500.0),
    "wind_speed": (0.0, 400.0),
    "wind_direction": (0.0, 360.0),
}


class AutomatedForecastPipeline:
    """
    Automated Multi-Model Meteorological Forecast Processing Workflow.
    
    Executes the complete 12-step operational sequence:
    1. Ingest forecast data
    2. Ingest observations
    3. Validate data
    4. Preprocess data
    5. Determine weather regime
    6. Retrieve historical model skill
    7. Calculate adaptive weights
    8. Generate blended forecast
    9. Calculate uncertainty/confidence
    10. Detect extreme events
    11. Store results
    12. Update dashboard
    
    Engineered with pluggable interfaces so operational APIs (IMD GTS, NOAA GFS,
    ECMWF, etc.) can seamlessly replace prototype data feeds.
    """

    def __init__(
        self,
        forecast_source: Optional[ForecastSourceInterface] = None,
        observation_source: Optional[ObservationSourceInterface] = None,
        dashboard_notifier: Optional[DashboardNotifierInterface] = None,
        weight_engine: Optional[AdaptiveWeightEngine] = None,
        blending_engine: Optional[ForecastBlendingEngine] = None,
        regime_classifier: Optional[WeatherRegimeClassifier] = None,
        guidance_engine: Optional[ExtremeWeatherGuidanceEngine] = None,
        skill_store: Optional[SkillScoreStore] = None,
        blended_store: Optional[BlendedForecastStore] = None,
        run_store: Optional[PipelineRunStore] = None,
    ):
        # 1. Modular data providers with strict provenance tracking
        from backend.app.data.sources.factory import ForecastSourceFactory, ObservationSourceFactory
        self.forecast_source = forecast_source or ForecastSourceFactory.create()
        self.observation_source = observation_source or ObservationSourceFactory.create()
        self.dashboard_notifier = dashboard_notifier or LocalJsonDashboardNotifier()

        # 2. Core analytical engines
        self.skill_store = skill_store or SkillScoreStore()
        self.weight_engine = weight_engine or AdaptiveWeightEngine(skill_store=self.skill_store)
        self.blended_store = blended_store or BlendedForecastStore()
        self.explainability_engine = ForecastExplainabilityEngine(skill_store=self.skill_store)
        self.blending_engine = blending_engine or ForecastBlendingEngine(
            weight_engine=self.weight_engine,
            store=self.blended_store,
            explainability_engine=self.explainability_engine,
        )
        self.regime_classifier = regime_classifier or RuleBasedRegimeClassifier()
        self.regime_service = RegimeClassificationService(classifier=self.regime_classifier)
        self.guidance_engine = guidance_engine or ExtremeWeatherGuidanceEngine()
        self.metrics_service = ForecastMetricsService(store=self.skill_store)
        self.run_store = run_store or PipelineRunStore()

    def run(self, config: Optional[PipelineConfig] = None) -> PipelineExecutionReport:
        """
        Executes the 12-step automated forecast pipeline.
        Tracks all telemetry, per-step timing, data sources, records processed,
        errors, models used, and generated forecasts.
        """
        cfg = config or PipelineConfig()
        exec_id = f"PIPE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        start_wall_time = time.perf_counter()
        start_datetime = datetime.now()

        logger.info("=" * 80)
        logger.info("STARTING AUTOMATED FORECAST PROCESSING WORKFLOW [%s]", exec_id)
        logger.info("=" * 80)

        step_results: List[StepResult] = []
        all_errors: List[str] = []
        all_sources: List[str] = []
        models_used: List[str] = list(self.forecast_source.models_provided)
        records_processed: Dict[str, int] = {
            "forecast_records": 0,
            "observation_records": 0,
            "validated_records": 0,
            "matched_pairs": 0,
            "total_records": 0,
        }

        # Pipeline Intermediate State Accumulators
        raw_forecast_records: List[StandardForecastRecord] = []
        raw_observation_records: List[ObservationRecord] = []
        validated_forecasts: List[StandardForecastRecord] = []
        validated_observations: List[ObservationRecord] = []
        matched_pairs: List[MatchedPair] = []
        station_regimes: Dict[str, Any] = {}
        blended_results: List[BlendedForecastResult] = []
        extreme_guidance_list: List[ExtremeWeatherGuidance] = []

        # Target stations resolution
        target_station_ids = cfg.stations or list(REFERENCE_STATIONS.keys())
        target_variables = cfg.variables
        target_lead_times = cfg.lead_times

        # =====================================================================
        # STEP 1: Ingest Forecast Data
        # =====================================================================
        step_t0 = time.perf_counter()
        step1_errors: List[str] = []
        try:
            logger.info("[Step 1/12] Ingesting forecast data via %s...", self.forecast_source.source_name)
            raw_forecast_records, f_meta = self.forecast_source.fetch_forecasts(
                station_ids=target_station_ids,
                variables=target_variables,
                lead_times=target_lead_times,
                reference_time=start_datetime,
            )
            all_sources.append(self.forecast_source.source_name)
            records_processed["forecast_records"] = len(raw_forecast_records)
            step_res = StepResult(
                step_number=1,
                step_name="Ingest forecast data",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(raw_forecast_records),
                records_out=len(raw_forecast_records),
                details=f_meta,
            )
            logger.info("  -> Ingested %d forecast records across models: %s", len(raw_forecast_records), models_used)
        except Exception as e:
            msg = f"Step 1 Failed (Forecast Ingestion): {e}"
            logger.exception(msg)
            step1_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=1,
                step_name="Ingest forecast data",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step1_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 2: Ingest Observations
        # =====================================================================
        step_t0 = time.perf_counter()
        step2_errors: List[str] = []
        try:
            logger.info("[Step 2/12] Ingesting observations via %s...", self.observation_source.source_name)
            raw_observation_records, o_meta = self.observation_source.fetch_observations(
                station_ids=target_station_ids,
                reference_time=start_datetime,
            )
            all_sources.append(self.observation_source.source_name)
            records_processed["observation_records"] = len(raw_observation_records)
            step_res = StepResult(
                step_number=2,
                step_name="Ingest observations",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(raw_observation_records),
                records_out=len(raw_observation_records),
                details=o_meta,
            )
            logger.info("  -> Ingested %d observation records", len(raw_observation_records))
        except Exception as e:
            msg = f"Step 2 Failed (Observation Ingestion): {e}"
            logger.exception(msg)
            step2_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=2,
                step_name="Ingest observations",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step2_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 3: Validate Data
        # =====================================================================
        step_t0 = time.perf_counter()
        step3_errors: List[str] = []
        clamped_count = 0
        try:
            logger.info("[Step 3/12] Validating physical bounds and integrity of ingested datasets...")
            # 3a. Validate forecast records
            for rec in raw_forecast_records:
                var_key = rec.forecast_variable.value if hasattr(rec.forecast_variable, "value") else str(rec.forecast_variable)
                bounds = PHYSICAL_BOUNDS.get(var_key)
                val = rec.forecast_value
                if bounds:
                    min_b, max_b = bounds
                    if val < min_b or val > max_b:
                        clamped_val = max(min_b, min(max_b, val))
                        clamped_count += 1
                        rec.forecast_value = clamped_val
                validated_forecasts.append(rec)

            # 3b. Validate observation records
            for obs in raw_observation_records:
                if obs.rainfall is not None and obs.rainfall < 0.0:
                    obs.rainfall = 0.0
                    clamped_count += 1
                if obs.wind_speed is not None and obs.wind_speed < 0.0:
                    obs.wind_speed = 0.0
                    clamped_count += 1
                if obs.wind_direction is not None:
                    obs.wind_direction = obs.wind_direction % 360.0
                validated_observations.append(obs)

            total_valid = len(validated_forecasts) + len(validated_observations)
            records_processed["validated_records"] = total_valid
            records_processed["total_records"] = total_valid

            step_res = StepResult(
                step_number=3,
                step_name="Validate data",
                status="SUCCESS" if clamped_count == 0 else "WARNING",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(raw_forecast_records) + len(raw_observation_records),
                records_out=total_valid,
                details={
                    "valid_forecasts": len(validated_forecasts),
                    "valid_observations": len(validated_observations),
                    "clamped_records": clamped_count,
                },
            )
            logger.info("  -> Validated %d total records (Clamped: %d)", total_valid, clamped_count)
        except Exception as e:
            msg = f"Step 3 Failed (Validation): {e}"
            logger.exception(msg)
            step3_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=3,
                step_name="Validate data",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step3_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 4: Preprocess Data
        # =====================================================================
        step_t0 = time.perf_counter()
        step4_errors: List[str] = []
        try:
            logger.info("[Step 4/12] Preprocessing: spatio-temporal alignment and observation matching...")
            if validated_forecasts and validated_observations:
                from backend.app.data.observation.matcher import MatchingConfig
                matcher = SpatialTemporalMatcher(
                    config=MatchingConfig(max_spatial_distance_km=50.0, max_temporal_offset_minutes=180)
                )
                matched_pairs = matcher.match(
                    forecast_records=validated_forecasts,
                    observation_records=validated_observations,
                )
                records_processed["matched_pairs"] = len(matched_pairs)

            step_res = StepResult(
                step_number=4,
                step_name="Preprocess data",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(validated_forecasts) + len(validated_observations),
                records_out=len(matched_pairs),
                details={
                    "matched_pairs_count": len(matched_pairs),
                    "target_stations": len(target_station_ids),
                    "target_variables": len(target_variables),
                    "target_leads": len(target_lead_times),
                },
            )
            logger.info("  -> Preprocessed datasets: aligned %d matched verification pairs", len(matched_pairs))
        except Exception as e:
            msg = f"Step 4 Failed (Preprocessing): {e}"
            logger.exception(msg)
            step4_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=4,
                step_name="Preprocess data",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step4_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 5: Determine Weather Regime
        # =====================================================================
        step_t0 = time.perf_counter()
        step5_errors: List[str] = []
        try:
            logger.info("[Step 5/12] Diagnosing synoptic weather regimes across target stations...")
            # Group latest observation by station
            latest_obs_by_station: Dict[str, ObservationRecord] = {}
            for obs in validated_observations:
                sid = obs.station_id.upper()
                if sid not in latest_obs_by_station or obs.timestamp > latest_obs_by_station[sid].timestamp:
                    latest_obs_by_station[sid] = obs

            for sid in target_station_ids:
                st = get_station_by_id(sid)
                if not st:
                    continue

                obs = latest_obs_by_station.get(sid.upper())
                ctx = WeatherContext(
                    temperature=obs.temperature if obs and obs.temperature is not None else 30.0,
                    rainfall=obs.rainfall if obs and obs.rainfall is not None else 10.0,
                    wind_speed=obs.wind_speed if obs and obs.wind_speed is not None else 15.0,
                    wind_direction=obs.wind_direction if obs else 220.0,
                    humidity=getattr(obs, "humidity", None) or 75.0,
                    pressure=getattr(obs, "pressure", None) or 1010.0,
                    recent_rainfall=obs.rainfall if obs and obs.rainfall is not None else 5.0,
                    station_id=sid,
                    region=st.region_type,
                    elevation_m=st.elevation_m,
                )
                diag = self.regime_classifier.classify(ctx)
                station_regimes[sid.upper()] = {
                    "regime": diag.regime_name,
                    "confidence": diag.confidence,
                    "description": diag.description,
                    "indicators": diag.supporting_indicators,
                }

            regime_names = list({r["regime"] for r in station_regimes.values()})
            step_res = StepResult(
                step_number=5,
                step_name="Determine weather regime",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(target_station_ids),
                records_out=len(station_regimes),
                details={
                    "stations_diagnosed": len(station_regimes),
                    "active_regimes": regime_names,
                },
            )
            logger.info("  -> Diagnosed weather regimes for %d stations: %s", len(station_regimes), regime_names)
        except Exception as e:
            msg = f"Step 5 Failed (Regime Classification): {e}"
            logger.exception(msg)
            step5_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=5,
                step_name="Determine weather regime",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step5_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 6: Retrieve Historical Model Skill
        # =====================================================================
        step_t0 = time.perf_counter()
        step6_errors: List[str] = []
        try:
            logger.info("[Step 6/12] Retrieving historical model skill scores & updating with latest matched pairs...")
            # If new matched pairs exist, continuously update skill store
            if matched_pairs:
                try:
                    self.metrics_service.evaluate_and_store(matched_pairs)
                    logger.info("  -> Evaluated and stored live skill scores from %d matched pairs", len(matched_pairs))
                except Exception as eval_err:
                    logger.warning("Dynamic skill update failed: %s (continuing with cached skill)", eval_err)

            total_historical_records = self.skill_store.count() if hasattr(self.skill_store, "count") else 0
            step_res = StepResult(
                step_number=6,
                step_name="Retrieve historical model skill",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(matched_pairs),
                records_out=total_historical_records,
                details={
                    "total_historical_skill_records": total_historical_records,
                    "updated_with_live_pairs": len(matched_pairs) > 0,
                },
            )
            logger.info("  -> Retrieved historical skill repository (%d records available)", total_historical_records)
        except Exception as e:
            msg = f"Step 6 Failed (Historical Skill Retrieval): {e}"
            logger.exception(msg)
            step6_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=6,
                step_name="Retrieve historical model skill",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step6_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 7: Calculate Adaptive Weights
        # =====================================================================
        step_t0 = time.perf_counter()
        step7_errors: List[str] = []
        calculated_weight_matrix: Dict[str, Dict[str, float]] = {}
        try:
            logger.info("[Step 7/12] Calculating context-aware adaptive model weights...")
            weight_calcs_count = 0
            for sid in target_station_ids:
                st = get_station_by_id(sid)
                if not st:
                    continue
                reg_info = station_regimes.get(sid.upper(), {})
                active_regime_str = reg_info.get("regime", "Normal")

                for var in target_variables:
                    for lt in target_lead_times:
                        weight_out = self.weight_engine.calculate_weights(
                            models=models_used,
                            variable=var,
                            lead_time_hours=lt,
                            region=st.region_type,
                            season=cfg.season,
                            weather_regime=active_regime_str,
                        )
                        key = f"{sid}_{var}_{lt}"
                        calculated_weight_matrix[key] = weight_out.normalized_weights
                        weight_calcs_count += 1

            step_res = StepResult(
                step_number=7,
                step_name="Calculate adaptive weights",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(target_station_ids) * len(target_variables) * len(target_lead_times),
                records_out=weight_calcs_count,
                details={
                    "total_weight_vectors_calculated": weight_calcs_count,
                    "models_weighted": models_used,
                },
            )
            logger.info("  -> Calculated %d adaptive weight allocations across stations, variables, and lead times", weight_calcs_count)
        except Exception as e:
            msg = f"Step 7 Failed (Weight Calculation): {e}"
            logger.exception(msg)
            step7_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=7,
                step_name="Calculate adaptive weights",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step7_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 8: Generate Blended Forecast
        # =====================================================================
        step_t0 = time.perf_counter()
        step8_errors: List[str] = []
        try:
            logger.info("[Step 8/12] Generating blended multi-model consensus predictions...")
            for sid in target_station_ids:
                st = get_station_by_id(sid)
                if not st:
                    continue
                reg_info = station_regimes.get(sid.upper(), {})
                active_regime_str = reg_info.get("regime", "Normal")

                for var in target_variables:
                    for lt in target_lead_times:
                        weight_key = f"{sid}_{var}_{lt}"
                        explicit_w = calculated_weight_matrix.get(weight_key)

                        blend_res = self.blending_engine.blend(
                            variable=var,
                            lead_time_hours=lt,
                            station_id=sid,
                            latitude=st.lat,
                            longitude=st.lon,
                            timestamp=start_datetime,
                            region=st.region_type,
                            weather_regime=active_regime_str,
                            model_weights=explicit_w,
                            persist=cfg.persist_results and not cfg.dry_run,
                        )
                        blended_results.append(blend_res)

            step_res = StepResult(
                step_number=8,
                step_name="Generate blended forecast",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(calculated_weight_matrix),
                records_out=len(blended_results),
                details={
                    "total_blended_points": len(blended_results),
                    "methods_used": ["linear_combination", "yamartino_vector_averaging"],
                },
            )
            logger.info("  -> Generated %d blended forecast predictions", len(blended_results))
        except Exception as e:
            msg = f"Step 8 Failed (Forecast Blending): {e}"
            logger.exception(msg)
            step8_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=8,
                step_name="Generate blended forecast",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step8_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 9: Calculate Uncertainty / Confidence
        # =====================================================================
        step_t0 = time.perf_counter()
        step9_errors: List[str] = []
        try:
            logger.info("[Step 9/12] Calculating uncertainty bounds and consensus confidence indices...")
            spreads = [b.ensemble_spread for b in blended_results if b.ensemble_spread is not None]
            confidences = [b.confidence_index for b in blended_results if b.confidence_index is not None]

            avg_spread = round(sum(spreads) / max(1, len(spreads)), 2)
            avg_conf = round(sum(confidences) / max(1, len(confidences)), 2)

            step_res = StepResult(
                step_number=9,
                step_name="Calculate uncertainty/confidence",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(blended_results),
                records_out=len(blended_results),
                details={
                    "average_confidence_index": avg_conf,
                    "average_ensemble_spread": avg_spread,
                    "confidence_intervals_derived": "10th and 90th percentiles",
                },
            )
            logger.info("  -> Uncertainty calculated: Avg Confidence: %s%%, Avg Spread: %s", avg_conf, avg_spread)
        except Exception as e:
            msg = f"Step 9 Failed (Uncertainty Quantification): {e}"
            logger.exception(msg)
            step9_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=9,
                step_name="Calculate uncertainty/confidence",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step9_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 10: Detect Extreme Events
        # =====================================================================
        step_t0 = time.perf_counter()
        step10_errors: List[str] = []
        try:
            logger.info("[Step 10/12] Evaluating regional thresholds for extreme weather hazards...")
            for b in blended_results:
                var_clean = b.variable.lower()
                val = b.blended_value

                guidance: Optional[ExtremeWeatherGuidance] = None

                # Rain hazard evaluation
                if "rain" in var_clean and val >= 30.0:
                    guidance = self.guidance_engine.evaluate_point(
                        event_type=ExtremeEventType.HEAVY_RAINFALL,
                        forecast_value=val,
                        location_name=b.station_name or f"Station {b.station_id}",
                        affected_region=b.region or "India",
                        latitude=b.latitude,
                        longitude=b.longitude,
                        lead_time_hours=b.lead_time_hours,
                        station_id=b.station_id,
                        model_forecasts=b.individual_forecasts,
                        model_weights=b.model_weights,
                        reference_time=start_datetime,
                    )
                # Heat hazard evaluation
                elif "temp" in var_clean and val >= 38.0:
                    guidance = self.guidance_engine.evaluate_point(
                        event_type=ExtremeEventType.HEAT_WAVE,
                        forecast_value=val,
                        location_name=b.station_name or f"Station {b.station_id}",
                        affected_region=b.region or "India",
                        latitude=b.latitude,
                        longitude=b.longitude,
                        lead_time_hours=b.lead_time_hours,
                        station_id=b.station_id,
                        model_forecasts=b.individual_forecasts,
                        model_weights=b.model_weights,
                        reference_time=start_datetime,
                    )
                # Wind hazard evaluation
                elif ("speed" in var_clean or "wind" in var_clean) and "dir" not in var_clean and val >= 45.0:
                    guidance = self.guidance_engine.evaluate_point(
                        event_type=ExtremeEventType.HIGH_WIND,
                        forecast_value=val,
                        location_name=b.station_name or f"Station {b.station_id}",
                        affected_region=b.region or "India",
                        latitude=b.latitude,
                        longitude=b.longitude,
                        lead_time_hours=b.lead_time_hours,
                        station_id=b.station_id,
                        model_forecasts=b.individual_forecasts,
                        model_weights=b.model_weights,
                        reference_time=start_datetime,
                    )

                if guidance and guidance.severity_level in (SeverityLevel.MODERATE, SeverityLevel.SEVERE, SeverityLevel.EXTREME):
                    extreme_guidance_list.append(guidance)

            # Deduplicate advisories by (station_id, event_type)
            unique_alerts: Dict[str, ExtremeWeatherGuidance] = {}
            for g in extreme_guidance_list:
                k = f"{g.station_id}_{g.event_type.value}"
                if k not in unique_alerts or g.severity_level.value > unique_alerts[k].severity_level.value:
                    unique_alerts[k] = g

            advisories = list(unique_alerts.values())

            step_res = StepResult(
                step_number=10,
                step_name="Detect extreme events",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(blended_results),
                records_out=len(advisories),
                details={
                    "total_advisories_detected": len(advisories),
                    "alert_categories": [a.recommended_alert_category.value for a in advisories],
                },
            )
            logger.info("  -> Detected %d active extreme weather advisories", len(advisories))
        except Exception as e:
            msg = f"Step 10 Failed (Extreme Weather Detection): {e}"
            logger.exception(msg)
            step10_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=10,
                step_name="Detect extreme events",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step10_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 11: Store Results
        # =====================================================================
        step_t0 = time.perf_counter()
        step11_errors: List[str] = []
        try:
            logger.info("[Step 11/12] Persisting blended forecasts and verification records to storage...")
            stored_count = 0
            if cfg.persist_results and not cfg.dry_run:
                self.blended_store.save()
                stored_count = len(blended_results)

            step_res = StepResult(
                step_number=11,
                step_name="Store results",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(blended_results),
                records_out=stored_count,
                details={
                    "blended_store_path": str(self.blended_store.storage_path),
                    "dry_run": cfg.dry_run,
                    "records_persisted": stored_count,
                },
            )
            logger.info("  -> Persisted %d records to %s", stored_count, self.blended_store.storage_path)
        except Exception as e:
            msg = f"Step 11 Failed (Persistence): {e}"
            logger.exception(msg)
            step11_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=11,
                step_name="Store results",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step11_errors,
            )
        step_results.append(step_res)

        # =====================================================================
        # STEP 12: Update Dashboard
        # =====================================================================
        step_t0 = time.perf_counter()
        step12_errors: List[str] = []
        try:
            logger.info("[Step 12/12] Updating live operational dashboard state and telemetry...")
            end_wall_time = time.perf_counter()
            duration_s = round(end_wall_time - start_wall_time, 3)
            duration_ms = round(duration_s * 1000.0, 2)

            telemetry = PipelineTelemetry(
                execution_id=exec_id,
                start_time=start_datetime,
                end_time=datetime.now(),
                execution_time_seconds=duration_s,
                execution_time_ms=duration_ms,
                data_sources=all_sources,
                records_processed=records_processed,
                errors=all_errors,
                error_count=len(all_errors),
                models_used=models_used,
                generated_forecasts={
                    "total_blended_forecasts": len(blended_results),
                    "stations_processed": len(target_station_ids),
                    "variables": target_variables,
                    "lead_times": target_lead_times,
                    "extreme_events_detected": len(extreme_guidance_list),
                    "active_regimes": list({r["regime"] for r in station_regimes.values()}),
                    "sample_blended_items": [
                        {
                            "station_id": b.station_id,
                            "variable": b.variable,
                            "lead_time": b.lead_time_hours,
                            "blended_value": b.blended_value,
                            "unit": b.unit,
                            "confidence_index": b.confidence_index,
                        }
                        for b in blended_results[:5]
                    ],
                },
            )

            status_str = "SUCCESS" if len(all_errors) == 0 else ("PARTIAL" if len(blended_results) > 0 else "FAILED")
            summary_statement = (
                f"Automated pipeline {exec_id} completed with status {status_str} in {duration_s}s. "
                f"Processed {records_processed['total_records']} records across {len(all_sources)} data sources. "
                f"Generated {len(blended_results)} blended forecasts using {len(models_used)} models. "
                f"Detected {len(extreme_guidance_list)} extreme weather alerts."
            )

            step_res = StepResult(
                step_number=12,
                step_name="Update dashboard",
                status="SUCCESS",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                records_in=len(blended_results),
                records_out=1 if cfg.notify_dashboard else 0,
                details={
                    "dashboard_notified": cfg.notify_dashboard,
                    "notifier": self.dashboard_notifier.notifier_name if cfg.notify_dashboard else "None",
                },
            )
            step_results.append(step_res)

            report = PipelineExecutionReport(
                execution_id=exec_id,
                status=status_str,
                telemetry=telemetry,
                step_results=step_results,
                summary=summary_statement,
                generated_at=datetime.now(),
            )

            if cfg.notify_dashboard:
                self.dashboard_notifier.notify(report)
                self.run_store.save_run(report)

            logger.info("  -> Dashboard updated with live execution telemetry")
        except Exception as e:
            msg = f"Step 12 Failed (Dashboard Notification): {e}"
            logger.exception(msg)
            step12_errors.append(msg)
            all_errors.append(msg)
            step_res = StepResult(
                step_number=12,
                step_name="Update dashboard",
                status="FAILED",
                execution_time_ms=round((time.perf_counter() - step_t0) * 1000.0, 2),
                errors=step12_errors,
            )
            step_results.append(step_res)
            # Fallback report assembly
            report = PipelineExecutionReport(
                execution_id=exec_id,
                status="FAILED",
                telemetry=PipelineTelemetry(
                    execution_id=exec_id,
                    start_time=start_datetime,
                    end_time=datetime.now(),
                    execution_time_seconds=round(time.perf_counter() - start_wall_time, 3),
                    execution_time_ms=round((time.perf_counter() - start_wall_time) * 1000.0, 2),
                    data_sources=all_sources,
                    records_processed=records_processed,
                    errors=all_errors,
                    error_count=len(all_errors),
                    models_used=models_used,
                    generated_forecasts={},
                ),
                step_results=step_results,
                summary=f"Pipeline {exec_id} terminated with errors: {msg}",
            )

        # Structured final logging of all required telemetry fields
        self._log_pipeline_summary(report)

        return report

    def _log_pipeline_summary(self, report: PipelineExecutionReport):
        """Prints a clean, structured operational telemetry log banner."""
        t = report.telemetry
        logger.info("=" * 80)
        logger.info("           AUTOMATED METEOROLOGICAL FORECAST PROCESSING REPORT          ")
        logger.info("=" * 80)
        logger.info(" Pipeline Execution ID: %s", t.execution_id)
        logger.info(" Overall Status       : %s", report.status)
        logger.info(" Execution Time       : %ss (%sms)", t.execution_time_seconds, t.execution_time_ms)
        logger.info(" Data Sources (%d)     : %s", len(t.data_sources), ", ".join(t.data_sources))
        logger.info(" Records Processed    : Total %d (Forecasts: %d, Observations: %d, Validated: %d, Matched: %d)",
                    t.records_processed.get("total_records", 0),
                    t.records_processed.get("forecast_records", 0),
                    t.records_processed.get("observation_records", 0),
                    t.records_processed.get("validated_records", 0),
                    t.records_processed.get("matched_pairs", 0))
        logger.info(" Models Used (%d)      : %s", len(t.models_used), ", ".join(t.models_used))
        logger.info(" Generated Forecasts  : %d blended consensus points",
                    t.generated_forecasts.get("total_blended_forecasts", 0))
        logger.info(" Extreme Hazards      : %d advisories detected",
                    t.generated_forecasts.get("extreme_events_detected", 0))
        logger.info(" Errors Encountered   : %d errors/warnings", t.error_count)
        if t.errors:
            for idx, err in enumerate(t.errors, 1):
                logger.warning("   [Error %d] %s", idx, err)
        logger.info("=" * 80)
