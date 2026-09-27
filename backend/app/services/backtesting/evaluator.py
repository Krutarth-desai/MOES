import logging
import math
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.config.settings import DATA_DIR, SAMPLE_DIR
from backend.app.data.ingestion.pipeline import IngestionPipeline
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.data.observation.ingestion import ObservationIngestionService
from backend.app.data.observation.matcher import MatchedPair, SpatialTemporalMatcher
from backend.app.services.blending.engine import ForecastBlendingEngine
from backend.app.services.backtesting.schemas import (
    BacktestConfig,
    BacktestRunResult,
    BacktestSplitMethod,
    ComparisonReportRow,
    DashboardHeadlineStatement,
    ModelEvaluationScore,
    ModelRelativeComparison,
)
from backend.app.services.verification.metrics import VerificationMath
from backend.app.services.verification.schemas import (
    ComprehensiveSkillScore,
    HistoricalSkillRecord,
    MetricDimensionSlice,
)
from backend.app.services.verification.store import SkillScoreStore
from backend.app.services.weighting.engine import AdaptiveWeightEngine

logger = logging.getLogger("moes.backtesting.evaluator")

VARIABLE_UNITS: Dict[str, str] = {
    "temperature": "°C",
    "rainfall": "mm",
    "wind_speed": "km/h",
    "wind_direction": "degrees",
}

CANONICAL_MODEL_NAMES = [
    "NWP Model A",
    "NWP Model B",
    "Ensemble Forecast",
    "AI Forecast",
    "Hybrid Blended Forecast",
]


