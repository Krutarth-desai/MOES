import math
from typing import Dict, List, Tuple
from backend.app.models.domain import GridCell, WeatherRegime, WeatherVariable
from backend.app.services.blender_interface import BaseBlender
from backend.app.ml.weight_model import AdaptiveWeightModel


class AdaptiveSoftmaxBlender(BaseBlender):
    """
    Adaptive Multi-Model Forecast Blender using Softmax Simplex Weights.
    """

    def __init__(self, weight_model: AdaptiveWeightModel = None):
        self.weight_model = weight_model or AdaptiveWeightModel()

    def compute_weights(
        self,
        lat: float,
        lon: float,
        lead_time_hours: int,
        regime: WeatherRegime,
        variable: WeatherVariable,
        elevation_m: float = 100.0,
    ) -> Dict[str, float]:
        return self.weight_model.predict_weights(
            lat=lat,
            lon=lon,
            lead_time_hours=lead_time_hours,
            regime=regime,
            variable=variable,
            elevation_m=elevation_m,
        )

    def blend_point(
        self,
        raw_predictions: Dict[str, float],
        weights: Dict[str, float],
        variable: WeatherVariable,
    ) -> Tuple[float, float, float]:
        """
        Compute weighted blended forecast value and confidence interval bounds.
        """
        weighted_sum = 0.0
        total_w = 0.0
        values = []

        for model_id, val in raw_predictions.items():
            w = weights.get(model_id, 0.25)
            weighted_sum += val * w
            total_w += w
            values.append(val)

        blended = weighted_sum / (total_w if total_w > 0 else 1.0)

        # Enforce non-negativity for precipitation
        if variable == WeatherVariable.PRECIPITATION:
            blended = max(0.0, blended)

        blended = round(blended, 1)

        # Estimate multi-model ensemble spread (standard deviation)
        if len(values) > 1:
            mean_val = sum(values) / len(values)
            variance = sum((v - mean_val) ** 2 for v in values) / (len(values) - 1)
            spread = math.sqrt(variance)
        else:
            spread = 1.0

        # Confidence bounds (approx. 10th and 90th percentile: 1.28 * std)
        margin = 1.28 * spread
        conf_10th = max(0.0 if variable == WeatherVariable.PRECIPITATION else -99.0, round(blended - margin, 1))
        conf_90th = round(blended + margin, 1)

        return blended, conf_10th, conf_90th

    def blend_grid(
        self,
        model_grids: Dict[str, List[GridCell]],
        weights: Dict[str, float],
        variable: WeatherVariable,
    ) -> List[GridCell]:
        """
        Produce a blended grid given spatial grid lists from individual models.
        """
        # Align grid cells by (lat, lon)
        combined: Dict[Tuple[float, float], Dict[str, float]] = {}
        for model_id, cells in model_grids.items():
            for c in cells:
                key = (c.lat, c.lon)
                if key not in combined:
                    combined[key] = {}
                combined[key][model_id] = c.value

        blended_cells = []
        for (lat, lon), preds in combined.items():
            blended_val, _, _ = self.blend_point(preds, weights, variable)
            blended_cells.append(GridCell(lat=lat, lon=lon, value=blended_val))

        return blended_cells
