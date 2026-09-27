import math
from collections import defaultdict
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.data.ingestion.schema import ForecastVariable
from backend.app.data.observation.matcher import MatchedPair


class ErrorMetrics(BaseModel):
    sample_count: int
    mean_absolute_error: float = Field(description="MAE in variable unit")
    root_mean_square_error: float = Field(description="RMSE in variable unit")
    mean_bias: float = Field(description="Signed Mean Bias: positive means over-prediction, negative means under-prediction")
    pearson_correlation: float = Field(description="Correlation coefficient (-1.0 to 1.0)")

    # Optional categorical extreme skill metrics (e.g. for heavy rain or heatwave)
    hits: Optional[int] = None
    misses: Optional[int] = None
    false_alarms: Optional[int] = None
    correct_negatives: Optional[int] = None
    critical_success_index: Optional[float] = None
    probability_of_detection: Optional[float] = None
    false_alarm_ratio: Optional[float] = None


class ModelComparisonSummary(BaseModel):
    model_name: str
    variable: ForecastVariable
    overall_metrics: ErrorMetrics
    lead_time_profile: Dict[int, ErrorMetrics] = Field(
        default_factory=dict,
        description="Error metrics broken down by lead time (24h, 48h, etc.)"
    )


class ForecastErrorCalculator:
    """
    Computes statistical verification metrics and error profiles from matched forecast-observation pairs.
    """

    @classmethod
    def compute_metrics(
        cls,
        pairs: List[MatchedPair],
        extreme_threshold: Optional[float] = None,
    ) -> ErrorMetrics:
        n = len(pairs)
        if n == 0:
            return ErrorMetrics(
                sample_count=0,
                mean_absolute_error=0.0,
                root_mean_square_error=0.0,
                mean_bias=0.0,
                pearson_correlation=0.0,
            )

        mae = sum(p.absolute_error for p in pairs) / n
        rmse = math.sqrt(sum(p.squared_error for p in pairs) / n)
        bias = sum(p.error for p in pairs) / n

        # Pearson correlation
        fcst_vals = [p.forecast_value for p in pairs]
        obs_vals = [p.observed_value for p in pairs]
        mean_f = sum(fcst_vals) / n
        mean_o = sum(obs_vals) / n

        num = sum((f - mean_f) * (o - mean_o) for f, o in zip(fcst_vals, obs_vals))
        den_f = math.sqrt(sum((f - mean_f) ** 2 for f in fcst_vals))
        den_o = math.sqrt(sum((o - mean_o) ** 2 for o in obs_vals))

        if (den_f * den_o) > 0:
            corr = num / (den_f * den_o)
        else:
            corr = 1.0 if den_f == 0 and den_o == 0 else 0.0

        metrics = ErrorMetrics(
            sample_count=n,
            mean_absolute_error=round(mae, 2),
            root_mean_square_error=round(rmse, 2),
            mean_bias=round(bias, 2),
            pearson_correlation=round(max(-1.0, min(1.0, corr)), 3),
        )

        # Categorical contingency table if threshold provided
        if extreme_threshold is not None:
            hits = sum(1 for p in pairs if p.forecast_value >= extreme_threshold and p.observed_value >= extreme_threshold)
            misses = sum(1 for p in pairs if p.forecast_value < extreme_threshold and p.observed_value >= extreme_threshold)
            false_alarms = sum(1 for p in pairs if p.forecast_value >= extreme_threshold and p.observed_value < extreme_threshold)
            correct_negs = sum(1 for p in pairs if p.forecast_value < extreme_threshold and p.observed_value < extreme_threshold)

            csi_den = hits + misses + false_alarms
            csi = (hits / csi_den) if csi_den > 0 else 1.0

            pod_den = hits + misses
            pod = (hits / pod_den) if pod_den > 0 else 1.0

            far_den = hits + false_alarms
            far = (false_alarms / far_den) if far_den > 0 else 0.0

            metrics.hits = hits
            metrics.misses = misses
            metrics.false_alarms = false_alarms
            metrics.correct_negatives = correct_negs
            metrics.critical_success_index = round(csi, 3)
            metrics.probability_of_detection = round(pod, 3)
            metrics.false_alarm_ratio = round(far, 3)

        return metrics

    @classmethod
    def evaluate_by_model_and_variable(
        cls,
        matched_pairs: List[MatchedPair],
    ) -> Dict[str, Dict[str, ModelComparisonSummary]]:
        """
        Calculates error scorecards grouped by:
        model_name -> variable -> ModelComparisonSummary (with lead time breakdown)
        """
        # Bucket by model and variable
        buckets: Dict[str, Dict[ForecastVariable, List[MatchedPair]]] = defaultdict(lambda: defaultdict(list))
        for p in matched_pairs:
            buckets[p.model_name][p.variable].append(p)

        results: Dict[str, Dict[str, ModelComparisonSummary]] = defaultdict(dict)

        for model_name, var_dict in buckets.items():
            for var, pairs in var_dict.items():
                threshold = 64.5 if var == ForecastVariable.RAINFALL else (40.0 if var == ForecastVariable.TEMPERATURE else None)
                overall = cls.compute_metrics(pairs, extreme_threshold=threshold)

                # Lead time breakdown
                by_lead: Dict[int, List[MatchedPair]] = defaultdict(list)
                for p in pairs:
                    by_lead[p.lead_time_hours].append(p)

                lead_profile: Dict[int, ErrorMetrics] = {}
                for lead_h, lead_pairs in sorted(by_lead.items()):
                    lead_profile[lead_h] = cls.compute_metrics(lead_pairs, extreme_threshold=threshold)

                results[model_name][var.value] = ModelComparisonSummary(
                    model_name=model_name,
                    variable=var,
                    overall_metrics=overall,
                    lead_time_profile=lead_profile,
                )

        return results

    @classmethod
    def evaluate_by_region(
        cls,
        matched_pairs: List[MatchedPair],
        variable: ForecastVariable,
    ) -> Dict[str, Dict[str, ErrorMetrics]]:
        """
        Calculates error scorecards grouped by:
        region -> model_name -> ErrorMetrics
        """
        filtered = [p for p in matched_pairs if p.variable == variable]
        buckets: Dict[str, Dict[str, List[MatchedPair]]] = defaultdict(lambda: defaultdict(list))

        for p in filtered:
            buckets[p.region][p.model_name].append(p)

        regional_summary: Dict[str, Dict[str, ErrorMetrics]] = defaultdict(dict)
        for region, model_dict in buckets.items():
            for model_name, pairs in model_dict.items():
                regional_summary[region][model_name] = cls.compute_metrics(pairs)

        return regional_summary
