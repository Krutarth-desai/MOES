import math
from typing import Dict, List
from backend.app.models.domain import WeatherRegime, WeatherVariable
from backend.app.ml.features import extract_blending_features


class AdaptiveWeightModel:
    """
    Dynamic Weight Meta-Learner.
    Maps atmospheric, temporal, and spatial features to normalized model weights:
        w_i = exp(logit_i) / sum(exp(logit_j))
    Ensures:
    1. Simplex property (weights sum to 1.0, non-negative).
    2. Adaptive shifting across lead time (AI dominates short leads, NWP stabilizes long leads).
    3. Spatial/regime sensitivity (ECMWF/GFS prioritized in complex orography, AI favored in synoptic flow).
    """

    MODELS = ["gfs", "ecmwf", "graphcast", "pangu"]

    def __init__(self, min_floor: float = 0.05):
        self.min_floor = min_floor

    def predict_weights(
        self,
        lat: float,
        lon: float,
        lead_time_hours: int,
        regime: WeatherRegime,
        variable: WeatherVariable,
        elevation_m: float = 100.0,
    ) -> Dict[str, float]:
        features = extract_blending_features(
            lat=lat,
            lon=lon,
            lead_time_hours=lead_time_hours,
            regime=regime,
            variable=variable,
            elevation_m=elevation_m,
        )

        # Baseline logits for [gfs, ecmwf, graphcast, pangu]
        # ECMWF: consistently high physical skill
        # GraphCast: state-of-the-art AI skill at 24h-72h
        # Pangu: complementary AI architecture
        # GFS: fast operational physics
        logits = {
            "gfs": 1.0,
            "ecmwf": 1.3,
            "graphcast": 1.4,
            "pangu": 1.1,
        }

        # 1. Lead-time degradation adjustment:
        # At short lead times (24-48h), AI models get a boost
        # At long lead times (>96h), NWP physics ensembles retain synoptic consistency
        lead_factor = features["norm_lead_time"]  # 0.14 to 1.0
        if lead_time_hours <= 48:
            logits["graphcast"] += 0.4
            logits["pangu"] += 0.2
        elif lead_time_hours >= 120:
            logits["ecmwf"] += 0.5
            logits["gfs"] += 0.2
            logits["graphcast"] -= 0.3
            logits["pangu"] -= 0.3

        # 2. Variable-specific adjustments:
        # Precipitation has high non-linearity: physics NWP handles convective clouds & topography
        if variable == WeatherVariable.PRECIPITATION:
            logits["ecmwf"] += 0.3
            if features["is_high_altitude"] or features["is_himalayan"]:
                logits["ecmwf"] += 0.4
                logits["gfs"] += 0.2
                logits["graphcast"] -= 0.2
        elif variable == WeatherVariable.TEMPERATURE_2M:
            # AI models excel at 2m continuous thermodynamic fields
            logits["graphcast"] += 0.3
            logits["pangu"] += 0.2

        # 3. Weather Regime sensitivity:
        if regime in (WeatherRegime.MONSOON_ACTIVE, WeatherRegime.POST_MONSOON_CYCLONE):
            # Heavy dynamic feedback favors physics-based moisture transport
            logits["ecmwf"] += 0.3
            logits["gfs"] += 0.2
        elif regime == WeatherRegime.HEATWAVE_SYNOPTIC:
            logits["graphcast"] += 0.3
            logits["ecmwf"] += 0.2

        # 4. Softmax computation with numerical stability
        max_logit = max(logits.values())
        exp_vals = {m: math.exp(logits[m] - max_logit) for m in self.MODELS}
        total_exp = sum(exp_vals.values())

        raw_weights = {m: exp_vals[m] / total_exp for m in self.MODELS}

        # Apply minimum weight floor to maintain ensemble diversity
        floored_weights = {}
        for m, w in raw_weights.items():
            floored_weights[m] = max(w, self.min_floor)

        # Re-normalize to exact 1.0
        final_total = sum(floored_weights.values())
        normalized_weights = {
            m: round(floored_weights[m] / final_total, 4) for m in self.MODELS
        }

        return normalized_weights