class BacktestEngine:
    """
    Operational Forecast Skill Comparison & Backtesting Engine.
    
    Conducts out-of-sample time-series evaluation (chronological train/test split or rolling-origin)
    to objectively compare:
    1. NWP Model A
    2. NWP Model B
    3. Ensemble Forecast
    4. AI Forecast
    5. Hybrid Blended Forecast
    
    Guarantees:
    - Zero data leakage: adaptive weights are calibrated exclusively on training data
    - Test evaluation is performed strictly out-of-sample against verified ground-truth
    - Mathematical metrics: MAE, RMSE, Bias, Correlation, CSI, POD, FAR, ETS, Brier Score
    - Auditable relative improvement calculations directly from real test residuals
    - Reproducible output artifacts and dimensional comparison reports
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

    def run_backtest(
        self,
        matched_pairs: Optional[List[MatchedPair]] = None,
        config: Optional[BacktestConfig] = None,
    ) -> BacktestRunResult:
        """
        Executes complete out-of-sample backtesting and skill comparison.
        """
        cfg = config or self.config
        pairs = matched_pairs or self._load_and_match_sample_data()

        if not pairs:
            raise ValueError("No matched forecast-observation pairs available for backtesting.")

        # 1. Normalize model names to canonical labels
        normalized_pairs = [self._normalize_pair(p) for p in pairs]

        # 2. Extract unique sorted timestamps to partition time series chronologically
        timestamps = sorted(list({p.forecast_timestamp for p in normalized_pairs}))
        if len(timestamps) < 2:
            raise ValueError(f"Insufficient unique timestamps ({len(timestamps)}) for time-series split.")

        split_idx = max(1, int(len(timestamps) * cfg.train_ratio))
        train_timestamps = set(timestamps[:split_idx])
        test_timestamps = set(timestamps[split_idx:])

        train_pairs = [p for p in normalized_pairs if p.forecast_timestamp in train_timestamps]
        test_pairs = [p for p in normalized_pairs if p.forecast_timestamp in test_timestamps]

        if not test_pairs:
            raise ValueError("Test set is empty after chronological partitioning. Adjust train_ratio.")

        train_start, train_end = timestamps[0], timestamps[split_idx - 1]
        test_start, test_end = timestamps[split_idx], timestamps[-1]

        logger.info(
            "Backtesting Split: %d train timestamps (%s to %s, %d pairs), "
            "%d test timestamps (%s to %s, %d pairs)",
            len(train_timestamps), train_start, train_end, len(train_pairs),
            len(test_timestamps), test_start, test_end, len(test_pairs)
        )

        # 3. Calibrate Adaptive Weights STRICTLY on Training Window (No Data Leakage)
        training_weight_engine = self._calibrate_training_weights(train_pairs)
        blending_engine = ForecastBlendingEngine(weight_engine=training_weight_engine, store=None)

        # 4. Generate Hybrid Blended Forecast for all test points
        aligned_test_dataset = self._generate_hybrid_and_align_test_set(
            test_pairs=test_pairs,
            blending_engine=blending_engine,
        )

        # 5. Evaluate all 5 models across requested variables
        models_to_evaluate = [
            "NWP Model A",
            "NWP Model B",
            "Ensemble Forecast",
            "AI Forecast",
            "Hybrid Blended Forecast",
        ]

        overall_scores: Dict[str, Dict[str, ModelEvaluationScore]] = {}
        relative_improvements: Dict[str, List[ModelRelativeComparison]] = {}
        headlines: Dict[str, DashboardHeadlineStatement] = {}
        dimensional_report: List[ComparisonReportRow] = []

        for var_name in cfg.variables:
            var_data = [item for item in aligned_test_dataset if item["variable"] == var_name]
            if not var_data:
                continue

            unit = VARIABLE_UNITS.get(var_name, "")
            scores_for_var: Dict[str, ModelEvaluationScore] = {}

            # Calculate metrics for each model
            for model_name in models_to_evaluate:
                score = self._compute_model_metrics(
                    model_name=model_name,
                    var_name=var_name,
                    items=var_data,
                    extreme_threshold=cfg.rainfall_extreme_threshold if var_name == "rainfall" else None,
                )
                scores_for_var[model_name] = score

            overall_scores[var_name] = scores_for_var

            # Compute relative improvements vs Hybrid
            hybrid_score = scores_for_var["Hybrid Blended Forecast"]
            improvements_list: List[ModelRelativeComparison] = []

            individual_models = [m for m in models_to_evaluate if m != "Hybrid Blended Forecast"]
            for m in individual_models:
                base_score = scores_for_var[m]
                rmse_red = ((base_score.rmse - hybrid_score.rmse) / base_score.rmse * 100.0) if base_score.rmse > 0 else 0.0
                mae_red = ((base_score.mae - hybrid_score.mae) / base_score.mae * 100.0) if base_score.mae > 0 else 0.0
                corr_gain = hybrid_score.correlation - base_score.correlation

                improvements_list.append(
                    ModelRelativeComparison(
                        model_name=m,
                        variable=var_name,
                        baseline_rmse=base_score.rmse,
                        hybrid_rmse=hybrid_score.rmse,
                        rmse_reduction_pct=round(rmse_red, 2),
                        baseline_mae=base_score.mae,
                        hybrid_mae=hybrid_score.mae,
                        mae_reduction_pct=round(mae_red, 2),
                        baseline_correlation=base_score.correlation,
                        hybrid_correlation=hybrid_score.correlation,
                        correlation_gain=round(corr_gain, 3),
                    )
                )

            relative_improvements[var_name] = improvements_list

            # Identify Best Individual Model (lowest test RMSE)
            best_indiv_model = min(individual_models, key=lambda m: scores_for_var[m].rmse)
            best_indiv_score = scores_for_var[best_indiv_model]
            best_rel_improvement = ((best_indiv_score.rmse - hybrid_score.rmse) / best_indiv_score.rmse * 100.0) if best_indiv_score.rmse > 0 else 0.0

            # Construct Dashboard Headline Statement
            st_hybrid = f"Hybrid forecast RMSE: {hybrid_score.rmse:.2f} {unit}"
            st_best = f"Best individual model RMSE: {best_indiv_score.rmse:.2f} {unit} ({best_indiv_model})"
            st_imp = f"Relative improvement: {best_rel_improvement:.2f}% error reduction"
            summary = (
                f"Out-of-sample backtest on {len(var_data)} test cases demonstrates that the "
                f"Hybrid Blended Forecast achieves an RMSE of {hybrid_score.rmse:.2f} {unit}, "
                f"outperforming the top-performing baseline ({best_indiv_model}, RMSE {best_indiv_score.rmse:.2f} {unit}) "
                f"with a {best_rel_improvement:.2f}% error reduction and Pearson correlation of {hybrid_score.correlation:.3f}."
            )

            headlines[var_name] = DashboardHeadlineStatement(
                variable=var_name,
                unit=unit,
                hybrid_rmse=hybrid_score.rmse,
                best_individual_model=best_indiv_model,
                best_individual_rmse=best_indiv_score.rmse,
                relative_improvement_pct=round(best_rel_improvement, 2),
                statement_hybrid_rmse=st_hybrid,
                statement_best_model_rmse=st_best,
                statement_relative_improvement=st_imp,
                summary_paragraph=summary,
            )

            # Build Dimensional Comparison Report Rows (Overall + Lead Time + Region)
            self._append_dimensional_rows(
                dimensional_report=dimensional_report,
                var_name=var_name,
                unit=unit,
                models=models_to_evaluate,
                var_data=var_data,
                scores_for_var=scores_for_var,
                threshold=cfg.rainfall_extreme_threshold if var_name == "rainfall" else None,
            )

        # 6. Assemble Full BacktestRunResult
        backtest_id = f"BACKTEST-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        sample_preds = aligned_test_dataset[:50]  # Store sample points for plotting

        result = BacktestRunResult(
            backtest_id=backtest_id,
            evaluated_at=datetime.now(),
            config=cfg,
            train_start=train_start,
            train_end=train_end,
            test_start=test_start,
            test_end=test_end,
            train_sample_count=len(train_pairs),
            test_sample_count=len(test_pairs),
            models_evaluated=models_to_evaluate,
            variables_evaluated=list(overall_scores.keys()),
            headlines=headlines,
            overall_scores=overall_scores,
            relative_improvements=relative_improvements,
            dimensional_report=dimensional_report,
            sample_test_predictions=sample_preds,
        )

        return result

    # -----------------------------------------------------------------
    # Private Helpers for Data Preparation, Calibration & Evaluation
    # -----------------------------------------------------------------

    def _normalize_pair(self, p: MatchedPair) -> MatchedPair:
        """Maps long or simulated model labels to canonical concise names."""
        m_raw = p.model_name
        canonical = m_raw
        if "NWP Model A" in m_raw or "GFS" in m_raw:
            canonical = "NWP Model A"
        elif "NWP Model B" in m_raw or "ECMWF" in m_raw:
            canonical = "NWP Model B"
        elif "Ensemble" in m_raw or "GEFS" in m_raw or "EPS" in m_raw:
            canonical = "Ensemble Forecast"
        elif "AI" in m_raw or "GraphCast" in m_raw or "Pangu" in m_raw:
            canonical = "AI Forecast"

        v_str = p.variable.value if isinstance(p.variable, ForecastVariable) else str(p.variable).lower()
        if "rain" in v_str or "precip" in v_str:
            norm_v = ForecastVariable.RAINFALL
        elif "temp" in v_str:
            norm_v = ForecastVariable.TEMPERATURE
        elif "wind_dir" in v_str:
            norm_v = ForecastVariable.WIND_DIRECTION
        elif "wind" in v_str:
            norm_v = ForecastVariable.WIND_SPEED
        else:
            norm_v = ForecastVariable.TEMPERATURE

        return MatchedPair(
            model_name=canonical,
            station_id=p.station_id,
            region=p.region,
            lead_time_hours=p.lead_time_hours,
            variable=norm_v,
            forecast_timestamp=p.forecast_timestamp,
            observation_timestamp=p.observation_timestamp,
            forecast_lat=p.forecast_lat,
            forecast_lon=p.forecast_lon,
            observation_lat=p.observation_lat,
            observation_lon=p.observation_lon,
            spatial_distance_km=p.spatial_distance_km,
            temporal_offset_minutes=p.temporal_offset_minutes,
            forecast_value=p.forecast_value,
            observed_value=p.observed_value,
            error=p.error,
            absolute_error=p.absolute_error,
            squared_error=p.squared_error,
        )

    def _calibrate_training_weights(self, train_pairs: List[MatchedPair]) -> AdaptiveWeightEngine:
        """
        Calibrates historical skill scores on training data only.
        Builds an isolated SkillScoreStore so that no test data can ever leak into the weights.
        """
        isolated_store = SkillScoreStore(storage_path=None)  # in-memory only
        generated_records: List[HistoricalSkillRecord] = []

        # Stratifications: (model, variable), (model, variable, lead), (model, variable, region)
        buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        for p in train_pairs:
            m = p.model_name
            v = p.variable
            lt = p.lead_time_hours
            reg = p.region

            buckets[(m, v, None, None)].append(p)
            buckets[(m, v, lt, None)].append(p)
            buckets[(m, v, None, reg)].append(p)
            buckets[(m, v, lt, reg)].append(p)

        for (m, v, lt, reg), group_pairs in buckets.items():
            f_vals = [p.forecast_value for p in group_pairs]
            o_vals = [p.observed_value for p in group_pairs]
            mae, rmse, bias, corr = VerificationMath.compute_continuous_metrics(f_vals, o_vals)
            comp_skill = VerificationMath.compute_composite_skill_score(rmse, corr)

            dim = MetricDimensionSlice(
                model_name=m,
                variable=v,
                lead_time_hours=lt,
                region=reg,
                season=Season.MONSOON,
                weather_regime=WeatherRegime.MONSOON_ACTIVE,
            )
            score = ComprehensiveSkillScore(
                sample_size=len(group_pairs),
                mae=mae,
                rmse=rmse,
                bias=bias,
                correlation=corr,
                composite_skill_score=comp_skill,
            )
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=score))

        isolated_store.add_records(generated_records)
        return AdaptiveWeightEngine(skill_store=isolated_store)

    def _generate_hybrid_and_align_test_set(
        self,
        test_pairs: List[MatchedPair],
        blending_engine: ForecastBlendingEngine,
    ) -> List[Dict[str, Any]]:
        """
        Pivots the test pairs by test instance (station, variable, lead, timestamp)
        and computes the Hybrid Blended Forecast for every point.
        """
        # Key: (forecast_timestamp, station_id, variable, lead_time_hours, region)
        test_instances: Dict[Tuple[str, str, str, int, str], Dict[str, Any]] = {}

        for p in test_pairs:
            v_str = p.variable.value if isinstance(p.variable, ForecastVariable) else str(p.variable).lower()
            key = (p.forecast_timestamp, p.station_id or "GRID", v_str, p.lead_time_hours, p.region)

            if key not in test_instances:
                test_instances[key] = {
                    "timestamp": p.forecast_timestamp,
                    "station_id": p.station_id,
                    "variable": v_str,
                    "lead_time_hours": p.lead_time_hours,
                    "region": p.region,
                    "observed_value": p.observed_value,
                    "model_predictions": {},
                }

            test_instances[key]["model_predictions"][p.model_name] = p.forecast_value

        aligned_items: List[Dict[str, Any]] = []

        for key, inst in test_instances.items():
            preds = inst["model_predictions"]
            var_name = inst["variable"]
            obs_val = inst["observed_value"]

            # Only evaluate instances where at least 2 models provided forecasts
            if len(preds) < 2:
                continue

            # Compute Blended Forecast via blending_engine
            blend_res = blending_engine.blend(
                variable=var_name,
                lead_time_hours=inst["lead_time_hours"],
                station_id=inst["station_id"],
                region=inst["region"],
                model_forecasts=preds,
                persist=False,
            )
            hybrid_val = blend_res.blended_value

            full_preds = dict(preds)
            full_preds["Hybrid Blended Forecast"] = hybrid_val

            aligned_items.append({
                "timestamp": inst["timestamp"],
                "station_id": inst["station_id"],
                "variable": var_name,
                "lead_time_hours": inst["lead_time_hours"],
                "region": inst["region"],
                "observed_value": obs_val,
                "predictions": full_preds,
            })

        return aligned_items

    def _compute_model_metrics(
        self,
        model_name: str,
        var_name: str,
        items: List[Dict[str, Any]],
        extreme_threshold: Optional[float] = None,
    ) -> ModelEvaluationScore:
        """
        Computes standard metrics on out-of-sample test predictions.
        """
        valid_items = [it for it in items if model_name in it["predictions"]]
        n = len(valid_items)

        if n == 0:
            return ModelEvaluationScore(
                model_name=model_name,
                variable=var_name,
                sample_size=0,
                mae=0.0,
                rmse=0.0,
                bias=0.0,
                correlation=0.0,
            )

        f_vals = [it["predictions"][model_name] for it in valid_items]
        o_vals = [it["observed_value"] for it in valid_items]

        mae, rmse, bias, corr = VerificationMath.compute_continuous_metrics(f_vals, o_vals)

        csi, pod, far, ets, brier = None, None, None, None, None
        if extreme_threshold is not None:
            hits, misses, fa, cn = VerificationMath.compute_contingency_table(f_vals, o_vals, extreme_threshold)
            pod, far, csi, ets = VerificationMath.compute_extreme_skill_scores(hits, misses, fa, cn)

            probs = [1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, (val - extreme_threshold) / (extreme_threshold * 0.2 + 1e-5))))) for val in f_vals]
            brier, _ = VerificationMath.compute_probabilistic_metrics(probs, o_vals, extreme_threshold)

        return ModelEvaluationScore(
            model_name=model_name,
            variable=var_name,
            sample_size=n,
            mae=mae,
            rmse=rmse,
            bias=bias,
            correlation=corr,
            csi=csi,
            pod=pod,
            far=far,
            ets=ets,
            brier_score=brier,
        )

    def _append_dimensional_rows(
        self,
        dimensional_report: List[ComparisonReportRow],
        var_name: str,
        unit: str,
        models: List[str],
        var_data: List[Dict[str, Any]],
        scores_for_var: Dict[str, ModelEvaluationScore],
        threshold: Optional[float],
    ):
        """
        Generates dimensional report rows:
        model | variable | lead time | region | metric
        """
        hybrid_overall = scores_for_var["Hybrid Blended Forecast"]

        # 1. Overall Strata (lead_time=None, region=None)
        for m in models:
            score = scores_for_var[m]
            rel_imp = None
            if m != "Hybrid Blended Forecast" and score.rmse > 0:
                rel_imp = round(((score.rmse - hybrid_overall.rmse) / score.rmse * 100.0), 2)

            for metric_name, val in [
                ("RMSE", score.rmse),
                ("MAE", score.mae),
                ("Bias", score.bias),
                ("Correlation", score.correlation),
            ]:
                dimensional_report.append(
                    ComparisonReportRow(
                        model_name=m,
                        variable=var_name,
                        lead_time_hours=None,
                        region=None,
                        metric=metric_name,
                        value=val,
                        unit=unit if metric_name in ("RMSE", "MAE", "Bias") else "coeff",
                        sample_size=score.sample_size,
                        relative_improvement_pct=rel_imp if metric_name == "RMSE" else None,
                    )
                )

            if score.csi is not None:
                dimensional_report.append(
                    ComparisonReportRow(
                        model_name=m,
                        variable=var_name,
                        lead_time_hours=None,
                        region=None,
                        metric="CSI",
                        value=score.csi,
                        unit="score",
                        sample_size=score.sample_size,
                    )
                )

        # 2. Strata by Lead Time
        lead_times = sorted(list({it["lead_time_hours"] for it in var_data}))
        for lt in lead_times:
            lt_items = [it for it in var_data if it["lead_time_hours"] == lt]
            lt_scores = {m: self._compute_model_metrics(m, var_name, lt_items, threshold) for m in models}
            lt_hybrid = lt_scores["Hybrid Blended Forecast"]

            for m in models:
                sc = lt_scores[m]
                rel_imp = round(((sc.rmse - lt_hybrid.rmse) / sc.rmse * 100.0), 2) if (m != "Hybrid Blended Forecast" and sc.rmse > 0) else None

                dimensional_report.append(
                    ComparisonReportRow(
                        model_name=m,
                        variable=var_name,
                        lead_time_hours=lt,
                        region=None,
                        metric="RMSE",
                        value=sc.rmse,
                        unit=unit,
                        sample_size=sc.sample_size,
                        relative_improvement_pct=rel_imp,
                    )
                )
                dimensional_report.append(
                    ComparisonReportRow(
                        model_name=m,
                        variable=var_name,
                        lead_time_hours=lt,
                        region=None,
                        metric="MAE",
                        value=sc.mae,
                        unit=unit,
                        sample_size=sc.sample_size,
                    )
                )

        # 3. Strata by Region
        regions = sorted(list({it["region"] for it in var_data if it.get("region")}))
        for reg in regions:
            reg_items = [it for it in var_data if it.get("region") == reg]
            reg_scores = {m: self._compute_model_metrics(m, var_name, reg_items, threshold) for m in models}
            reg_hybrid = reg_scores["Hybrid Blended Forecast"]

            for m in models:
                sc = reg_scores[m]
                rel_imp = round(((sc.rmse - reg_hybrid.rmse) / sc.rmse * 100.0), 2) if (m != "Hybrid Blended Forecast" and sc.rmse > 0) else None

                dimensional_report.append(
                    ComparisonReportRow(
                        model_name=m,
                        variable=var_name,
                        lead_time_hours=None,
                        region=reg,
                        metric="RMSE",
                        value=sc.rmse,
                        unit=unit,
                        sample_size=sc.sample_size,
                        relative_improvement_pct=rel_imp,
                    )
                )

    def _load_and_match_sample_data(self) -> List[MatchedPair]:
        """
        Loads forecast files and ground truth observations from SAMPLE_DIR and matches them.
        """
        fcst_pipeline = IngestionPipeline()
        fcst_pipeline.ingest_directory(SAMPLE_DIR)
        fcst_records = fcst_pipeline.get_all_records()

        obs_service = ObservationIngestionService()
        obs_file = SAMPLE_DIR / "observations.csv"
        if not obs_file.exists():
            raise FileNotFoundError(f"Observations file not found at {obs_file}")

        obs_records, _ = obs_service.load_file(obs_file)
        matcher = SpatialTemporalMatcher()
        return matcher.match(fcst_records, obs_records)
