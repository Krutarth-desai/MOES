from datetime import datetime
from typing import List, Optional, Tuple
from backend.app.services.regime.base import BaseWeatherRegimeClassifier, WeatherRegimeClassifier
from backend.app.services.regime.schemas import (
    RegimeClassificationResult,
    RegimeType,
    WeatherContext,
)


class RuleBasedRegimeClassifier(WeatherRegimeClassifier):
    """
    Deterministic Rule-Based Weather Regime Classifier.
    Applies official meteorological decision rules (IMD criteria) to classify atmospheric
    situations using temperature, rainfall, humidity, wind speed, pressure, recent rainfall,
    and forecast tendencies.
    """

    @property
    def classifier_name(self) -> str:
        return "Deterministic-RuleBased-v1.0 (IMD Standard Criteria)"

    def classify(self, context: WeatherContext) -> RegimeClassificationResult:
        t = context.temperature
        r = context.rainfall
        w = context.wind_speed
        h = context.humidity
        p = context.pressure
        recent_r = context.recent_rainfall or 0.0
        trends = context.forecast_trends or {}
        elev = context.elevation_m or 100.0
        is_hills = elev >= 1000.0

        p_trend = trends.get("pressure_tendency_12h", 0.0)
        t_trend = trends.get("temp_trend_24h", 0.0)

        # ---------------------------------------------------------
        # Rule 1: Heavy Rain Regime
        # IMD Heavy Rain: >= 64.5 mm/24h, or >= 35 mm on saturated ground
        # ---------------------------------------------------------
        if r >= 64.5 or (r >= 35.0 and recent_r >= 100.0):
            indicators = []
            if r >= 204.5:
                indicators.append(f"Cumulative rainfall {r:.1f} mm exceeds IMD Extremely Heavy Rainfall threshold (204.5 mm)")
                severity = "EXTREME"
                confidence = min(0.98, 0.88 + (r - 204.5) * 0.0005)
            elif r >= 115.6:
                indicators.append(f"Cumulative rainfall {r:.1f} mm exceeds IMD Very Heavy Rainfall threshold (115.6 mm)")
                severity = "SEVERE"
                confidence = min(0.96, 0.85 + (r - 115.6) * 0.001)
            else:
                indicators.append(f"Cumulative rainfall {r:.1f} mm meets IMD Heavy Rainfall criterion (64.5 mm)")
                severity = "MODERATE"
                confidence = min(0.92, 0.80 + (r - 64.5) * 0.002)

            if recent_r >= 80.0:
                indicators.append(f"Antecedent 7-day rainfall of {recent_r:.1f} mm indicates elevated soil moisture saturation")
            if h is not None and h >= 85.0:
                indicators.append(f"High relative humidity ({h:.1f}%) sustaining persistent deep convective cloud cover")

            # Check co-occurring high wind
            secondary = RegimeType.HIGH_WIND if w >= 45.0 else None

            return RegimeClassificationResult(
                regime=RegimeType.HEAVY_RAIN,
                regime_name=RegimeType.HEAVY_RAIN.value,
                confidence=round(confidence, 2),
                supporting_indicators=indicators,
                secondary_regime=secondary,
                severity_level=severity,
                description="Active Heavy Rain Regime with IMD threshold exceedance",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 2: Convective / Severe Storm Regime
        # Rapid convective initiation: rain + squall + pressure drop or cold pool
        # ---------------------------------------------------------
        is_convective_rain_wind = (r >= 20.0 and w >= 40.0)
        is_pressure_drop_squall = (p_trend <= -2.5 and w >= 38.0)
        is_cold_pool_outflow = (t_trend <= -4.0 and r >= 12.0 and w >= 35.0)
        is_pre_convective = (t >= 35.0 and (h is not None and h >= 70.0) and w >= 35.0)

        if is_convective_rain_wind or is_pressure_drop_squall or is_cold_pool_outflow or is_pre_convective:
            indicators = []
            if is_convective_rain_wind:
                indicators.append(f"Convective signature: intense localized precipitation ({r:.1f} mm) coupled with squally wind ({w:.1f} km/h)")
            if is_pressure_drop_squall:
                indicators.append(f"Rapid 12h barometric pressure fall ({p_trend:+.1f} hPa) indicates vigorous mesoscale convective deepening")
            if is_cold_pool_outflow:
                indicators.append(f"Abrupt 24h thermal plunge ({t_trend:+.1f} °C) indicates cold-pool thunderstorm outflow boundary")
            if is_pre_convective:
                indicators.append(f"High pre-convective thermodynamic instability: temperature {t:.1f} °C with high moisture ({h:.1f}% RH)")

            confidence = 0.88 if is_pressure_drop_squall or is_convective_rain_wind else 0.82
            severity = "SEVERE" if (w >= 60.0 or r >= 40.0) else "MODERATE"

            return RegimeClassificationResult(
                regime=RegimeType.CONVECTIVE_STORM,
                regime_name=RegimeType.CONVECTIVE_STORM.value,
                confidence=confidence,
                supporting_indicators=indicators,
                secondary_regime=RegimeType.HIGH_WIND if w >= 50.0 else None,
                severity_level=severity,
                description="Severe Convective / Thunderstorm Regime with squall line indicators",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 3: Heat Wave Regime
        # Plains: >= 40°C with rising trend or dry air, or >= 45°C
        # Hills: >= 30°C
        # ---------------------------------------------------------
        is_plains_heatwave = (not is_hills) and (
            t >= 45.0 or (t >= 40.0 and (t_trend >= 1.0 or (h is not None and h <= 40.0) or t >= 42.0))
        )
        is_hills_heatwave = is_hills and (t >= 30.0)

        if is_plains_heatwave or is_hills_heatwave:
            indicators = []
            if t >= 47.0:
                indicators.append(f"Extreme surface temperature ({t:.1f} °C) exceeds IMD Severe Heatwave criteria (47.0 °C)")
                severity = "EXTREME"
                confidence = min(0.98, 0.90 + (t - 47.0) * 0.02)
            elif t >= 45.0:
                indicators.append(f"Maximum surface temperature ({t:.1f} °C) reaches IMD Heatwave threshold (45.0 °C)")
                severity = "SEVERE"
                confidence = min(0.95, 0.85 + (t - 45.0) * 0.03)
            elif is_hills_heatwave:
                indicators.append(f"High altitude temperature ({t:.1f} °C at {elev:.0f}m) exceeds hill station heatwave criteria (30.0 °C)")
                severity = "MODERATE"
                confidence = 0.88
            else:
                indicators.append(f"Plains temperature ({t:.1f} °C) exceeds 40.0 °C under dry subsiding airflow")
                severity = "MODERATE"
                confidence = min(0.90, 0.78 + (t - 40.0) * 0.03)

            if h is not None and h <= 30.0:
                indicators.append(f"Very low relative humidity ({h:.1f}%) exacerbating atmospheric sensible heat loading")
            if t_trend >= 1.5:
                indicators.append(f"Rising 24h temperature trend ({t_trend:+.1f} °C) indicates strengthening thermal ridge")

            return RegimeClassificationResult(
                regime=RegimeType.HEAT_WAVE,
                regime_name=RegimeType.HEAT_WAVE.value,
                confidence=round(confidence, 2),
                supporting_indicators=indicators,
                secondary_regime=RegimeType.DRY_EXTREME_DRY if (h is not None and h <= 20.0) else None,
                severity_level=severity,
                description="Synoptic Heat Wave Regime with elevated temperature anomaly",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 4: High Wind Regime
        # Sustained surface winds >= 48 km/h (~26 knots)
        # ---------------------------------------------------------
        if w >= 48.0:
            indicators = [
                f"Sustained surface wind speed ({w:.1f} km/h) exceeds IMD gale-force threshold (48.0 km/h)"
            ]
            if w >= 75.0:
                indicators.append("Cyclonic storm force wind gusts threatening structural stability")
                severity = "EXTREME"
                confidence = min(0.98, 0.90 + (w - 75.0) * 0.003)
            elif w >= 60.0:
                indicators.append("Rough coastal sea state and strong inland squalls")
                severity = "SEVERE"
                confidence = min(0.94, 0.84 + (w - 60.0) * 0.005)
            else:
                severity = "MODERATE"
                confidence = min(0.90, 0.80 + (w - 48.0) * 0.008)

            return RegimeClassificationResult(
                regime=RegimeType.HIGH_WIND,
                regime_name=RegimeType.HIGH_WIND.value,
                confidence=round(confidence, 2),
                supporting_indicators=indicators,
                secondary_regime=None,
                severity_level=severity,
                description="High Wind / Squall Regime with gale-force surface winds",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 5: Cold Spell Regime
        # Plains <= 7°C or drop <= -4°C, Hills <= 0°C
        # ---------------------------------------------------------
        is_plains_cold = (not is_hills) and (t <= 7.0 or (t <= 11.0 and t_trend <= -4.0))
        is_hills_cold = is_hills and (t <= 0.0 or (t <= 4.0 and t_trend <= -3.5))

        if is_plains_cold or is_hills_cold:
            indicators = []
            if (not is_hills and t <= 4.0) or (is_hills and t <= -4.0):
                indicators.append(f"Severe cold wave condition: temperature {t:.1f} °C")
                severity = "SEVERE"
                confidence = 0.92
            else:
                indicators.append(f"Temperature ({t:.1f} °C) meets IMD Cold Spell criteria")
                severity = "MODERATE"
                confidence = 0.85

            if t_trend <= -3.0:
                indicators.append(f"Post-frontal cold air advection with sharp 24h plunge ({t_trend:+.1f} °C)")

            return RegimeClassificationResult(
                regime=RegimeType.COLD_SPELL,
                regime_name=RegimeType.COLD_SPELL.value,
                confidence=confidence,
                supporting_indicators=indicators,
                secondary_regime=None,
                severity_level=severity,
                description="Cold Spell / Winter Surge Regime with suppressed minimum temperatures",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 6: Dry / Extreme Dry Regime
        # Rain 0, antecedent rain near 0, low humidity, warm
        # ---------------------------------------------------------
        is_extreme_dry = (
            r == 0.0
            and recent_r <= 2.0
            and ((h is not None and h <= 25.0) or (t >= 32.0 and recent_r == 0.0 and (h is None or h <= 35.0)))
        )

        if is_extreme_dry:
            indicators = [
                f"Prolonged absence of precipitation (recent cumulative: {recent_r:.1f} mm)"
            ]
            if h is not None and h <= 25.0:
                indicators.append(f"Atmospheric moisture deficit with relative humidity down to {h:.1f}%")
            if t >= 32.0:
                indicators.append(f"Warm daytime temperature ({t:.1f} °C) elevating vapor pressure deficit")

            return RegimeClassificationResult(
                regime=RegimeType.DRY_EXTREME_DRY,
                regime_name=RegimeType.DRY_EXTREME_DRY.value,
                confidence=0.86,
                supporting_indicators=indicators,
                secondary_regime=None,
                severity_level="MODERATE",
                description="Dry / Atmospheric Deficit Regime with acute moisture depletion",
                diagnosed_at=datetime.now(),
            )

        # ---------------------------------------------------------
        # Rule 7: Normal Baseline Regime
        # None of the anomalous criteria were met
        # ---------------------------------------------------------
        return RegimeClassificationResult(
            regime=RegimeType.NORMAL,
            regime_name=RegimeType.NORMAL.value,
            confidence=0.90,
            supporting_indicators=[
                f"Surface temperature ({t:.1f} °C) within normal seasonal range",
                f"Rainfall ({r:.1f} mm) is negligible or within non-hazardous threshold",
                f"Wind speed ({w:.1f} km/h) below squall threshold",
                "No severe convective triggers or synoptic hazard anomalies detected",
            ],
            secondary_regime=None,
            severity_level="NORMAL",
            description="Normal Seasonal Atmospheric Regime with benign conditions",
            diagnosed_at=datetime.now(),
        )

    def classify_spatial(self, contexts: List[WeatherContext]) -> List[RegimeClassificationResult]:
        return [self.classify(ctx) for ctx in contexts]
