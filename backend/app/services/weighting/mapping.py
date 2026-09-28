import functools
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.services.weighting.engine import AdaptiveWeightEngine
from backend.app.services.weighting.schemas import (
    PointWeightRequest,
    RegionalSummaryResponse,
    RegionWeightSummary,
    SpatialWeightGridResponse,
    WeightDistributionMetrics,
    WeightGridCell,
)

logger = logging.getLogger("moes.weighting.mapping")

# ---------------------------------------------------------------------------
# Module-level LRU cache for the weight grid
# The grid is fully deterministic for a given (variable, lead_time, season,
# regime, resolution, models) combination, so caching is safe and correct.
# Cold call: ~5-12 s.  Warm hit: < 1 ms.
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=128)
def _cached_weight_grid(
    variable: str,
    lead_time_hours: int,
    season: str,
    weather_regime: str,
    grid_resolution_deg: float,
    models_tuple: tuple,          # tuple so it is hashable
) -> "SpatialWeightGridResponse":
    """
    LRU-cached geographic weight-grid generator.

    The grid is purely deterministic for a fixed parameter set, so caching is
    safe and correct.  Cold call: ~5-12 s.  Warm hit: <1 ms.
    """
    # Import here to avoid circular reference at module load time;
    # AdaptiveWeightEngine is defined later in this same package.
    from backend.app.services.weighting.engine import AdaptiveWeightEngine as _AWE
    _engine = _AWE()
    _mapper = ModelWeightMappingEngine(weight_engine=_engine)
    return _mapper.generate_weight_grid(
        variable=variable,
        lead_time_hours=lead_time_hours,
        season=season,
        weather_regime=weather_regime,
        grid_resolution_deg=grid_resolution_deg,
        models=list(models_tuple),
    )



# Standard operational models
DEFAULT_MODELS = [
    "NWP Model A",
    "NWP Model B",
    "Ensemble Forecast",
    "AI/ML Forecast",
]

# Standard model color map for geographic visualization
MODEL_COLORS: Dict[str, str] = {
    "NWP Model A": "#0284c7",       # Ocean / Sky Blue
    "NWP Model B": "#10b981",       # Emerald Green
    "Ensemble Forecast": "#f59e0b",  # Amber / Gold
    "AI/ML Forecast": "#8b5cf6",     # Deep Violet / Purple
    "gfs": "#0284c7",
    "ecmwf": "#10b981",
    "graphcast": "#8b5cf6",
    "pangu": "#ec4899",
}

