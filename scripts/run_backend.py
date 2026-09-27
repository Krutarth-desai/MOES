#!/usr/bin/env python3
"""
Development runner script for MOES FastAPI Backend.
"""
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

if __name__ == "__main__":
    import uvicorn
    print("Starting MOES Hybrid AI-NWP Blending Backend on http://localhost:8000 ...")
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
