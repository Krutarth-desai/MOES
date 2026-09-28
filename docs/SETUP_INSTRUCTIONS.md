# System Setup & Installation Guide

> **Hybrid AI–NWP Multi-Model Forecast Blending System**  
> Smart India Hackathon (SIH) Operational Meteorological Platform

This guide provides step-by-step instructions to set up, configure, test, and run the Hybrid AI–NWP Multi-Model Forecast Blending System on Windows, Linux, or macOS.

---

## 1. Prerequisites

Ensure the following tools are installed on your host workstation:

| Requirement | Supported Version | Verification Command | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ (tested on Python 3.14) | `python --version` | Standard scientific runtime |
| **Node.js** | 18+ (tested on Node 20+) | `node -v` | Required for frontend build |
| **npm** | 9+ | `npm -v` | Vite package manager |
| **Git** | Any modern version | `git --version` | Codebase version control |

---

## 2. Repository Setup

Clone or open the project directory:

```bash
cd d:\GIT\MOES
```

Ensure the repository structure is intact:
```
MOES/
├── backend/            # FastAPI REST backend and analytical engines
├── frontend/           # Vite + React 18 operational dashboard
├── configs/            # YAML configuration files (models, domains, thresholds)
├── data/               # Raw, processed, and sample benchmark datasets
├── docs/               # Architecture, setup, demo, and API documentation
├── tests/              # 191+ automated unit and integration tests
└── run_pipeline.py     # Single-command CLI runner for the 12-step pipeline
```

---

## 3. Backend Setup

### A. Python Environment
It is recommended to run in your dedicated virtual environment or Python 3.10+ installation:

```bash
# Optional: create a virtual environment
python -m venv .venv

# Activate on Windows PowerShell:
.venv\Scripts\Activate.ps1

# Activate on Linux/macOS:
source .venv/bin/activate
```

### B. Install Python Dependencies
Install required backend packages:

```bash
pip install fastapi uvicorn pydantic pyyaml httpx numpy
```

*(Optional for advanced NetCDF C extensions: `pip install scipy netCDF4 xarray`. Note: A pure-Python NetCDF-3 binary parser is built-in, so external NetCDF C libraries are not strictly required!)*

---

## 4. Frontend Setup

### A. Install Node Dependencies
Navigate to the `frontend/` directory and install npm packages:

```bash
cd frontend
npm install
cd ..
```

### B. Verify Frontend Production Build
Validate that Vite compiles without warnings or syntax errors:

```bash
cd frontend
npm run build
cd ..
```
The output bundle will be generated in `frontend/dist/`.

---

## 5. Running the System Locally

### Step 1: Start the FastAPI Backend
Launch the backend server via `uvicorn`:

```bash
# From repository root (d:\GIT\MOES):
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend is now live:
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Reference**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Step 2: Start the React Dashboard
In a separate terminal, launch the Vite development server:

```bash
cd frontend
npm run dev
```

The operational dashboard is now accessible at [http://localhost:5173/](http://localhost:5173/) (or the port specified in terminal).

---

## 6. Running the 12-Step Automated Pipeline via CLI

The entire meteorological forecast processing workflow can be executed directly from the command line:

### A. Single Execution Pass (Default)
```bash
python run_pipeline.py --once
```

### B. Scheduled Recurring Execution (e.g. every 5 minutes)
```bash
python run_pipeline.py --interval 300
```

### C. Specific Stations and Variables
```bash
python run_pipeline.py --once --stations BOM,DEL,BLR --variables rainfall,temperature --lead-times 6,12,24,48
```

### D. Export Execution Report to JSON
```bash
python run_pipeline.py --once --json-output pipeline_report.json
```

---

## 7. Running the Automated Test Suite

Execute all 191 unit and integration tests covering data ingestion, verification, adaptive weighting, forecast blending, extreme hazards, NetCDF parsing, and pipeline orchestration:

```bash
python -m unittest discover tests
```

Expected output:
```
Ran 191 tests in 29.2s — OK
```

To run a specific test suite:
```bash
# Test data adapters, NetCDF parsing, and provenance:
python -m unittest tests/test_data_adapters.py

# Test 12-step pipeline and scheduler:
python -m unittest tests/test_pipeline.py

# Test core REST APIs:
python -m unittest tests/test_core_api.py
```
