# Sample Dataset & Format Specification Guide

> **Hybrid AI–NWP Multi-Model Forecast Blending System**  
> Meteorological Datasets, Schema Specifications, and Operational Ingestion Guidelines

This document details the bundled demonstration datasets, supported scientific weather file formats, schema mappings, and steps to connect real operational feeds.

---

## 1. Bundled Sample Datasets (`data/sample/`)

The repository includes pre-packaged benchmark fixtures in [`data/sample/`](file:///d:/GIT/MOES/data/sample/) enabling immediate offline execution, verification, and UI testing:

| File Name | Format | Model / Network Origin | Description | Records |
| :--- | :--- | :--- | :--- | :--- |
| **`nwp_model_a.csv`** | CSV | NWP Model A (GFS-like) | High spatial responsiveness; slight wet bias in convective rainfall | 282 rows |
| **`nwp_model_b.csv`** | CSV | NWP Model B (ECMWF-like) | Strong synoptic consistency; conservative peak precipitation | 281 rows |
| **`ensemble_forecast.csv`**| CSV | Ensemble (GEFS/EPS-like) | Multi-member probabilistic mean with ensemble spread | 281 rows |
| **`ai_forecast.json`** | JSON | AI Forecast (GraphCast-like) | Deep neural network forecast (GeoJSON FeatureCollection layout) | 282 rows |
| **`ground_truth.csv`** | CSV | IMD Benchmark Ground Truth | Verified surface station observations for skill calibration | 280 rows |
| **`observations.csv`** | CSV | In-Situ AWS Station Network | Real-time multi-variable telemetry (Temp, Rain, Wind, RH, MSLP) | 73 rows |
| **`observations.json`**| JSON | IMD AWS Digital Bulletin | Structured JSON observation payload | 73 rows |

---

## 2. Standard Meteorological Data Formats Supported

The ingestion layer natively parses three primary meteorological data formats:

### A. NetCDF Format (`.nc`, `.nc4`, `.netcdf`)
- **CF Conventions Compliant**: Supports Climate and Forecast (CF) metadata standards.
- **Built-in Pure-Python Reader**: Includes `PurePythonNetCDF3Reader` so binary NetCDF-3 (CDF-1/CDF-2) files can be parsed without requiring external C libraries (`libnetcdf` or `HDF5`).
- **Standard Variable Mappings**:
  - *Temperature*: `t2m`, `temp`, `temperature`, `temperature_2m`, `tas` (automatically detects Kelvin $>150$ and converts to Celsius).
  - *Rainfall*: `tp`, `precip`, `precipitation`, `rainfall`, `rain_mm`, `pr`.
  - *Wind Speed*: `ws10`, `wind_speed`, `wind_speed_10m`, `si10` (or derived from $u_{10}$ and $v_{10}$ via $\sqrt{u^2 + v^2}$).
  - *Wind Direction*: `wdir`, `wind_dir`, `wdir10` (or derived from $u_{10}$ and $v_{10}$ via $\text{atan2}(-u, -v)$).

### B. Tabular CSV Format (`.csv`)
- **Supported Columns**:
  - Coordinate: `latitude`, `longitude`, `station_id`, `station_name`, `elevation_m`
  - Timestamp: `timestamp`, `initialization_time`, `lead_time_hours`
  - Variables: `temperature`, `rainfall`, `wind_speed`, `wind_direction`
  - Metadata: `model_name`, `region`, `season`

### C. JSON & GeoJSON Format (`.json`, `.geojson`)
- Supports flat record arrays, nested response envelopes (`{"data": [...]}` or `{"records": [...]}`), and standard **GeoJSON `FeatureCollection`** with `coordinates: [lon, lat]` and `properties: {temperature, rainfall, ...}`.

---

## 3. Canonical Internal Record Schemas

All ingested forecasts and observations are validated and converted into canonical Pydantic models:

### A. `StandardForecastRecord` ([`schema.py`](file:///d:/GIT/MOES/backend/app/data/ingestion/schema.py#L45))
```python
class StandardForecastRecord(BaseModel):
    timestamp: datetime           # Valid forecast time
    latitude: float               # Decimal degrees [-90, +90]
    longitude: float              # Decimal degrees [-180, +180]
    forecast_variable: ForecastVariable  # TEMPERATURE, RAINFALL, WIND_SPEED, WIND_DIRECTION
    forecast_value: float         # In canonical units (°C, mm, km/h, degrees)
    initialization_time: datetime # Model cycle start time
    lead_time_hours: int          # Forecast horizon (e.g. 6, 12, 24, 48, 72, 168)
    source_name: str              # Model name
    region: str                   # Geographic region
    season: Season                # Climatological season
    weather_regime: WeatherRegime # Diagnosed regime
    quality_flag: QualityFlag     # VALID, IMPUTED, CLAMPED, REJECTED
```

### B. `ObservationRecord` ([`schema.py`](file:///d:/GIT/MOES/backend/app/data/observation/schema.py#L6))
```python
class ObservationRecord(BaseModel):
    timestamp: datetime           # In-situ observation time
    latitude: float               # Station latitude
    longitude: float              # Station longitude
    temperature: Optional[float]  # Observed 2m temperature in °C
    rainfall: Optional[float]     # Observed rainfall in mm
    wind_speed: Optional[float]   # Observed 10m wind speed in km/h
    wind_direction: Optional[float] # Observed direction (0-360°)
    station_id: Optional[str]     # Observatory code (e.g. BOM, DEL)
    station_name: Optional[str]   # Station name
    source: str                   # Network provider (e.g. IMD_AWS)
```

---

## 4. Plugging in Real Operational Meteorological Feeds

To transition from the bundled sample fixtures to live operational data:

### Option A: Via Configuration File ([`configs/data_sources.yaml`](file:///d:/GIT/MOES/configs/data_sources.yaml))
Edit `configs/data_sources.yaml`:
```yaml
forecast_source:
  type: "netcdf"
  path: "data/raw/operational_gfs_0p25.nc"
  category: "REAL DATA"

observation_source:
  type: "csv"
  path: "data/raw/imd_aws_telemetry_live.csv"
  category: "REAL DATA"
```

### Option B: Via Environment Variables
```bash
set MOES_FORECAST_SOURCE=netcdf
set MOES_FORECAST_PATH=D:\operational_data\ecmwf_20260928.nc
set MOES_OBSERVATION_SOURCE=csv
set MOES_OBSERVATION_PATH=D:\operational_data\imd_aws_stations.csv
set MOES_DATA_CATEGORY="REAL DATA"

python run_pipeline.py --once
```

### Option C: Subclassing the Modular Adapters
Implement custom connections to IMD GTS or NOAA NOMADS servers by subclassing [`ForecastSource`](file:///d:/GIT/MOES/backend/app/data/sources/interfaces.py#L11):

```python
from backend.app.data.sources.interfaces import ForecastSource
from backend.app.data.sources.provenance import DataCategory, DataProvenance

class ImdOperationalGtsSource(ForecastSource):
    @property
    def source_name(self) -> str:
        return "IMD National Weather Forecasting Centre (NWFC) GTS Feed"

    @property
    def data_category(self) -> DataCategory:
        return DataCategory.REAL_DATA

    @property
    def provenance(self) -> DataProvenance:
        return DataProvenance.create_real(
            provider="India Meteorological Department",
            description="Operational Global and Regional NWP models from IMD/NCMRWF GTS server.",
        )

    def fetch_forecasts(self, station_ids, variables, lead_times, reference_time):
        # Fetch from IMD API or binary GRIB2 server, map to List[StandardForecastRecord]
        ...
```
