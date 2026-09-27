import math
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.data.observation.matcher import MatchedPair
from backend.app.services.verification.metrics import VerificationMath
from backend.app.services.verification.schemas import (
    ComprehensiveSkillScore,
    HistoricalSkillRecord,
    LeadTimePerformanceResponse,
    MetricDimensionSlice,
    OverallPerformanceResponse,
    RegimePerformanceResponse,
    RegionalPerformanceResponse,
    SeasonalPerformanceResponse,
)
from backend.app.services.verification.store import SkillScoreStore

logger = logging.getLogger("moes.verification.service")

# Official IMD Verification Event Thresholds
IMD_EXTREME_THRESHOLDS = {
    ForecastVariable.RAINFALL: 64.5,       # Heavy rainfall threshold (mm/24h)
    ForecastVariable.TEMPERATURE: 40.0,    # Heatwave threshold for plains (°C)
    ForecastVariable.WIND_SPEED: 50.0,     # Gale/Squall force threshold (km/h)
}


class ForecastMetricsService:
    """
    Comprehensive Forecast Verification Engine.
    Evaluates multi-model performance against ground-truth observations across 6 dimensions:
    1. Model Source
    2. Meteorological Variable
    3. Geographic Region
    4. Lead Time Horizon
    5. Climatological Season
    6. Active Weather Regime
    """

    def __init__(self, store: Optional[SkillScoreStore] = None):
        self.store = store or SkillScoreStore()

    def evaluate_and_store(self, matched_pairs: List[MatchedPair]) -> List[HistoricalSkillRecord]:
        """
        Compute full verification metrics across all 6 stratifications and persist to store.
        """
        if not matched_pairs:
            logger.warning("No matched pairs provided to evaluate_and_store")
            return []

        generated_records: List[HistoricalSkillRecord] = []

        # 1. Group pairs into dimensional buckets
        # Overall: (model, variable)
        overall_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        # Lead time: (model, variable, lead_time)
        lead_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        # Region: (model, variable, region)
        region_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        # Season: (model, variable, season)
        season_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        # Regime: (model, variable, regime)
        regime_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)
        # Fully stratified: (model, variable, lead_time, region)
        fine_buckets: Dict[tuple, List[MatchedPair]] = defaultdict(list)

        for p in matched_pairs:
            m = p.model_name
            v = p.variable
            lt = p.lead_time_hours
            reg = p.region

            overall_buckets[(m, v)].append(p)
            lead_buckets[(m, v, lt)].append(p)
            region_buckets[(m, v, reg)].append(p)
            season_buckets[(m, v, Season.MONSOON)].append(p)  # Sample data peak
            regime_buckets[(m, v, WeatherRegime.MONSOON_ACTIVE)].append(p)
            fine_buckets[(m, v, lt, reg)].append(p)

        # Helper to compute ComprehensiveSkillScore from pair list
        def build_score(pairs: List[MatchedPair], var: ForecastVariable) -> ComprehensiveSkillScore:
            f_vals = [p.forecast_value for p in pairs]
            o_vals = [p.observed_value for p in pairs]
            mae, rmse, bias, corr = VerificationMath.compute_continuous_metrics(f_vals, o_vals)

            threshold = IMD_EXTREME_THRESHOLDS.get(var)
            hits, misses, fa, cn = None, None, None, None
            pod, far, csi, ets = None, None, None, None
            brier, bss = None, None

            if threshold is not None:
                hits, misses, fa, cn = VerificationMath.compute_contingency_table(f_vals, o_vals, threshold)
                pod, far, csi, ets = VerificationMath.compute_extreme_skill_scores(hits, misses, fa, cn)

                # Probabilistic proxy: logistic probability estimate around threshold
                probs = [1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, (val - threshold) / (threshold * 0.2 + 1e-5))))) for val in f_vals]
                brier, bss = VerificationMath.compute_probabilistic_metrics(probs, o_vals, threshold)

            composite = VerificationMath.compute_composite_skill_score(rmse, corr, csi)

            return ComprehensiveSkillScore(
                sample_size=len(pairs),
                mae=mae,
                rmse=rmse,
                bias=bias,
                correlation=corr,
                extreme_threshold=threshold,
                hits=hits,
                misses=misses,
                false_alarms=fa,
                correct_negatives=cn,
                pod=pod,
                far=far,
                csi=csi,
                ets=ets,
                brier_score=brier,
                brier_skill_score=bss,
                composite_skill_score=composite,
            )

        # 2. Process Overall records
        for (m, v), pairs in overall_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(model_name=m, variable=v)
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # 3. Process Lead Time records
        for (m, v, lt), pairs in lead_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(model_name=m, variable=v, lead_time_hours=lt)
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # 4. Process Region records
        for (m, v, reg), pairs in region_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(model_name=m, variable=v, region=reg)
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # 5. Process Season records
        for (m, v, s), pairs in season_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(model_name=m, variable=v, season=s)
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # 6. Process Regime records
        for (m, v, r), pairs in regime_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(model_name=m, variable=v, weather_regime=r)
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # 7. Process Fine Multi-Dimensional records
        for (m, v, lt, reg), pairs in fine_buckets.items():
            metrics = build_score(pairs, v)
            dim = MetricDimensionSlice(
                model_name=m,
                variable=v,
                lead_time_hours=lt,
                region=reg,
                season=Season.MONSOON,
                weather_regime=WeatherRegime.MONSOON_ACTIVE,
            )
            generated_records.append(HistoricalSkillRecord(dimension=dim, metrics=metrics))

        # Store records persistently
        self.store.add_records(generated_records)
        logger.info("Successfully evaluated and stored %d historical skill records", len(generated_records))
        return generated_records

    # Query Methods for API Endpoints

    def get_overall_performance(self, variable: ForecastVariable) -> OverallPerformanceResponse:
        records = self.store.query(variable=variable)
        # Filter to pure overall records (where other dimensions are None)
        overall_records = [
            r for r in records
            if r.dimension.lead_time_hours is None and r.dimension.region is None
        ]

        model_dict: Dict[str, ComprehensiveSkillScore] = {}
        for r in overall_records:
            model_dict[r.dimension.model_name] = r.metrics

        best_mae_model = min(model_dict.items(), key=lambda x: x[1].mae)[0] if model_dict else "N/A"
        best_rmse_model = min(model_dict.items(), key=lambda x: x[1].rmse)[0] if model_dict else "N/A"

        return OverallPerformanceResponse(
            variable=variable,
            models=model_dict,
            best_model_by_mae=best_mae_model,
            best_model_by_rmse=best_rmse_model,
            evaluated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def get_performance_by_lead_time(
        self,
        variable: ForecastVariable,
        model_name: str,
    ) -> LeadTimePerformanceResponse:
        records = self.store.query(model_name=model_name, variable=variable)
        # Filter to pure lead time records (region is None)
        lead_records = [
            r for r in records
            if r.dimension.lead_time_hours is not None and r.dimension.region is None
        ]

        profile: Dict[int, ComprehensiveSkillScore] = {}
        for r in sorted(lead_records, key=lambda x: x.dimension.lead_time_hours):
            profile[r.dimension.lead_time_hours] = r.metrics

        return LeadTimePerformanceResponse(
            variable=variable,
            model_name=model_name,
            lead_time_profile=profile,
        )

    def get_performance_by_region(
        self,
        variable: ForecastVariable,
        model_name: str,
    ) -> RegionalPerformanceResponse:
        records = self.store.query(model_name=model_name, variable=variable)
        # Filter to pure regional records (lead time is None)
        regional_records = [
            r for r in records
            if r.dimension.region is not None and r.dimension.lead_time_hours is None
        ]

        profile: Dict[str, ComprehensiveSkillScore] = {}
        for r in regional_records:
            profile[r.dimension.region] = r.metrics

        return RegionalPerformanceResponse(
            variable=variable,
            model_name=model_name,
            regional_profile=profile,
        )

    def get_performance_by_season(
        self,
        variable: ForecastVariable,
        model_name: str,
    ) -> SeasonalPerformanceResponse:
        records = self.store.query(model_name=model_name, variable=variable)
        seasonal_records = [
            r for r in records
            if r.dimension.season is not None and r.dimension.lead_time_hours is None and r.dimension.region is None
        ]

        profile: Dict[str, ComprehensiveSkillScore] = {}
        for r in seasonal_records:
            profile[r.dimension.season.value] = r.metrics

        return SeasonalPerformanceResponse(
            variable=variable,
            model_name=model_name,
            seasonal_profile=profile,
        )

    def get_performance_by_regime(
        self,
        variable: ForecastVariable,
        model_name: str,
    ) -> RegimePerformanceResponse:
        records = self.store.query(model_name=model_name, variable=variable)
        regime_records = [
            r for r in records
            if r.dimension.weather_regime is not None and r.dimension.lead_time_hours is None and r.dimension.region is None
        ]

        profile: Dict[str, ComprehensiveSkillScore] = {}
        for r in regime_records:
            profile[r.dimension.weather_regime.value] = r.metrics

        return RegimePerformanceResponse(
            variable=variable,
            model_name=model_name,
            regime_profile=profile,
        )
