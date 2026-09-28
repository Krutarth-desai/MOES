# SIH Demonstration Instructions

> **Hybrid AI–NWP Multi-Model Forecast Blending System**  
> Operational Meteorology Demonstration Protocol for Smart India Hackathon (SIH)

This document provides a guided walkthrough for demonstrating the system to technical and non-technical judges.

---

## 1. Quick Launch (Under 60 Seconds)

Open two terminal windows:

### Terminal 1: Launch Backend API Server
```bash
# From repository root (d:\GIT\MOES):
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Verify: Open [http://localhost:8000/api/health](http://localhost:8000/api/health) to confirm `"status": "healthy"`.

### Terminal 2: Launch React GIS Dashboard
```bash
cd frontend
npm run dev
```
Open: [http://localhost:5173/](http://localhost:5173/)

---

## 2. Interactive Dashboard Walkthrough (8 Sections)

The dashboard is structured into 8 operational panels accessible via the top navigation bar:

### Section 1: Overview & Executive Status
- **What to show**:
  - Active Synoptic Weather Regime badge (`Convective/Storm`, `Heat Wave`, `Normal`).
  - Dominant Contributing Model badge (e.g. `NWP Model A: 48%`).
  - Active Severe Weather Alerts counter.
  - Mean multi-model confidence index.
- **Judge Talking Point**: *"The system immediately diagnoses the atmospheric state and dynamically identifies which model is most trustworthy for the current conditions."*

### Section 2: Live Multi-Model Forecast Meteogram
- **What to show**:
  - Switch between variables: **Precipitation (mm)**, **Temperature (°C)**, and **Wind Speed & Direction**.
  - Point out individual model forecasts (NWP Model A, NWP Model B, Ensemble, AI).
  - Point out the **Cyan Bold Line**: The Hybrid Blended Forecast.
  - Observe how the blended line avoids erratic spikes from single models while capturing realistic extrema.
- **Judge Talking Point**: *"Notice how for wind direction, we don't perform naive arithmetic averaging which would fail across 360°/0° North; we compute circular trigonometric vector averaging."*

### Section 3: Model Comparison & Circular Wind
- **What to show**:
  - Comparison table listing individual model predictions side-by-side with the hybrid consensus.
  - Circular wind compass showing directional convergence across models.

### Section 4: Adaptive Model Weights Radar
- **What to show**:
  - The dynamic weight radar chart displaying how weights shift across lead times (24h, 48h, 72h, 120h).
  - Note how AI models carry higher weight at short horizons ($T+24$h), while physical NWP models gain prominence at longer synoptic horizons ($T+72$h).
- **Judge Talking Point**: *"Weights are not static constants. They obey the Softmax Simplex where $\sum w_i = 1.0$ and dynamically adapt to terrain, lead time, season, and historical skill."*

### Section 5: Geographic Model Weight Map (GIS)
- **What to show**:
  - Interactive Leaflet map displaying Indian meteorological sub-regions (Western Ghats, Indo-Gangetic Plains, Himalayas, etc.).
  - Color-coded dominant model per region:
    - *Blue*: NWP Model A (GFS-like)
    - *Green*: NWP Model B (ECMWF-like)
    - *Purple*: AI Forecast (GraphCast-like)
    - *Orange*: Ensemble Forecast
- **Judge Talking Point**: *"No single model is globally best. ECMWF excels over Western Ghats orography; GFS leads over the Gangetic plains; AI dominates short-range non-linear transitions."*

### Section 6: IMD Extreme Weather Guidance
- **What to show**:
  - Automated early warning cards for **Heavy Rainfall** ($>64.5$ mm), **Heatwaves** ($>40^\circ$C), and **Gale Winds** ($>50$ km/h).
  - Warning colors mapped directly to official IMD color codes:
    - 🔴 **Red Alert**: Take Action (Extremely Heavy Rain / Severe Heatwave)
    - 🟠 **Orange Alert**: Be Prepared
    - 🟡 **Yellow Alert**: Be Aware
    - 🟢 **Green**: No Warning
- **Judge Talking Point**: *"We clearly distinguish between the raw forecast value, the derived probabilistic risk indicator, and the official alert threshold."*

### Section 7: Objective Backtesting & Skill Scorecards
- **What to show**:
  - Click **"Run Backtest"** to trigger a live rolling-origin time-series evaluation.
  - Show the headline verification metric:
    - *"Hybrid forecast RMSE: 4.82 mm | Best individual model RMSE: 5.61 mm | Relative improvement: 14.1%"*
- **Judge Talking Point**: *"Every improvement number is computed strictly from out-of-sample test splits. We enforce a zero-data-leakage guarantee by calibrating weights only on the historical train partition."*

### Section 8: Automated 12-Step Operational Pipeline & Telemetry
- **What to show**:
  - Click **"Run Pipeline Now"** in Card 4 of Section 8.
  - Watch the live telemetry card display:
    - *Execution Time*: e.g., `0.21s` (or full run time)
    - *Records Processed*: Total count across forecasts and observations
    - *Generated Forecasts*: Count of blended points
    - *Errors*: `0 warnings/errors`
    - *Data Sources & Provenance Badges*: `REAL DATA` (Green), `SIMULATED DATA` (Purple), `DEMO DATA` (Blue).
- **Judge Talking Point**: *"The entire end-to-end meteorological workflow is automated and can be executed with a single command: `python run_pipeline.py` or scheduled as a cron daemon."*

---

## 3. Command-Line Demonstration (CLI)

Run the single-command automated pipeline in front of judges:

```bash
# Execute single pass:
python run_pipeline.py --once

# Execute for specific station and variables:
python run_pipeline.py --once --stations BOM,DEL --variables rainfall,temperature

# Execute scheduled test (2 iterations, 2-second interval):
python run_pipeline.py --interval 2 --iterations 2
```
Point out the formatted ASCII report and telemetry output logging all 6 required metrics.
