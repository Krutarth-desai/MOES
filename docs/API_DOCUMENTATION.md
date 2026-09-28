# REST API Documentation & Specification

> **Hybrid AI–NWP Multi-Model Forecast Blending System**  
> Complete OpenAPI Reference for Operational Weather Services

Interactive Swagger UI is available at: `http://localhost:8000/docs`  
Interactive ReDoc UI is available at: `http://localhost:8000/redoc`

---

## 1. System Health & Regions

### `GET /api/health`
Checks backend service availability, analytical engine readiness, and database storage health.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "active_provider": "simulated",
  "historical_records_loaded": 2520,
  "system_time": "2026-09-28T22:00:00.000000"
}
```

---

### `GET /api/regions`
Returns metadata and bounding coordinates for all 8 Indian meteorological sub-regions.

**Response (200 OK):**
```json
{
  "total_regions": 8,
  "regions": [
    {
      "id": "western_ghats",
      "name": "Western Ghats & Coastal",
      "center_latitude": 15.5,
      "center_longitude": 74.5,
      "elevation_m": 850.0,
      "coastal": true,
      "description": "High orographic precipitation corridor",
      "key_strengths": {"ecmwf": 0.45, "gfs": 0.35, "ai": 0.20}
    }
  ]
}
```

---

## 2. Forecasts & Blending

### `GET /api/forecasts`
Retrieves raw, individual model forecasts for a specific variable, station, and lead time.

**Query Parameters:**
- `latitude` (optional, float)
- `longitude` (optional, float)
- `region` (optional, string)
- `variable` (string, default: `rainfall`): `rainfall`, `temperature`, `wind_speed`, `wind_direction`
- `lead_time` (int, default: `24`): Lead time in hours

**Response (200 OK):**
```json
{
  "variable": "rainfall",
  "unit": "mm",
  "lead_time_hours": 24,
  "region": "Western Ghats & Coastal",
  "latitude": 19.076,
  "longitude": 72.8777,
  "forecasts": {
    "NWP Model A": 45.2,
    "NWP Model B": 38.0,
    "Ensemble Forecast": 41.5,
    "AI/ML Forecast": 43.1
  }
}
```

---

### `GET /api/blended-forecast`
Calculates the dynamic consensus blended forecast using context-aware adaptive model weights. Applies circular vector math for wind direction.

**Query Parameters:**
- `latitude`, `longitude`, `region`
- `variable` (default: `rainfall`)
- `lead_time` (default: `24`)
- `season` (optional, default: `monsoon`)
- `weather_regime` (optional, default: `normal`)

**Response (200 OK):**
```json
{
  "variable": "rainfall",
  "unit": "mm",
  "lead_time_hours": 24,
  "blended_value": 42.45,
  "ensemble_spread": 7.2,
  "confidence_index": 0.88,
  "model_weights": {
    "NWP Model A": 0.38,
    "NWP Model B": 0.32,
    "Ensemble Forecast": 0.16,
    "AI/ML Forecast": 0.14
  },
  "weighted_contributions": {
    "NWP Model A": 17.18,
    "NWP Model B": 12.16,
    "Ensemble Forecast": 6.64,
    "AI/ML Forecast": 6.03
  },
  "explanation": "NWP Model A received the highest weight (0.38) due to superior rainfall skill during convective conditions."
}
```

---

## 3. Adaptive Model Weights & Mapping

### `GET /api/model-weights`
Returns the normalized model weights ($\sum w_i = 1.0$) for a specific context.

**Query Parameters:**
- `latitude`, `longitude`, `region`, `variable`, `lead_time`, `season`, `weather_regime`

**Response (200 OK):**
```json
{
  "variable": "rainfall",
  "lead_time_hours": 24,
  "region": "Western Ghats & Coastal",
  "weather_regime": "convective_local",
  "normalized_weights": {
    "NWP Model A": 0.42,
    "NWP Model B": 0.30,
    "Ensemble Forecast": 0.15,
    "AI/ML Forecast": 0.13
  },
  "dominant_model": "NWP Model A",
  "dominant_weight": 0.42
}
```

---

## 4. Verification, Backtesting & Skill

### `GET /api/skill-comparison`
Objectively compares individual models against the hybrid blended forecast across verification metrics (MAE, RMSE, Bias, Correlation).

**Query Parameters:**
- `variable`, `lead_time`, `region`

**Response (200 OK):**
```json
{
  "variable": "rainfall",
  "lead_time_hours": 24,
  "region": "Western Ghats & Coastal",
  "comparison": [
    {"model_name": "Hybrid Blended Forecast", "mae": 3.2, "rmse": 4.82, "bias": 0.12, "relative_improvement_pct": 14.1},
    {"model_name": "NWP Model B", "mae": 3.8, "rmse": 5.61, "bias": -0.45, "relative_improvement_pct": null},
    {"model_name": "NWP Model A", "mae": 4.1, "rmse": 5.85, "bias": 0.85, "relative_improvement_pct": null}
  ],
  "headline": "Hybrid forecast achieved 14.1% RMSE reduction relative to the best individual model."
}
```

---

### `POST /api/run-backtest`
Executes an out-of-sample time-series evaluation strictly partitioning historical records into train and test splits to guarantee zero data leakage.

**Request Body:**
```json
{
  "variable": "rainfall",
  "lead_time_hours": 24,
  "test_split_ratio": 0.30
}
```

**Response (200 OK):**
```json
{
  "backtest_id": "BT-20260928-001",
  "variable": "rainfall",
  "lead_time_hours": 24,
  "hybrid_forecast_rmse": 4.82,
  "best_individual_model": "NWP Model B",
  "best_individual_model_rmse": 5.61,
  "relative_improvement_pct": 14.08,
  "summary_statement": "Hybrid forecast RMSE: 4.82 mm | Best individual model RMSE: 5.61 mm | Relative improvement: 14.08%",
  "data_leakage_safeguard": "Weights and metrics calibrated strictly on historical train partition"
}
```

---

## 5. Severe Weather Early Warnings

### `GET /api/extreme-events`
Evaluates regional thresholds for severe weather hazards.

**Query Parameters:**
- `lead_time` (int, default: `24`)
- `hazard_type` (optional): `heavy_rainfall`, `heat_wave`, `high_wind`
- `min_severity` (optional): `minor`, `moderate`, `severe`, `extreme`

**Response (200 OK):**
```json
{
  "total_events": 2,
  "lead_time_hours": 24,
  "guidance": [
    {
      "event_type": "heavy_rainfall",
      "severity_level": "extreme",
      "forecast_value": 85.0,
      "risk_score": 0.89,
      "recommended_alert_category": "RED",
      "location_name": "Mumbai (Santacruz)",
      "affected_region": "Western Ghats & Coastal",
      "confidence": 0.91,
      "action_statement": "Red Alert: Take immediate precautionary action. High flood risk."
    }
  ]
}
```

---

## 6. Automated Pipeline Telemetry & Provenance

### `GET /api/pipeline/status`
Returns the status and full telemetry metrics from the latest automated pipeline run.

**Response (200 OK):**
```json
{
  "status": "operational",
  "latest_run": {
    "execution_id": "PIPE-20260928-220054-83873F",
    "status": "SUCCESS",
    "telemetry": {
      "execution_time_seconds": 0.29,
      "data_sources": ["FileForecastSource", "FileObservationSource"],
      "records_processed": {"total_records": 826, "forecast_records": 406, "observation_records": 420},
      "models_used": ["NWP Model A", "NWP Model B", "Ensemble Forecast", "AI Forecast"],
      "errors": []
    }
  }
}
```

---

### `GET /api/data-sources`
Exposes the active meteorological data sources, supported formats, and strict provenance labels.

**Response (200 OK):**
```json
{
  "active_forecast_source": {
    "name": "DemoForecastAdapter",
    "category": "DEMO DATA",
    "is_real": false,
    "is_simulated": false,
    "is_demo": true,
    "supported_formats": ["NetCDF-3/4 (.nc)", "CSV (.csv)", "JSON (.json)", "REST API"]
  },
  "active_observation_source": {
    "name": "DemoObservationAdapter",
    "category": "DEMO DATA",
    "is_real": false,
    "is_simulated": false,
    "is_demo": true,
    "supported_formats": ["NetCDF-3/4 (.nc)", "IMD AWS CSV (.csv)", "JSON (.json)", "REST API"]
  },
  "disclaimer_notice": "STRICT METEOROLOGICAL PROVENANCE: Simulated data is explicitly flagged as synthetic and must never be represented as real observational data."
}
```
