import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.models.regime import RegimeType
from backend.app.services.verification.schemas import (
    ComprehensiveSkillScore,
    HistoricalSkillRecord,
    MetricDimensionSlice,
)
from backend.app.services.verification.store import SkillScoreStore
from backend.app.services.weighting.schemas import (
    AdaptiveWeightOutput,
    FallbackLevel,
    ModelWeightDetail,
)

logger = logging.getLogger("moes.weighting.engine")


class AdaptiveWeightEngine:
    """
    Intelligent Adaptive Model Weight Engine.
    
    Dynamically computes normalized model blending weights based on:
    1. Historical forecast skill (verified continuous & extreme event scores)
    2. Forecast lead time (short-range vs medium-range skill degradation)
    3. Geographic region (orographic & climatological performance)
    4. Season (monsoon, post-monsoon, winter, pre-monsoon)
    5. Weather regime (synoptic & mesoscale atmospheric situation)
    6. Forecast variable (temperature, rainfall, wind speed, wind direction)
    
    Adheres strictly to the Simplex Constraint (sum of weights == 1.0) and
    implements critical operational safeguards:
    - Min/Max weight floors and ceilings
    - Missing skill data handling with neutral Bayesian priors
    - Unseen region & unseen regime graceful fallback hierarchy
    - Insufficient historical sample size shrinkage
    - Zero hardcoded model winners
    """

    def __init__(
        self,
        skill_store: Optional[SkillScoreStore] = None,
        min_weight: float = 0.05,
        max_weight: float = 0.85,
        min_sample_threshold: int = 15,
        shrinkage_prior: float = 0.50,
        power: float = 2.0,
    ):
        self.skill_store = skill_store or SkillScoreStore()
        self.default_min_weight = min_weight
        self.default_max_weight = max_weight
        self.min_sample_threshold = min_sample_threshold
        self.shrinkage_prior = shrinkage_prior
        self.power = power

    def calculate_weights(
        self,
        models: List[str],
        variable: Union[ForecastVariable, str],
        lead_time_hours: int = 24,
        region: Optional[str] = None,
        season: Optional[Union[Season, str]] = None,
        weather_regime: Optional[Union[WeatherRegime, RegimeType, str]] = None,
        historical_performance: Optional[Union[SkillScoreStore, List[HistoricalSkillRecord], Dict[str, Any]]] = None,
        min_weight: Optional[float] = None,
        max_weight: Optional[float] = None,
    ) -> AdaptiveWeightOutput:
        """
        Calculate dynamically adaptive, normalized weights for the provided forecast models.
        """
        if not models:
            raise ValueError("models list cannot be empty.")

        # Resolve safeguards boundaries
        effective_min_w = self.default_min_weight if min_weight is None else min_weight
        effective_max_w = self.default_max_weight if max_weight is None else max_weight

        # Normalize target variable
        norm_var_str, norm_var_enum = self._normalize_variable(variable)

        # Normalize season and weather regime
        norm_season_str, norm_season_enum = self._normalize_season(season)
        norm_regime_str, norm_regime_enum = self._normalize_regime(weather_regime)

        safeguards_applied: List[str] = []

        # Single model trivial case
        if len(models) == 1:
            m = models[0]
            detail = ModelWeightDetail(
                model_name=m,
                weight=1.0,
                raw_score=1.0,
                reliability_score=1.0,
                sample_size=100,
                fallback_level=FallbackLevel.EXACT,
                explanation="Single forecast model provided; received full unitary weight (100%).",
            )
            return AdaptiveWeightOutput(
                variable=norm_var_str,
                region=region,
                lead_time_hours=lead_time_hours,
                season=norm_season_str,
                weather_regime=norm_regime_str,
                weights={m: 1.0},
                normalized_weights={m: 1.0},
                model_details=[detail],
                summary_explanation=f"Single source '{m}' selected with unitary weight 1.0.",
                safeguards_applied=[],
            )

        # 1. Retrieve or calculate reliability scores for each model
        model_evals = []
        for model_name in models:
            eval_info = self._evaluate_model_performance(
                model_name=model_name,
                variable=norm_var_enum,
                lead_time_hours=lead_time_hours,
                region=region,
                season=norm_season_enum,
                weather_regime=norm_regime_enum,
                regime_str=norm_regime_str or (str(weather_regime) if weather_regime else None),
                historical_performance=historical_performance,
            )
            model_evals.append(eval_info)

            # Check if safeguards triggered for this model
            if eval_info["fallback_level"] == FallbackLevel.UNSEEN_FALLBACK:
                safeguards_applied.append(
                    f"Missing historical data for model '{model_name}': assigned neutral baseline prior ({self.shrinkage_prior:.2f})."
                )
            elif eval_info["sample_size"] < self.min_sample_threshold:
                safeguards_applied.append(
                    f"Insufficient sample size for '{model_name}' (N={eval_info['sample_size']} < {self.min_sample_threshold}): applied shrinkage toward neutral prior."
                )

        # Record unseen dimension safeguards
        if region and not any(e["matched_region"] for e in model_evals if e["fallback_level"] in (FallbackLevel.EXACT, FallbackLevel.REGION_LEAD)):
            safeguards_applied.append(
                f"Unseen or unstratified region '{region}': fell back to lead-time and overall skill profiles."
            )
        if weather_regime and not any(e["matched_regime"] for e in model_evals if e["fallback_level"] in (FallbackLevel.EXACT, FallbackLevel.REGIME_LEAD)):
            safeguards_applied.append(
                f"Unseen or unstratified weather regime '{weather_regime}': fell back to lead-time and regional skill profiles."
            )

        # 2. Convert reliability scores into raw weights using exponential/power scaling
        raw_weights: Dict[str, float] = {}
        for ev in model_evals:
            m = ev["model_name"]
            score = max(0.001, ev["reliability_score"])
            # Power formulation rewards consistently superior skill
            raw_weights[m] = math.pow(score, self.power)

        # 3. Apply simplex projection with min/max bounds safeguards
        final_weights, bounds_triggered = self._project_onto_simplex(
            raw_weights=raw_weights,
            min_weight=effective_min_w,
            max_weight=effective_max_w,
        )
        if bounds_triggered:
            safeguards_applied.append(
                f"Enforced weight boundary constraints: min_weight floor ({effective_min_w:.1%}), max_weight ceiling ({effective_max_w:.1%})."
            )

        # 4. Construct detailed model explanations
        details: List[ModelWeightDetail] = []
        for ev in model_evals:
            m = ev["model_name"]
            w = final_weights[m]
            exp = self._build_model_explanation(ev, w, norm_var_str, lead_time_hours, region, norm_regime_str)
            details.append(
                ModelWeightDetail(
                    model_name=m,
                    weight=w,
                    raw_score=round(ev["raw_score"], 4),
                    reliability_score=round(ev["reliability_score"], 4),
                    sample_size=ev["sample_size"],
                    fallback_level=ev["fallback_level"],
                    explanation=exp,
                )
            )

        # 5. Synthesize summary explanation
        summary_exp = self._build_summary_explanation(
            details=details,
            variable=norm_var_str,
            lead_time_hours=lead_time_hours,
            region=region,
            season=norm_season_str,
            weather_regime=norm_regime_str,
            safeguards=safeguards_applied,
        )

        return AdaptiveWeightOutput(
            variable=norm_var_str,
            region=region,
            lead_time_hours=lead_time_hours,
            season=norm_season_str,
            weather_regime=norm_regime_str,
            weights=final_weights,
            normalized_weights=final_weights,
            model_details=details,
            summary_explanation=summary_exp,
            safeguards_applied=safeguards_applied,
        )

    # -------------------------------------------------------------
    # Performance Evaluation & Hierarchical Query
    # -------------------------------------------------------------
    def _evaluate_model_performance(
        self,
        model_name: str,
        variable: ForecastVariable,
        lead_time_hours: int,
        region: Optional[str],
        season: Optional[Season],
        weather_regime: Optional[WeatherRegime],
        regime_str: Optional[str] = None,
        historical_performance: Optional[Union[SkillScoreStore, List[HistoricalSkillRecord], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Hierarchically queries verified performance for a model and computes
        its reliability score with Bayesian sample size shrinkage.
        """
        # Case A: Custom performance dictionary provided
        if isinstance(historical_performance, dict):
            return self._evaluate_from_custom_dict(model_name, historical_performance, regime_str)

        # Case B: Query SkillScoreStore or list of records
        store = (
            historical_performance
            if isinstance(historical_performance, SkillScoreStore)
            else (self.skill_store if historical_performance is None else None)
        )
        records = store.get_all_records() if store else (historical_performance if isinstance(historical_performance, list) else [])

        # Filter candidate records for this model
        candidates = [
            r for r in records
            if self._model_names_match(model_name, r.dimension.model_name) and r.dimension.variable == variable
        ]

        if not candidates:
            # Model unseen in historical database
            return {
                "model_name": model_name,
                "raw_score": self.shrinkage_prior,
                "reliability_score": self.shrinkage_prior,
                "sample_size": 0,
                "fallback_level": FallbackLevel.UNSEEN_FALLBACK,
                "matched_region": False,
                "matched_regime": False,
                "metrics": None,
            }

        # Hierarchy 1: Exact match (lead_time, region, regime, season)
        if region and weather_regime and season:
            for r in candidates:
                d = r.dimension
                if (d.lead_time_hours == lead_time_hours and
                    d.region and region.lower() in d.region.lower() and
                    d.weather_regime == weather_regime and
                    d.season == season):
                    return self._process_matched_record(model_name, r, FallbackLevel.EXACT, True, True)

        # Hierarchy 2: Region + Lead Time + Regime match
        if region and weather_regime:
            for r in candidates:
                d = r.dimension
                if (d.lead_time_hours == lead_time_hours and
                    d.region and region.lower() in d.region.lower() and
                    d.weather_regime == weather_regime):
                    return self._process_matched_record(model_name, r, FallbackLevel.EXACT, True, True)

        # Hierarchy 3: Region + Lead Time match
        if region:
            for r in candidates:
                d = r.dimension
                if (d.lead_time_hours == lead_time_hours and
                    d.region and region.lower() in d.region.lower()):
                    return self._process_matched_record(model_name, r, FallbackLevel.REGION_LEAD, True, False)

        # Hierarchy 4: Regime + Lead Time match
        if weather_regime:
            for r in candidates:
                d = r.dimension
                if (d.lead_time_hours == lead_time_hours and
                    d.weather_regime == weather_regime):
                    return self._process_matched_record(model_name, r, FallbackLevel.REGIME_LEAD, False, True)

        # Hierarchy 5: Lead Time match
        for r in candidates:
            if r.dimension.lead_time_hours == lead_time_hours:
                return self._process_matched_record(model_name, r, FallbackLevel.LEAD_TIME, False, False)

        # Hierarchy 6: Overall Model Variable match
        overall_records = [r for r in candidates if r.dimension.lead_time_hours is None and r.dimension.region is None]
        if overall_records:
            return self._process_matched_record(model_name, overall_records[0], FallbackLevel.OVERALL, False, False)

        # Fallback to the first available record for this model
        return self._process_matched_record(model_name, candidates[0], FallbackLevel.OVERALL, False, False)

    def _process_matched_record(
        self,
        model_name: str,
        record: HistoricalSkillRecord,
        fallback_level: FallbackLevel,
        matched_region: bool,
        matched_regime: bool,
    ) -> Dict[str, Any]:
        """Extracts skill metrics and applies Bayesian sample-size shrinkage."""
        m = record.metrics
        raw_skill = m.composite_skill_score

        # If rainfall / extreme regime and CSI is available, synthesize categorical extreme threat
        if record.dimension.variable == ForecastVariable.RAINFALL and m.csi is not None and m.csi > 0:
            raw_skill = 0.60 * raw_skill + 0.40 * m.csi

        n = m.sample_size
        # Bayesian shrinkage: shrink toward prior 0.50 if sample size is small
        confidence_factor = n / (n + self.min_sample_threshold) if n > 0 else 0.0
        shrunk_skill = confidence_factor * raw_skill + (1.0 - confidence_factor) * self.shrinkage_prior

        return {
            "model_name": model_name,
            "raw_score": raw_skill,
            "reliability_score": shrunk_skill,
            "sample_size": n,
            "fallback_level": fallback_level,
            "matched_region": matched_region,
            "matched_regime": matched_regime,
            "metrics": m,
        }

    def _evaluate_from_custom_dict(
        self,
        model_name: str,
        custom_perf: Dict[str, Any],
        regime_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parses caller-supplied performance dictionaries for ad-hoc evaluations and testing."""
        source_data = custom_perf
        if regime_str:
            clean_reg = str(regime_str).lower().replace("_", "").replace(" ", "").replace("/", "")
            for k, v in custom_perf.items():
                if isinstance(v, dict):
                    clean_k = str(k).lower().replace("_", "").replace(" ", "").replace("/", "")
                    if clean_k == clean_reg or clean_reg in clean_k or clean_k in clean_reg:
                        source_data = v
                        break

        # Find matching model key
        matched_key = None
        for k in source_data:
            if self._model_names_match(model_name, k):
                matched_key = k
                break

        if matched_key is None:
            return {
                "model_name": model_name,
                "raw_score": self.shrinkage_prior,
                "reliability_score": self.shrinkage_prior,
                "sample_size": 0,
                "fallback_level": FallbackLevel.UNSEEN_FALLBACK,
                "matched_region": False,
                "matched_regime": False,
                "metrics": None,
            }

        val = source_data[matched_key]
        if isinstance(val, (int, float)):
            # Direct numeric score or error
            if val > 1.0:
                # Treated as RMSE/MAE error -> invert
                raw_score = 1.0 / (1.0 + float(val) / 5.0)
            else:
                raw_score = float(val)
            sample_size = 50
        elif isinstance(val, dict):
            if "skill" in val:
                raw_score = float(val["skill"])
            elif "composite_skill_score" in val:
                raw_score = float(val["composite_skill_score"])
            elif "rmse" in val:
                raw_score = 1.0 / (1.0 + float(val["rmse"]) / 5.0)
            elif "mae" in val:
                raw_score = 1.0 / (1.0 + float(val["mae"]) / 4.0)
            else:
                raw_score = self.shrinkage_prior

            sample_size = val.get("sample_size", 50)
        else:
            raw_score = self.shrinkage_prior
            sample_size = 0

        # Sample size shrinkage
        confidence_factor = sample_size / (sample_size + self.min_sample_threshold) if sample_size > 0 else 0.0
        shrunk_skill = confidence_factor * raw_score + (1.0 - confidence_factor) * self.shrinkage_prior

        return {
            "model_name": model_name,
            "raw_score": raw_score,
            "reliability_score": shrunk_skill,
            "sample_size": sample_size,
            "fallback_level": FallbackLevel.EXACT if sample_size >= self.min_sample_threshold else FallbackLevel.OVERALL,
            "matched_region": True,
            "matched_regime": True,
            "metrics": None,
        }

    # -------------------------------------------------------------
    # Simplex Projection & Bounds Enforcement Safeguard
    # -------------------------------------------------------------
    def _project_onto_simplex(
        self,
        raw_weights: Dict[str, float],
        min_weight: float,
        max_weight: float,
    ) -> Tuple[Dict[str, float], bool]:
        """
        Projects raw weights onto the probability simplex sum(w) = 1.0,
        enforcing min_weight <= w_i <= max_weight.
        Guarantees strict sum(w) == 1.0000.
        """
        n = len(raw_weights)
        if n == 0:
            return {}, False

        # Verify mathematical feasibility of bounds for n models
        if n * min_weight > 1.0 or n * max_weight < 1.0:
            min_weight = 0.0
            max_weight = 1.0

        total_raw = sum(raw_weights.values())
        if total_raw > 0:
            weights = {k: v / total_raw for k, v in raw_weights.items()}
        else:
            weights = {k: 1.0 / n for k in raw_weights}

        bounds_triggered = False

        # Iterative clamping and redistribution
        for _ in range(n + 2):
            clamped = {}
            unclamped_keys = []
            for k, v in weights.items():
                if v < min_weight:
                    clamped[k] = min_weight
                    bounds_triggered = True
                elif v > max_weight:
                    clamped[k] = max_weight
                    bounds_triggered = True
                else:
                    unclamped_keys.append(k)

            if len(clamped) == 0:
                break
            if len(unclamped_keys) == 0:
                weights = {k: 1.0 / n for k in weights}
                break

            sum_clamped = sum(clamped.values())
            remaining_budget = max(0.0, 1.0 - sum_clamped)
            sum_unclamped = sum(weights[k] for k in unclamped_keys)

            if sum_unclamped > 0:
                scale = remaining_budget / sum_unclamped
                for k in unclamped_keys:
                    weights[k] = weights[k] * scale
            else:
                for k in unclamped_keys:
                    weights[k] = remaining_budget / len(unclamped_keys)

            for k, v in clamped.items():
                weights[k] = v

        # Normalize and eliminate floating point rounding error so sum is EXACTLY 1.0000
        current_sum = sum(weights.values())
        norm_weights = {k: round(v / current_sum, 4) for k, v in weights.items()}
        diff = round(1.0 - sum(norm_weights.values()), 4)
        if diff != 0.0:
            # Add residue to the model with highest weight
            top_key = max(norm_weights.keys(), key=lambda k: norm_weights[k])
            norm_weights[top_key] = round(norm_weights[top_key] + diff, 4)

        return norm_weights, bounds_triggered

    # -------------------------------------------------------------
    # Explanations & Interpretability Builders
    # -------------------------------------------------------------
    def _build_model_explanation(
        self,
        eval_info: Dict[str, Any],
        weight: float,
        variable: str,
        lead_time_hours: int,
        region: Optional[str],
        regime: Optional[str],
    ) -> str:
        pct = weight * 100.0
        lvl = eval_info["fallback_level"].value
        m = eval_info["metrics"]

        if eval_info["fallback_level"] == FallbackLevel.UNSEEN_FALLBACK:
            return (
                f"Assigned safety floor weight ({pct:.1f}%) based on neutral prior; "
                f"no historical verification pairs exist for this model/variable slice."
            )

        metric_details = []
        if m:
            metric_details.append(f"RMSE={m.rmse:.2f}")
            metric_details.append(f"MAE={m.mae:.2f}")
            metric_details.append(f"Bias={m.bias:+.2f}")
            if m.csi is not None:
                metric_details.append(f"CSI={m.csi:.2f}")
            metric_details.append(f"CompositeSkill={m.composite_skill_score:.2f}")

        details_str = f" ({', '.join(metric_details)})" if metric_details else ""
        return (
            f"Derived {pct:.1f}% weight based on {lvl} matched verification{details_str} "
            f"across {eval_info['sample_size']} observations at {lead_time_hours}h lead time."
        )

    def _build_summary_explanation(
        self,
        details: List[ModelWeightDetail],
        variable: str,
        lead_time_hours: int,
        region: Optional[str],
        season: Optional[str],
        weather_regime: Optional[str],
        safeguards: List[str],
    ) -> str:
        sorted_details = sorted(details, key=lambda d: d.weight, reverse=True)
        top = sorted_details[0]
        runner_up = sorted_details[1] if len(sorted_details) > 1 else None

        parts = [
            f"For {variable} forecasting at {lead_time_hours}h lead time"
            + (f" in {region}" if region else "")
            + (f" under {weather_regime} regime" if weather_regime else "")
            + f", '{top.model_name}' received the dominant weight of {top.weight * 100:.1f}% "
            f"(reliability score: {top.reliability_score:.2f}, N={top.sample_size})."
        ]

        if runner_up:
            parts.append(
                f"'{runner_up.model_name}' acts as the primary secondary consensus member with {runner_up.weight * 100:.1f}% weight."
            )

        if safeguards:
            parts.append(f"Active safeguards applied: {len(safeguards)} constraint(s) enforced.")

        return " ".join(parts)

    # -------------------------------------------------------------
    # Normalization Helpers
    # -------------------------------------------------------------
    def _model_names_match(self, query: str, target: str) -> bool:
        import re
        q = query.strip().lower()
        t = target.strip().lower()
        if q == t:
            return True
        # Word boundary search prevents substring clashes (e.g. knownmodel vs unknownmodel)
        if re.search(r'\b' + re.escape(q) + r'\b', t) or re.search(r'\b' + re.escape(t) + r'\b', q):
            return True
        # Handle specific common aliases
        aliases = {
            "gfs": "nwp model a",
            "ecmwf": "nwp model b",
            "ensemble": "ensemble forecast",
            "graphcast": "ai/ml forecast",
            "ai": "ai/ml forecast",
        }
        for alias, mapped in aliases.items():
            if alias in q and mapped in t:
                return True
        return False

    def _normalize_variable(self, var: Union[ForecastVariable, str]) -> Tuple[str, ForecastVariable]:
        s = var.value if isinstance(var, ForecastVariable) else str(var).lower().strip()
        if "rain" in s or "precip" in s:
            return "rainfall", ForecastVariable.RAINFALL
        if "temp" in s:
            return "temperature", ForecastVariable.TEMPERATURE
        if "wind_dir" in s or "direction" in s:
            return "wind_direction", ForecastVariable.WIND_DIRECTION
        if "wind" in s:
            return "wind_speed", ForecastVariable.WIND_SPEED
        return "rainfall", ForecastVariable.RAINFALL

    def _normalize_season(self, season: Optional[Union[Season, str]]) -> Tuple[Optional[str], Optional[Season]]:
        if not season:
            return None, None
        s = season.value if isinstance(season, Season) else str(season).lower().strip()
        for member in Season:
            if member.value in s:
                return member.value, member
        return s, None

    def _normalize_regime(
        self, regime: Optional[Union[WeatherRegime, RegimeType, str]]
    ) -> Tuple[Optional[str], Optional[WeatherRegime]]:
        if not regime:
            return None, None
        s = regime.value if hasattr(regime, "value") else str(regime).strip()
        clean_s = s.lower().replace("_", "").replace(" ", "").replace("/", "")
        for member in WeatherRegime:
            clean_m = member.value.lower().replace("_", "").replace(" ", "").replace("/", "")
            if clean_m in clean_s or clean_s in clean_m:
                return member.value, member
        for member in RegimeType:
            clean_m = member.value.lower().replace("_", "").replace(" ", "").replace("/", "")
            if clean_m in clean_s or clean_s in clean_m:
                return member.value, None
        return s, None
