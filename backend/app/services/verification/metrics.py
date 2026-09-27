import math
from typing import List, Optional, Tuple
from backend.app.services.verification.schemas import ComprehensiveSkillScore


class VerificationMath:
    """
    Standardized mathematical algorithms for meteorological forecast verification.
    Compliant with WMO (World Meteorological Organization) and IMD verification standards.
    """

    @classmethod
    def compute_continuous_metrics(
        cls,
        forecasts: List[float],
        observations: List[float],
    ) -> Tuple[float, float, float, float]:
        """
        Calculates (MAE, RMSE, Bias, Correlation).
        """
        n = len(forecasts)
        if n == 0:
            return 0.0, 0.0, 0.0, 0.0

        errors = [f - o for f, o in zip(forecasts, observations)]
        mae = sum(abs(e) for e in errors) / n
        rmse = math.sqrt(sum(e ** 2 for e in errors) / n)
        bias = sum(errors) / n

        mean_f = sum(forecasts) / n
        mean_o = sum(observations) / n

        num = sum((f - mean_f) * (o - mean_o) for f, o in zip(forecasts, observations))
        den_f = math.sqrt(sum((f - mean_f) ** 2 for f in forecasts))
        den_o = math.sqrt(sum((o - mean_o) ** 2 for o in observations))

        if den_f * den_o > 0:
            corr = max(-1.0, min(1.0, num / (den_f * den_o)))
        else:
            corr = 1.0 if (den_f == 0 and den_o == 0) else 0.0

        return round(mae, 2), round(rmse, 2), round(bias, 2), round(corr, 3)

    @classmethod
    def compute_contingency_table(
        cls,
        forecasts: List[float],
        observations: List[float],
        threshold: float,
    ) -> Tuple[int, int, int, int]:
        """
        Builds 2x2 contingency table: (Hits, Misses, False Alarms, Correct Negatives).
        """
        hits = 0
        misses = 0
        false_alarms = 0
        correct_negs = 0

        for f, o in zip(forecasts, observations):
            f_event = f >= threshold
            o_event = o >= threshold

            if f_event and o_event:
                hits += 1
            elif not f_event and o_event:
                misses += 1
            elif f_event and not o_event:
                false_alarms += 1
            else:
                correct_negs += 1

        return hits, misses, false_alarms, correct_negs

    @classmethod
    def compute_extreme_skill_scores(
        cls,
        hits: int,
        misses: int,
        false_alarms: int,
        correct_negs: int,
    ) -> Tuple[float, float, float, float]:
        """
        Calculates (POD, FAR, CSI, ETS).
        """
        total = hits + misses + false_alarms + correct_negs
        if total == 0:
            return 0.0, 0.0, 0.0, 0.0

        # 1. Probability of Detection (Hit Rate): H / (H + M)
        pod_den = hits + misses
        pod = (hits / pod_den) if pod_den > 0 else (1.0 if misses == 0 else 0.0)

        # 2. False Alarm Ratio: F / (H + F)
        far_den = hits + false_alarms
        far = (false_alarms / far_den) if far_den > 0 else 0.0

        # 3. Critical Success Index (Threat Score): H / (H + M + F)
        csi_den = hits + misses + false_alarms
        csi = (hits / csi_den) if csi_den > 0 else (1.0 if (misses == 0 and false_alarms == 0) else 0.0)

        # 4. Equitable Threat Score (Gilbert Skill Score)
        # H_r = (H + M) * (H + F) / Total
        h_r = ((hits + misses) * (hits + false_alarms)) / total
        ets_den = hits + misses + false_alarms - h_r
        ets = ((hits - h_r) / ets_den) if ets_den != 0 else 0.0

        return round(pod, 3), round(far, 3), round(csi, 3), round(ets, 3)

    @classmethod
    def compute_probabilistic_metrics(
        cls,
        forecast_probs: List[float],
        observations: List[float],
        threshold: float,
    ) -> Tuple[float, float]:
        """
        Calculates (Brier Score, Brier Skill Score).
        """
        n = len(forecast_probs)
        if n == 0:
            return 0.0, 0.0

        # Observed binary outcomes: 1 if event occurred, 0 otherwise
        obs_binary = [1.0 if o >= threshold else 0.0 for o in observations]
        brier_score = sum((p - o) ** 2 for p, o in zip(forecast_probs, obs_binary)) / n

        # Climatological baseline probability
        base_rate = sum(obs_binary) / n
        brier_clim = sum((base_rate - o) ** 2 for o in obs_binary) / n

        if brier_clim > 0:
            bss = 1.0 - (brier_score / brier_clim)
        else:
            bss = 1.0 if brier_score == 0 else 0.0

        return round(brier_score, 4), round(bss, 3)

    @classmethod
    def compute_composite_skill_score(
        cls,
        rmse: float,
        corr: float,
        csi: Optional[float] = None,
        scale_factor: float = 10.0,
    ) -> float:
        """
        Computes a normalized composite skill factor in [0.05, 1.0] for adaptive weighting.
        Combines accuracy (normalized inverse-RMSE), consistency (correlation), and extreme detection (CSI).
        """
        # Normalized inverse RMSE: 1 / (1 + RMSE / scale)
        norm_rmse_skill = 1.0 / (1.0 + max(0.0, rmse) / scale_factor)

        # Normalized correlation factor: (corr + 1) / 2
        norm_corr_skill = max(0.0, min(1.0, (corr + 1.0) / 2.0))

        if csi is not None:
            # Weighted average with extreme skill
            composite = 0.45 * norm_rmse_skill + 0.35 * norm_corr_skill + 0.20 * csi
        else:
            composite = 0.55 * norm_rmse_skill + 0.45 * norm_corr_skill

        return round(max(0.05, min(1.0, composite)), 4)
