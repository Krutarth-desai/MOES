import logging
import math
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union
from backend.app.data.stations import REFERENCE_STATIONS, get_station_by_id
from backend.app.models.domain import WeatherRegime, WeatherVariable
from backend.app.services.blending.schemas import (
    BlendedForecastResult,
    BlendingMethod,
    ForecastBlendRequest,
    ModelContribution,
)
from backend.app.services.blending.store import BlendedForecastStore
from backend.app.services.blending.vector_math import (
    circular_dispersion_and_confidence,
    circular_mean_degrees,
)
from backend.app.services.simulated_provider import SimulatedForecastProvider
from backend.app.services.weighting.engine import AdaptiveWeightEngine

logger = logging.getLogger("moes.blending.engine")

# Physical validity boundaries for atmospheric variables
PHYSICAL_LIMITS: Dict[str, Tuple[float, float]] = {
    "temperature": (-60.0, 65.0),       # °C
    "rainfall": (0.0, 1500.0),           # mm
    "wind_speed": (0.0, 400.0),          # km/h
    "wind_direction": (0.0, 360.0),      # degrees
}

# Variable display units
VARIABLE_UNITS: Dict[str, str] = {
    "temperature": "°C",
    "rainfall": "mm",
    "wind_speed": "km/h",
    "wind_direction": "degrees",
}

# Climatological scales for confidence index derivation
CLIMATOLOGICAL_SIGMA: Dict[str, float] = {
    "temperature": 2.5,
    "rainfall": 12.0,
    "wind_speed": 7.0,
    "wind_direction": 30.0,
}