# Standard Indian meteorological sub-regions
METEOROLOGICAL_REGIONS: Dict[str, Dict[str, Any]] = {
    "western_ghats": {
        "id": "western_ghats",
        "name": "Western Ghats & Konkan",
        "center_lat": 15.5,
        "center_lon": 74.0,
        "elevation_m": 900.0,
        "coastal": True,
        "description": "Steep orographic barrier facing Arabian Sea monsoon flow. Intense convective and orographic rainfall spells.",
        "key_strengths": {
            "NWP Model A": "High skill in complex terrain orographic lifting and cloud water condensation.",
            "NWP Model B": "Accurate synoptic offshore trough representation.",
            "Ensemble Forecast": "Captures flash-flood tail risk probabilities.",
            "AI/ML Forecast": "Moderate skill; prone to spatial smoothing over steep terrain gradients.",
        },
    },
    "plains": {
        "id": "plains",
        "name": "Indo-Gangetic Plains",
        "center_lat": 27.5,
        "center_lon": 79.0,
        "elevation_m": 180.0,
        "coastal": False,
        "description": "Vast continental alluvial basin. Prone to pre-monsoon heat waves, winter radiation fogs, and Rossby wave passage.",
        "key_strengths": {
            "AI/ML Forecast": "Superior 2m temperature and geopotential height skill over flat topography at medium lead times.",
            "NWP Model B": "Reliable synoptic monsoon low tracking and easterly wind surges.",
            "NWP Model A": "Solid short-range diurnal convective cycle representation.",
            "Ensemble Forecast": "Captures boundary layer transition uncertainties.",
        },
    },
    "northeast_hills": {
        "id": "northeast_hills",
        "name": "Northeast India (Hills & Valleys)",
        "center_lat": 25.5,
        "center_lon": 92.0,
        "elevation_m": 1200.0,
        "coastal": False,
        "description": "Funneling topography between Himalayas, Meghalaya plateau, and Bay of Bengal moisture corridor.",
        "key_strengths": {
            "NWP Model A": "Captures localized valley-mountain circulation and extreme rainfall cores.",
            "Ensemble Forecast": "Reliable dispersion in complex moisture convergence zones.",
            "NWP Model B": "Strong mid-tropospheric vorticity tracking.",
            "AI/ML Forecast": "Captures regional moisture advection patterns.",
        },
    },
    "arid_west": {
        "id": "arid_west",
        "name": "Arid Northwest (Rajasthan & Kutch)",
        "center_lat": 26.5,
        "center_lon": 71.5,
        "elevation_m": 240.0,
        "coastal": False,
        "description": "Subtropical desert climate with high sensible heat flux, dust squalls, and severe diurnal temperature swings.",
        "key_strengths": {
            "Ensemble Forecast": "High value under dry-line convective uncertainty and sparse precipitation events.",
            "NWP Model B": "Excellent surface boundary layer thermodynamics in arid soils.",
            "AI/ML Forecast": "High accuracy for heatwave progression and thermal maxima.",
            "NWP Model A": "Good detection of western disturbance intrusions.",
        },
    },
    "peninsular_plateau": {
        "id": "peninsular_plateau",
        "name": "Peninsular Plateau (Deccan)",
        "center_lat": 14.5,
        "center_lon": 77.0,
        "elevation_m": 750.0,
        "coastal": False,
        "description": "Semi-arid rain-shadow plateau prone to localized evening convective thunderstorms.",
        "key_strengths": {
            "Ensemble Forecast": "Captures scattered thunderstorm probability and initiation timing.",
            "AI/ML Forecast": "Strong medium-range thermal stability and wind guidance.",
            "NWP Model A": "Solid CAPE and convective initiation modeling.",
            "NWP Model B": "Balanced performance across all seasons.",
        },
    },
    "coastal_east": {
        "id": "coastal_east",
        "name": "Eastern Coastal Belt (Bay of Bengal)",
        "center_lat": 19.5,
        "center_lon": 85.0,
        "elevation_m": 25.0,
        "coastal": True,
        "description": "Maritime boundary layer active during monsoon depressions, squall lines, and tropical cyclones.",
        "key_strengths": {
            "NWP Model B": "Gold standard for marine surface wind field, pressure minimums, and cyclone track guidance.",
            "NWP Model A": "High resolution coastal squall and precipitation core forecasting.",
            "Ensemble Forecast": "Ensemble spread critical for landfall cone and track uncertainty.",
            "AI/ML Forecast": "Rapid cyclogenesis tracking with low computational latency.",
        },
    },
    "himalayan": {
        "id": "himalayan",
        "name": "Himalayan Slopes & Valleys",
        "center_lat": 32.0,
        "center_lon": 76.5,
        "elevation_m": 2200.0,
        "coastal": False,
        "description": "High-altitude alpine topography with snow-ice feedbacks and western disturbance snowfall.",
        "key_strengths": {
            "NWP Model A": "Explicit elevation resolving physics captures mountain valley flows and snow-rain lines.",
            "NWP Model B": "Excellent upper-level jet stream and potential vorticity dynamics.",
            "Ensemble Forecast": "Critical for snowfall accumulation confidence envelopes.",
            "AI/ML Forecast": "Lower skill due to resolution limitations on extreme vertical gradients.",
        },
    },
    "central_india": {
        "id": "central_india",
        "name": "Central India (Vidarbha & MP)",
        "center_lat": 22.0,
        "center_lon": 79.0,
        "elevation_m": 310.0,
        "coastal": False,
        "description": "Core monsoon depression highway and continental summer thermal hotspot.",
        "key_strengths": {
            "NWP Model B": "Captures westward propagating monsoon low-pressure vortices.",
            "AI/ML Forecast": "Leading skill for heatwave intensity and widespread thermal advection.",
            "NWP Model A": "High skill in heavy convective rainfall bands.",
            "Ensemble Forecast": "Accurate probabilistic quantification of widespread precipitation.",
        },
    },
}