class ForecastBlendingEngine:
    """
    Operational Forecast Blending Engine.
    
    Synthesizes multi-model predictions into a unified, dynamically weighted consensus:
    - Temperature, Rainfall, Wind Speed: Linear weighted sum
    - Wind Direction: Directional circular/vector averaging (trigonometric Yamartino method)
    
    Features:
    1. Dynamic retrieval of model forecasts and adaptive weights.
    2. Comprehensive validation: missing model tolerance, weight renormalization,
       invalid value rejection, and spatio-temporal alignment checks.
    3. Transparent weighted contribution calculation per model.
    4. Quantitative uncertainty and spread estimation.
    5. Persistence of both individual and blended forecast records.
    """

    def __init__(
        self,
        weight_engine: Optional[AdaptiveWeightEngine] = None,
        store: Optional[BlendedForecastStore] = None,
        provider: Optional[SimulatedForecastProvider] = None,
    ):
        self.weight_engine = weight_engine or AdaptiveWeightEngine()
        self.store = store or BlendedForecastStore()
        self.provider = provider or SimulatedForecastProvider()

    def blend(
        self,
        variable: Union[WeatherVariable, str],
        lead_time_hours: int = 24,
        station_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        region: Optional[str] = None,
        weather_regime: Optional[str] = None,
        model_forecasts: Optional[Dict[str, float]] = None,
        model_weights: Optional[Dict[str, float]] = None,
        model_coordinates: Optional[Dict[str, Tuple[float, float]]] = None,
        model_timestamps: Optional[Dict[str, datetime]] = None,
        persist: bool = True,
    ) -> BlendedForecastResult:
        """
        Calculates and stores the blended forecast consensus for a specific variable and location.
        """
        norm_var = self._normalize_variable(variable)
        now = timestamp or datetime.now()

        # 1. Resolve target spatial coordinates
        target_lat, target_lon, st_name, st_id = self._resolve_location(
            station_id=station_id,
            latitude=latitude,
            longitude=longitude,
        )

        # 2. Validate spatio-temporal alignment if model-specific coordinates/timestamps provided
        self._validate_alignment(
            target_lat=target_lat,
            target_lon=target_lon,
            target_time=now,
            model_coordinates=model_coordinates,
            model_timestamps=model_timestamps,
        )

        # 3. Retrieve or resolve raw model forecasts
        raw_forecasts = self._resolve_model_forecasts(
            norm_var=norm_var,
            target_lat=target_lat,
            target_lon=target_lon,
            lead_time_hours=lead_time_hours,
            explicit_forecasts=model_forecasts,
        )

        # 4. Retrieve or derive adaptive model weights
        configured_models = list(raw_forecasts.keys())
        resolved_weights = self._resolve_model_weights(
            models=configured_models,
            norm_var=norm_var,
            lead_time_hours=lead_time_hours,
            region=region or st_name,
            weather_regime=weather_regime,
            explicit_weights=model_weights,
        )

        # 5. Validate forecasts: handle missing models, reject invalid values, renormalize weights
        (
            valid_forecasts,
            renormalized_weights,
            models_available,
            models_missing,
            models_rejected,
            weights_renormalized,
        ) = self._validate_and_filter(
            norm_var=norm_var,
            raw_forecasts=raw_forecasts,
            weights=resolved_weights,
        )

        # 6. Execute blending algorithm based on variable type
        if norm_var == "wind_direction":
            blended_val, spread, conf_idx, ci_10, ci_90, contributions, method = self._blend_wind_direction(
                valid_forecasts=valid_forecasts,
                renormalized_weights=renormalized_weights,
            )
        else:
            blended_val, spread, conf_idx, ci_10, ci_90, contributions, method = self._blend_linear(
                norm_var=norm_var,
                valid_forecasts=valid_forecasts,
                renormalized_weights=renormalized_weights,
            )

        # 7. Assemble BlendedForecastResult container
        forecast_id = f"BLEND-{norm_var[:4].upper()}-{st_id or 'GRID'}-{lead_time_hours}H-{now.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
        unit = VARIABLE_UNITS.get(norm_var, "")

        result = BlendedForecastResult(
            forecast_id=forecast_id,
            timestamp=now,
            variable=norm_var,
            unit=unit,
            station_id=st_id,
            station_name=st_name,
            latitude=round(target_lat, 4),
            longitude=round(target_lon, 4),
            lead_time_hours=lead_time_hours,
            region=region or st_name,
            weather_regime=weather_regime,
            individual_forecasts={k: round(v, 2) for k, v in valid_forecasts.items()},
            model_weights={k: round(v, 4) for k, v in renormalized_weights.items()},
            blended_value=round(blended_val, 2),
            model_contributions=contributions,
            confidence_index=round(conf_idx, 2),
            ensemble_spread=round(spread, 2),
            confidence_interval_10th=round(ci_10, 2) if ci_10 is not None else None,
            confidence_interval_90th=round(ci_90, 2) if ci_90 is not None else None,
            models_available=models_available,
            models_missing=models_missing,
            models_rejected=models_rejected,
            weights_renormalized=weights_renormalized,
            blending_method=method,
            created_at=datetime.now(),
        )

        # 8. Persist into store
        if persist:
            self.store.save_blended_forecast(result)

        return result

    # -------------------------------------------------------------
    # Blending Algorithms
    # -------------------------------------------------------------
    def _blend_linear(
        self,
        norm_var: str,
        valid_forecasts: Dict[str, float],
        renormalized_weights: Dict[str, float],
    ) -> Tuple[float, float, float, Optional[float], Optional[float], List[ModelContribution], BlendingMethod]:
        """
        Executes linear weighted sum: sum(model_forecast * adaptive_weight).
        Computes weighted spread, confidence bounds, and itemized contributions.
        """
        weighted_sum = 0.0
        contributions: List[ModelContribution] = []

        # Calculate weighted sum
        for m, val in valid_forecasts.items():
            w = renormalized_weights[m]
            contrib = val * w
            weighted_sum += contrib

        # Apply physical non-negativity constraint
        if norm_var in ("rainfall", "wind_speed"):
            weighted_sum = max(0.0, weighted_sum)

        total_abs_contrib = sum(abs(valid_forecasts[m] * renormalized_weights[m]) for m in valid_forecasts)
        for m, val in valid_forecasts.items():
            w = renormalized_weights[m]
            contrib = val * w
            pct = (abs(contrib) / total_abs_contrib * 100.0) if total_abs_contrib > 0 else (100.0 / len(valid_forecasts))
            contributions.append(
                ModelContribution(
                    model_name=m,
                    forecast_value=round(val, 2),
                    adaptive_weight=round(w, 4),
                    weighted_contribution=round(contrib, 2),
                    contribution_percentage=round(pct, 2),
                )
            )

        # Weighted variance & ensemble spread
        if len(valid_forecasts) > 1:
            variance = sum(
                renormalized_weights[m] * ((valid_forecasts[m] - weighted_sum) ** 2)
                for m in valid_forecasts
            )
            spread = math.sqrt(variance)
        else:
            spread = 0.0

        # Confidence index: inter-model agreement relative to climatology
        sigma_0 = CLIMATOLOGICAL_SIGMA.get(norm_var, 5.0)
        confidence_idx = max(0.10, min(0.98, math.exp(-spread / sigma_0)))

        # 10th and 90th percentile confidence bounds (approx. +/- 1.28 * spread)
        margin = 1.28 * spread
        ci_10 = weighted_sum - margin
        ci_90 = weighted_sum + margin

        if norm_var in ("rainfall", "wind_speed"):
            ci_10 = max(0.0, ci_10)
            ci_90 = max(0.0, ci_90)

        return weighted_sum, spread, confidence_idx, ci_10, ci_90, contributions, BlendingMethod.LINEAR_WEIGHTED_SUM

    def _blend_wind_direction(
        self,
        valid_forecasts: Dict[str, float],
        renormalized_weights: Dict[str, float],
    ) -> Tuple[float, float, float, Optional[float], Optional[float], List[ModelContribution], BlendingMethod]:
        """
        Executes circular vector averaging for wind direction angles across the [0, 360) circle.
        """
        models = list(valid_forecasts.keys())
        angles = [valid_forecasts[m] for m in models]
        weights = [renormalized_weights[m] for m in models]

        blended_deg, R = circular_mean_degrees(angles, weights)
        spread_deg, conf_idx = circular_dispersion_and_confidence(R)

        contributions: List[ModelContribution] = []
        for m in models:
            w = renormalized_weights[m]
            val = valid_forecasts[m]
            # Directional contribution percentage based on normalized weight
            contributions.append(
                ModelContribution(
                    model_name=m,
                    forecast_value=round(val, 1),
                    adaptive_weight=round(w, 4),
                    weighted_contribution=round(val * w, 2),
                    contribution_percentage=round(w * 100.0, 2),
                )
            )

        # For circular directions, CI bounds wrap circularly
        ci_10 = (blended_deg - spread_deg + 360.0) % 360.0
        ci_90 = (blended_deg + spread_deg) % 360.0

        return blended_deg, spread_deg, conf_idx, ci_10, ci_90, contributions, BlendingMethod.VECTOR_CIRCULAR_AVERAGE

    # -------------------------------------------------------------
    # Validation & Filtering Safeguards
    # -------------------------------------------------------------
    def _validate_and_filter(
        self,
        norm_var: str,
        raw_forecasts: Dict[str, float],
        weights: Dict[str, float],
    ) -> Tuple[Dict[str, float], Dict[str, float], List[str], List[str], List[str], bool]:
        """
        Validates forecasts against physical boundaries, detects missing models,
        and renormalizes available weights to sum strictly to 1.0.
        """
        valid_forecasts: Dict[str, float] = {}
        models_available: List[str] = []
        models_missing: List[str] = []
        models_rejected: List[str] = []

        min_val, max_val = PHYSICAL_LIMITS.get(norm_var, (-1000.0, 1000.0))

        for m, val in raw_forecasts.items():
            if val is None or math.isnan(val) or math.isinf(val):
                models_missing.append(m)
                continue

            # Physical limit bounds check
            if val < min_val or val > max_val:
                logger.warning(
                    "Model '%s' forecast for %s (%.1f) exceeds physical boundaries [%.1f, %.1f]. Rejected.",
                    m, norm_var, val, min_val, max_val
                )
                models_rejected.append(m)
                continue

            valid_forecasts[m] = float(val)
            models_available.append(m)

        if not valid_forecasts:
            raise ValueError(f"No valid model forecasts available for variable '{norm_var}'. All inputs missing or rejected.")

        # Re-normalize weights for available models
        raw_w_sum = sum(weights.get(m, 1.0 / len(raw_forecasts)) for m in models_available)
        renormalized_weights: Dict[str, float] = {}
        weights_renormalized = False

        if raw_w_sum <= 0:
            renormalized_weights = {m: 1.0 / len(models_available) for m in models_available}
            weights_renormalized = True
        else:
            if abs(raw_w_sum - 1.0) > 1e-4 or len(models_available) < len(raw_forecasts):
                weights_renormalized = True
            for m in models_available:
                renormalized_weights[m] = weights.get(m, 1.0 / len(raw_forecasts)) / raw_w_sum

        # Ensure exact 1.0 sum to 4 decimal places
        tot = sum(renormalized_weights.values())
        renormalized_weights = {k: round(v / tot, 4) for k, v in renormalized_weights.items()}
        residual = round(1.0 - sum(renormalized_weights.values()), 4)
        if residual != 0.0:
            top_k = max(renormalized_weights.keys(), key=lambda k: renormalized_weights[k])
            renormalized_weights[top_k] = round(renormalized_weights[top_k] + residual, 4)

        return (
            valid_forecasts,
            renormalized_weights,
            models_available,
            models_missing,
            models_rejected,
            weights_renormalized,
        )

    def _validate_alignment(
        self,
        target_lat: float,
        target_lon: float,
        target_time: datetime,
        model_coordinates: Optional[Dict[str, Tuple[float, float]]] = None,
        model_timestamps: Optional[Dict[str, datetime]] = None,
        spatial_tolerance_deg: float = 0.15,
        temporal_tolerance_seconds: float = 3600.0,
    ):
        """
        Validates that all input forecasts correspond to the same target point and valid time.
        """
        if model_coordinates:
            for m, (lat, lon) in model_coordinates.items():
                dist = math.sqrt((lat - target_lat) ** 2 + (lon - target_lon) ** 2)
                if dist > spatial_tolerance_deg:
                    raise ValueError(
                        f"Spatial alignment error for model '{m}': coordinate ({lat:.2f}, {lon:.2f}) "
                        f"differs from target ({target_lat:.2f}, {target_lon:.2f}) by {dist:.3f}° > tolerance {spatial_tolerance_deg}°."
                    )

        if model_timestamps:
            for m, t in model_timestamps.items():
                delta = abs((t - target_time).total_seconds())
                if delta > temporal_tolerance_seconds:
                    raise ValueError(
                        f"Temporal alignment error for model '{m}': timestamp {t} "
                        f"differs from target {target_time} by {delta:.0f}s > tolerance {temporal_tolerance_seconds:.0f}s."
                    )

    # -------------------------------------------------------------
    # Location & Forecast Resolvers
    # -------------------------------------------------------------
    def _resolve_location(
        self,
        station_id: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Tuple[float, float, str, Optional[str]]:
        if station_id:
            sid = station_id.upper().strip()
            if sid in REFERENCE_STATIONS:
                st = REFERENCE_STATIONS[sid]
                return st.lat, st.lon, st.name, sid
            raise ValueError(f"Unknown station ID '{station_id}'.")
        elif latitude is not None and longitude is not None:
            return latitude, longitude, f"Coord ({latitude:.2f}N, {longitude:.2f}E)", None
        else:
            # Default to Mumbai
            st = REFERENCE_STATIONS["BOM"]
            return st.lat, st.lon, st.name, "BOM"

    def _resolve_model_forecasts(
        self,
        norm_var: str,
        target_lat: float,
        target_lon: float,
        lead_time_hours: int,
        explicit_forecasts: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        if explicit_forecasts:
            return dict(explicit_forecasts)

        # Retrieve forecasts from simulated operational provider
        var_map = {
            "rainfall": WeatherVariable.PRECIPITATION,
            "temperature": WeatherVariable.TEMPERATURE_2M,
            "wind_speed": WeatherVariable.WIND_SPEED_10M,
        }
        if norm_var in var_map:
            wv = var_map[norm_var]
            point_forecasts = self.provider.get_point_forecast(target_lat, target_lon, wv, [lead_time_hours])
            return {m: point_forecasts[m][lead_time_hours] for m in point_forecasts}
        elif norm_var == "wind_direction":
            # Physically grounded wind direction for Indian subcontinental monsoon
            base_dir = (235.0 + 15.0 * math.sin(target_lat * 0.5)) % 360.0
            return {
                "gfs": round((base_dir - 5.0) % 360.0, 1),
                "ecmwf": round(base_dir, 1),
                "graphcast": round((base_dir + 4.0) % 360.0, 1),
                "pangu": round((base_dir + 2.0) % 360.0, 1),
            }
        return {"gfs": 25.0, "ecmwf": 25.0}

    def _resolve_model_weights(
        self,
        models: List[str],
        norm_var: str,
        lead_time_hours: int,
        region: Optional[str],
        weather_regime: Optional[str],
        explicit_weights: Optional[Dict[str, float]],
    ) -> Dict[str, float]:
        if explicit_weights:
            tot = sum(explicit_weights.values())
            if tot > 0:
                return {k: v / tot for k, v in explicit_weights.items()}
            return {k: 1.0 / len(explicit_weights) for k in explicit_weights}

        # Query AdaptiveWeightEngine
        weight_out = self.weight_engine.calculate_weights(
            models=models,
            variable=norm_var,
            lead_time_hours=lead_time_hours,
            region=region,
            weather_regime=weather_regime,
        )
        return weight_out.normalized_weights

    def _normalize_variable(self, var: Union[WeatherVariable, str]) -> str:
        s = var.value if isinstance(var, WeatherVariable) else str(var).lower().strip()
        if "rain" in s or "precip" in s:
            return "rainfall"
        if "temp" in s:
            return "temperature"
        if "wind_dir" in s or "direction" in s:
            return "wind_direction"
        if "wind" in s:
            return "wind_speed"
        return "temperature"