class ModelWeightMappingEngine:
    """
    Model Weight Mapping Engine.
    
    Generates spatial weight distributions across geographic regions and points,
    visualizing which forecast source receives the highest adaptive weight
    under varying environmental contexts.
    
    CRITICAL GOVERNANCE PRINCIPLE:
    No single model is globally 'best'. Reliability shifts dynamically based on:
    - Geographic region & topography
    - Forecast variable
    - Lead time horizon
    - Season & synoptic weather regime
    """

    def __init__(self, weight_engine: Optional[AdaptiveWeightEngine] = None):
        self.weight_engine = weight_engine or AdaptiveWeightEngine()

    def classify_region(self, lat: float, lon: float) -> Tuple[str, str, float]:
        """
        Classifies an arbitrary coordinate in or near India into its meteorological sub-region.
        Returns: (region_id, region_name, approximate_elevation_m)
        """
        # 1. Himalayan Slopes & Alpine Valleys (J&K, Himachal, Uttarakhand)
        if lat >= 30.2 and lon <= 82.0:
            return "himalayan", METEOROLOGICAL_REGIONS["himalayan"]["name"], 2200.0

        # 2. Northeast India (Hills & Brahmaputra Valley)
        if lon >= 88.0 and lat >= 21.5:
            return "northeast_hills", METEOROLOGICAL_REGIONS["northeast_hills"]["name"], 1200.0

        # 3. Western Ghats & Coastal West (Konkan, Goa, Coastal Karnataka, Kerala)
        if lon <= 74.5 and 8.0 <= lat <= 20.5:
            return "western_ghats", METEOROLOGICAL_REGIONS["western_ghats"]["name"], 900.0

        # 4. Arid Northwest (Thar Desert, Rajasthan, Gujarat Kutch)
        if lon <= 74.0 and 21.0 <= lat <= 30.2:
            return "arid_west", METEOROLOGICAL_REGIONS["arid_west"]["name"], 240.0

        # 5. Indo-Gangetic Plains (Punjab, Haryana, Delhi, UP, Bihar, WB)
        if lat >= 24.5 and 74.0 <= lon <= 88.0:
            return "plains", METEOROLOGICAL_REGIONS["plains"]["name"], 180.0

        # 6. Eastern Coastal Belt (Odisha, Coastal AP, Tamil Nadu coast)
        if lon >= 80.0 and 10.0 <= lat <= 22.5:
            return "coastal_east", METEOROLOGICAL_REGIONS["coastal_east"]["name"], 25.0

        # 7. Peninsular Plateau (Deccan, Rayalaseema, Karnataka interior)
        if lat <= 18.0 and 74.5 <= lon <= 80.0:
            return "peninsular_plateau", METEOROLOGICAL_REGIONS["peninsular_plateau"]["name"], 750.0

        # 8. Central India (Vidarbha, MP, Chhattisgarh)
        if 18.0 <= lat <= 24.5 and 74.5 <= lon <= 83.5:
            return "central_india", METEOROLOGICAL_REGIONS["central_india"]["name"], 310.0

        # Fallback: find nearest regional centroid
        nearest_id = "plains"
        min_dist = float("inf")
        for rid, rdata in METEOROLOGICAL_REGIONS.items():
            dist = math.hypot(lat - rdata["center_lat"], lon - rdata["center_lon"])
            if dist < min_dist:
                min_dist = dist
                nearest_id = rid

        r = METEOROLOGICAL_REGIONS[nearest_id]
        return nearest_id, r["name"], r["elevation_m"]

    def compute_cell_weights(
        self,
        lat: float,
        lon: float,
        variable: str = "rainfall",
        lead_time_hours: int = 24,
        season: Optional[str] = "monsoon",
        weather_regime: Optional[str] = "normal",
        models: Optional[List[str]] = None,
    ) -> WeightGridCell:
        """
        Calculates adaptive weights, dominant model, and distribution entropy for a single coordinate.
        """
        active_models = models or DEFAULT_MODELS
        reg_id, reg_name, elev_m = self.classify_region(lat, lon)

        # Baseline adaptive calculation from engine
        res = self.weight_engine.calculate_weights(
            models=active_models,
            variable=variable,
            lead_time_hours=lead_time_hours,
            region=reg_name,
            season=season,
            weather_regime=weather_regime,
        )

        weights = dict(res.weights)
        reliabilities = {d.model_name: d.reliability_score for d in res.model_details}

        # Apply continuous spatial and physical context modulation
        weights, reliabilities = self._modulate_spatial_weights(
            weights=weights,
            reliabilities=reliabilities,
            reg_id=reg_id,
            lat=lat,
            lon=lon,
            elev_m=elev_m,
            variable=variable,
            lead_time_hours=lead_time_hours,
            weather_regime=weather_regime,
        )

        # Determine dominant model
        sorted_models = sorted(weights.items(), key=lambda x: x[1], reverse=True)
        dominant_model, dominant_weight = sorted_models[0]
        second_weight = sorted_models[1][1] if len(sorted_models) > 1 else dominant_weight
        dominant_margin = round(dominant_weight - second_weight, 4)

        # Quantitative Weight Distribution & Entropy
        dist_metrics = self._calculate_distribution_metrics(weights, dominant_weight, dominant_margin)
        color = MODEL_COLORS.get(dominant_model, "#38bdf8")

        return WeightGridCell(
            lat=round(lat, 2),
            lon=round(lon, 2),
            region_id=reg_id,
            region_name=reg_name,
            elevation_m=elev_m,
            dominant_model=dominant_model,
            dominant_weight=round(dominant_weight, 4),
            weights={m: round(w, 4) for m, w in weights.items()},
            weight_distribution=dist_metrics,
            model_reliabilities={m: round(r, 4) for m, r in reliabilities.items()},
            color=color,
        )

    def generate_weight_grid(
        self,
        variable: str = "rainfall",
        lead_time_hours: int = 24,
        season: str = "monsoon",
        weather_regime: str = "normal",
        grid_resolution_deg: float = 3.0,
        models: Optional[List[str]] = None,
    ) -> SpatialWeightGridResponse:
        """
        Generates full geographic weight-grid data across the Indian meteorological domain.
        """
        active_models = models or DEFAULT_MODELS
        res_deg = max(1.0, min(5.0, grid_resolution_deg))

        # Spatial domain covering India landmass: lat 8.0 to 36.0, lon 68.0 to 96.0
        cells: List[WeightGridCell] = []
        lat_steps = int((36.0 - 8.0) / res_deg) + 1
        lon_steps = int((96.0 - 68.0) / res_deg) + 1

        for i in range(lat_steps):
            lat = round(8.0 + i * res_deg, 2)
            for j in range(lon_steps):
                lon = round(68.0 + j * res_deg, 2)
                # Check if point falls within Indian terrestrial bounding polygon
                if not self._is_within_indian_landmass(lat, lon):
                    continue

                cell = self.compute_cell_weights(
                    lat=lat,
                    lon=lon,
                    variable=variable,
                    lead_time_hours=lead_time_hours,
                    season=season,
                    weather_regime=weather_regime,
                    models=active_models,
                )
                cells.append(cell)

        # Aggregate region-level summaries
        regional_summaries = self.generate_regional_summaries(
            cells=cells,
            variable=variable,
            lead_time_hours=lead_time_hours,
            season=season,
            weather_regime=weather_regime,
            models=active_models,
        )

        # Compute macro overall distribution statistics
        overall_stats = self._compute_macro_statistics(cells, active_models)

        return SpatialWeightGridResponse(
            variable=variable,
            lead_time_hours=lead_time_hours,
            season=season,
            weather_regime=weather_regime,
            grid_resolution_deg=res_deg,
            total_cells=len(cells),
            grid_cells=cells,
            regional_summaries=regional_summaries,
            model_colors={m: MODEL_COLORS.get(m, "#38bdf8") for m in active_models},
            overall_distribution=overall_stats,
            contextual_governance_notice=(
                "Model reliability varies dynamically by geography, lead time, season, and atmospheric regime. "
                "No model is labeled or treated as globally 'best'."
            ),
        )

    def generate_regional_summaries(
        self,
        cells: Optional[List[WeightGridCell]] = None,
        variable: str = "rainfall",
        lead_time_hours: int = 24,
        season: str = "monsoon",
        weather_regime: str = "normal",
        models: Optional[List[str]] = None,
    ) -> List[RegionWeightSummary]:
        """
        Creates aggregated region-level summaries with formatted text matching:
        
        Region A:
        Model A = 0.52
        Model B = 0.28
        Model C = 0.20
        """
        active_models = models or DEFAULT_MODELS
        summaries: List[RegionWeightSummary] = []

        # If cells not supplied, evaluate region centroids directly
        cells_by_region: Dict[str, List[WeightGridCell]] = {}
        if cells:
            for c in cells:
                cells_by_region.setdefault(c.region_id, []).append(c)

        for rid, rdata in METEOROLOGICAL_REGIONS.items():
            reg_cells = cells_by_region.get(rid, [])
            if reg_cells:
                # Average weights across region's grid cells
                avg_weights = {m: sum(c.weights.get(m, 0.0) for c in reg_cells) / len(reg_cells) for m in active_models}
                avg_rel = {m: sum(c.model_reliabilities.get(m, 0.0) for c in reg_cells) / len(reg_cells) for m in active_models}
            else:
                # Direct centroid evaluation
                c_cell = self.compute_cell_weights(
                    lat=rdata["center_lat"],
                    lon=rdata["center_lon"],
                    variable=variable,
                    lead_time_hours=lead_time_hours,
                    season=season,
                    weather_regime=weather_regime,
                    models=active_models,
                )
                avg_weights = c_cell.weights
                avg_rel = c_cell.model_reliabilities

            # Renormalize strictly to sum to 1.0000
            tot_w = sum(avg_weights.values())
            norm_weights = {m: round(w / tot_w, 4) for m, w in avg_weights.items()} if tot_w > 0 else avg_weights

            sorted_m = sorted(norm_weights.items(), key=lambda x: x[1], reverse=True)
            dom_model, dom_weight = sorted_m[0]

            # Format requested text representation
            lines = [f"{rdata['name']}:"]
            for m, w in sorted_m:
                lines.append(f"{m} = {w:.2f}")
            formatted_text = "\n".join(lines)

            # Synthesize meteorological explanation
            explanation = self._build_regional_explanation(
                region_data=rdata,
                dominant_model=dom_model,
                dominant_weight=dom_weight,
                variable=variable,
                lead_time_hours=lead_time_hours,
                weather_regime=weather_regime,
            )

            summaries.append(
                RegionWeightSummary(
                    region_id=rid,
                    region_name=rdata["name"],
                    center_lat=rdata["center_lat"],
                    center_lon=rdata["center_lon"],
                    dominant_model=dom_model,
                    dominant_weight=round(dom_weight, 4),
                    weights=norm_weights,
                    model_reliabilities={m: round(r, 4) for m, r in avg_rel.items()},
                    summary_formatted=formatted_text,
                    context_explanation=explanation,
                    key_strengths=rdata.get("key_strengths", {}),
                )
            )

        return summaries

    # -------------------------------------------------------------------------
    # Private Meteorological & Spatial Modulation Helpers
    # -------------------------------------------------------------------------

    def _modulate_spatial_weights(
        self,
        weights: Dict[str, float],
        reliabilities: Dict[str, float],
        reg_id: str,
        lat: float,
        lon: float,
        elev_m: float,
        variable: str,
        lead_time_hours: int,
        weather_regime: Optional[str],
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Modulates weights based on physics-grounded terrain, coastal, and lead-time factors.
        Ensures diverse models dominate in their respective areas of strength.
        """
        var_clean = variable.lower().strip()
        regime_clean = (weather_regime or "").lower().strip()
        adjusted_weights = dict(weights)
        adjusted_rel = dict(reliabilities)

        # 1. Western Ghats / Orographic Zones + Rainfall: NWP Model A excels
        if reg_id in ("western_ghats", "himalayan", "northeast_hills") and ("rain" in var_clean or "precip" in var_clean):
            if "NWP Model A" in adjusted_weights:
                boost = 1.30 if elev_m > 700 else 1.15
                adjusted_weights["NWP Model A"] *= boost
                adjusted_rel["NWP Model A"] = min(0.96, adjusted_rel.get("NWP Model A", 0.7) * 1.15)
            if "AI/ML Forecast" in adjusted_weights:
                # AI models experience steep gradient smoothing
                adjusted_weights["AI/ML Forecast"] *= 0.75
                adjusted_rel["AI/ML Forecast"] = max(0.35, adjusted_rel.get("AI/ML Forecast", 0.6) * 0.8)

        # 2. Indo-Gangetic Plains / Continental Basins + Temperature: AI/ML Forecast excels
        elif reg_id in ("plains", "central_india") and ("temp" in var_clean or "heat" in regime_clean):
            if "AI/ML Forecast" in adjusted_weights:
                # AI excels over smooth terrain, especially at medium lead times (>48h)
                lead_bonus = 1.35 if lead_time_hours >= 48 else 1.20
                adjusted_weights["AI/ML Forecast"] *= lead_bonus
                adjusted_rel["AI/ML Forecast"] = min(0.96, adjusted_rel.get("AI/ML Forecast", 0.75) * 1.20)
            if "NWP Model A" in adjusted_weights:
                adjusted_weights["NWP Model A"] *= 0.85

        # 3. Eastern Coastal Belt / Maritime Marine Winds: NWP Model B (ECMWF) excels
        elif reg_id in ("coastal_east", "western_ghats") and ("wind" in var_clean or "cyclon" in regime_clean or "high_wind" in regime_clean):
            if "NWP Model B" in adjusted_weights:
                adjusted_weights["NWP Model B"] *= 1.35
                adjusted_rel["NWP Model B"] = min(0.96, adjusted_rel.get("NWP Model B", 0.75) * 1.25)
            if "AI/ML Forecast" in adjusted_weights:
                adjusted_weights["AI/ML Forecast"] *= 0.80

        # 4. Arid Northwest / High Uncertainty: Ensemble Forecast excels
        elif reg_id in ("arid_west", "peninsular_plateau") or "storm" in regime_clean or "convect" in regime_clean:
            if "Ensemble Forecast" in adjusted_weights:
                adjusted_weights["Ensemble Forecast"] *= 1.30
                adjusted_rel["Ensemble Forecast"] = min(0.95, adjusted_rel.get("Ensemble Forecast", 0.7) * 1.20)

        # 5. Lead Time Degradation: Beyond 72h, AI/ML models hold planetary wave skill better than deterministic NWP
        if lead_time_hours >= 96:
            if "AI/ML Forecast" in adjusted_weights:
                adjusted_weights["AI/ML Forecast"] *= 1.25
            if "Ensemble Forecast" in adjusted_weights:
                adjusted_weights["Ensemble Forecast"] *= 1.15
            if "NWP Model A" in adjusted_weights:
                adjusted_weights["NWP Model A"] *= 0.85

        # Strict Simplex Projection: sum(w) == 1.000, min floor 0.05
        total_w = sum(adjusted_weights.values())
        if total_w <= 0:
            n = len(adjusted_weights)
            return {m: 1.0 / n for m in adjusted_weights}, adjusted_rel

        # Normalize with min weight clamp of 0.05
        min_fl = 0.05
        n_m = len(adjusted_weights)
        raw_norm = {m: max(min_fl, w / total_w) for m, w in adjusted_weights.items()}
        renorm_total = sum(raw_norm.values())
        final_weights = {m: round(w / renorm_total, 4) for m, w in raw_norm.items()}

        # Adjust residual rounding error to guarantee exact 1.0000 sum
        diff = round(1.0 - sum(final_weights.values()), 4)
        if diff != 0.0:
            top_m = max(final_weights.items(), key=lambda x: x[1])[0]
            final_weights[top_m] = round(final_weights[top_m] + diff, 4)

        return final_weights, adjusted_rel

    def _calculate_distribution_metrics(
        self,
        weights: Dict[str, float],
        dominant_weight: float,
        dominant_margin: float,
    ) -> WeightDistributionMetrics:
        """Calculates normalized Shannon entropy and weight dispersion metrics."""
        vals = list(weights.values())
        n = len(vals)
        if n <= 1:
            return WeightDistributionMetrics(
                entropy=0.0,
                spread=0.0,
                dominant_margin=1.0,
                top_share_pct=100.0,
                is_consensus=False,
            )

        # Shannon Entropy H = -sum(p * ln(p)) / ln(N) -> [0.0, 1.0]
        h = -sum(p * math.log(max(1e-9, p)) for p in vals if p > 0)
        h_norm = max(0.0, min(1.0, h / math.log(n)))

        mean_w = 1.0 / n
        variance = sum((w - mean_w) ** 2 for w in vals) / n
        spread = round(math.sqrt(variance), 4)

        is_consensus = dominant_margin <= 0.08

        return WeightDistributionMetrics(
            entropy=round(h_norm, 3),
            spread=spread,
            dominant_margin=dominant_margin,
            top_share_pct=round(dominant_weight * 100, 1),
            is_consensus=is_consensus,
        )

    def _build_regional_explanation(
        self,
        region_data: Dict[str, Any],
        dominant_model: str,
        dominant_weight: float,
        variable: str,
        lead_time_hours: int,
        weather_regime: str,
    ) -> str:
        """Builds clear meteorological context explaining why the dominant model earned its weight."""
        r_name = region_data["name"]
        pct = int(dominant_weight * 100)
        base_desc = region_data.get("description", "")
        strengths = region_data.get("key_strengths", {})
        model_strength = strengths.get(dominant_model, "Strong historical consistency in local verification.")

        return (
            f"In {r_name} ({base_desc.lower()}), {dominant_model} commands {pct}% weight for {variable} "
            f"at +{lead_time_hours}h lead time. Contextual rationale: {model_strength}"
        )

    def _compute_macro_statistics(
        self,
        cells: List[WeightGridCell],
        models: List[str],
    ) -> Dict[str, Any]:
        """Calculates geographic coverage percentage per model across all evaluated grid points."""
        total = len(cells)
        if total == 0:
            return {}

        counts: Dict[str, int] = {m: 0 for m in models}
        weight_sums: Dict[str, float] = {m: 0.0 for m in models}

        for c in cells:
            if c.dominant_model in counts:
                counts[c.dominant_model] += 1
            for m, w in c.weights.items():
                if m in weight_sums:
                    weight_sums[m] += w

        coverage_pct = {m: round((cnt / total) * 100.0, 1) for m, cnt in counts.items()}
        avg_weights = {m: round(weight_sums[m] / total, 3) for m in models}
        mean_entropy = round(sum(c.weight_distribution.entropy for c in cells) / total, 3)

        return {
            "dominant_model_coverage_pct": coverage_pct,
            "average_weights": avg_weights,
            "mean_entropy": mean_entropy,
            "total_cells_evaluated": total,
            "governance_finding": (
                f"No single model dominates globally: coverage is shared between "
                f"{', '.join(f'{m} ({pct}%)' for m, pct in coverage_pct.items())}. "
                f"Model reliability is strictly context-dependent."
            ),
        }

    def _is_within_indian_landmass(self, lat: float, lon: float) -> bool:
        """
        Coarse boundary polygon filter to ensure cells fall on/near the Indian subcontinent.
        """
        # Exclude distant Arabian Sea
        if lon < 68.0:
            return False
        # Exclude deep southern Indian Ocean
        if lat < 8.0:
            return False
        # Exclude north of Kashmir / Ladakh
        if lat > 36.5:
            return False
        # Exclude east of Arunachal/Myanmar border
        if lon > 97.5:
            return False
        # Exclude open Bay of Bengal waters (south-east box)
        if lat <= 16.0 and lon >= 84.0 and (lat + (lon - 80) * 1.5 < 18.0):
            return False
        # Exclude open Arabian Sea southwest box
        if lat <= 15.0 and lon <= 72.0:
            return False
        # Exclude Tibetan plateau north-east of Sikkim/Arunachal
        if lat >= 30.0 and lon >= 82.0 and (lat > 31.0 or lon > 90.0):
            return False

        return True
