"""
Hybrid AI–NWP Multi-Model Forecast Blending System
Unified Application Launcher (run.py)

Directly starts the complete operational stack:
  1. FastAPI Meteorological Backend (uvicorn) on http://localhost:8000
  2. React + Vite Interactive GIS Dashboard on http://localhost:3000
  3. Automatically validates system health and launches default browser.

Usage:
  python run.py                   # Launches complete full-stack application
  python run.py --backend-only    # Runs only FastAPI backend server
  python run.py --no-browser      # Starts stack without auto-opening browser
  python run.py --demo            # Auto-opens directly to SIH Demo Mode
  python run.py --port 8080       # Custom backend port
"""

import argparse
import os
import platform
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

# Fix Windows console UTF-8 encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

os.environ["PYTHONUNBUFFERED"] = "1"

# Paths
ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"

BANNER = f"""{CYAN}{BOLD}
+=============================================================================+
|                                                                             |
|   HYBRID AI-NWP MULTI-MODEL FORECAST BLENDING SYSTEM                        |
|   Ministry of Earth Sciences (MoES) - India Meteorological Department (IMD) |
|   Smart India Hackathon (SIH) Operational Production Prototype              |
|                                                                             |
+=============================================================================+{RESET}
"""


def log_backend(msg: str):
    print(f"{BLUE}[BACKEND]{RESET}  {msg.strip()}", flush=True)


def log_frontend(msg: str):
    print(f"{MAGENTA}[FRONTEND]{RESET} {msg.strip()}", flush=True)


def log_system(msg: str):
    print(f"{GREEN}[SYSTEM]{RESET}   {msg.strip()}", flush=True)


def log_warn(msg: str):
    print(f"{YELLOW}[WARNING]{RESET}  {msg.strip()}", flush=True)


def log_error(msg: str):
    print(f"{RED}[ERROR]{RESET}    {msg.strip()}", flush=True)



def check_python_environment():
    """Verify minimum required python modules."""
    required = ["fastapi", "uvicorn", "pydantic"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        log_error(f"Missing required Python dependencies: {', '.join(missing)}")
        log_error("Please install them with: pip install -r requirements.txt")
        sys.exit(1)


def wait_for_backend(url: str, timeout: float = 15.0) -> bool:
    """Poll backend health check until it responds 200 OK or times out."""
    start_time = time.time()
    health_endpoint = f"{url.rstrip('/')}/api/health"
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(health_endpoint, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionResetError, OSError):
            time.sleep(0.3)
    return False


def wait_for_frontend(url: str, timeout: float = 12.0) -> bool:
    """Poll frontend server until it starts responding."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status in (200, 304):
                    return True
        except (urllib.error.URLError, ConnectionResetError, OSError):
            time.sleep(0.3)
    return False


def stream_pipe(pipe, logger_func):
    """Continuously reads output from a subprocess pipe and logs it."""
    try:
        for line in iter(pipe.readline, ""):
            if not line:
                break
            # Skip verbose health check polling logs
            if "GET /api/health" in line:
                continue
            logger_func(line)
    except (ValueError, OSError):
        pass


def run_full_stack():
    parser = argparse.ArgumentParser(
        description="Unified Launcher for MoES Hybrid AI-NWP Forecast Blending System."
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host interface to bind backend server (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Backend port for FastAPI / Uvicorn (default: 8000)",
    )
    parser.add_argument(
        "--frontend-port",
        type=int,
        default=3000,
        help="Frontend port for Vite dev server (default: 3000)",
    )
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run only the FastAPI backend server",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not auto-open the browser on startup",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Open directly to the dedicated SIH Presentation Demo Mode",
    )
    parser.add_argument(
        "--build-frontend",
        action="store_true",
        help="Trigger npm run build before launching servers",
    )

    args = parser.parse_args()

    print(BANNER)
    check_python_environment()

    # Determine command extensions for Windows
    is_windows = platform.system() == "Windows"
    npm_cmd = "npm.cmd" if is_windows else "npm"

    has_node = shutil.which(npm_cmd) is not None or shutil.which("npm") is not None
    has_frontend_code = (FRONTEND_DIR / "package.json").exists()
    has_prebuilt_dist = (FRONTEND_DIST / "index.html").exists()

    processes = []

    def shutdown_processes():
        log_system("Shutting down processes gracefully...")
        for p in processes:
            try:
                if is_windows:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    p.terminate()
            except Exception:
                pass
        log_system("Shutdown complete. Good luck with SIH presentation!")

    # Register OS signals
    def sig_handler(sig, frame):
        shutdown_processes()
        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    # 1. Build frontend if requested
    if args.build_frontend and has_node and has_frontend_code:
        log_system("Building optimized frontend bundle with Vite...")
        subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR), check=True)
        log_system("Frontend build finished successfully.")

    # 2. Launch FastAPI Backend
    log_system(f"Launching FastAPI backend on http://{args.host}:{args.port}...")
    backend_env = os.environ.copy()
    backend_env["PYTHONPATH"] = str(ROOT_DIR)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]

    backend_proc = subprocess.Popen(
        backend_cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=backend_env,
    )
    processes.append(backend_proc)

    # Start backend stream logger thread
    t_backend = threading.Thread(
        target=stream_pipe,
        args=(backend_proc.stdout, log_backend),
        daemon=True,
    )
    t_backend.start()

    backend_local_url = f"http://localhost:{args.port}"
    log_system("Waiting for meteorological backend to initialize...")
    if not wait_for_backend(backend_local_url, timeout=12.0):
        log_error("Backend failed to respond on /api/health within 12 seconds.")
        shutdown_processes()
        sys.exit(1)

    log_system(f"{GREEN}✓ Backend is healthy and operational.{RESET}")

    # 3. Launch Frontend (if requested and node available)
    frontend_started = False
    frontend_url = None

    if not args.backend_only and has_node and has_frontend_code:
        log_system(f"Launching Vite frontend dev server on http://localhost:{args.frontend_port}...")
        frontend_cmd = [npm_cmd, "run", "dev", "--", "--port", str(args.frontend_port)]

        frontend_proc = subprocess.Popen(
            frontend_cmd,
            cwd=str(FRONTEND_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append(frontend_proc)

        t_frontend = threading.Thread(
            target=stream_pipe,
            args=(frontend_proc.stdout, log_frontend),
            daemon=True,
        )
        t_frontend.start()

        frontend_url = f"http://localhost:{args.frontend_port}"
        if wait_for_frontend(frontend_url, timeout=10.0):
            frontend_started = True
            log_system(f"{GREEN}✓ Frontend is online and serving at {frontend_url}{RESET}")
        else:
            log_warn("Frontend dev server took longer than expected; falling back to direct URL.")
            frontend_started = True

    elif has_prebuilt_dist:
        # Prebuilt bundle served directly by FastAPI
        frontend_url = f"http://localhost:{args.port}/dashboard"
        log_system(f"{GREEN}✓ Serving prebuilt React dashboard from backend at {frontend_url}{RESET}")
    else:
        frontend_url = f"http://localhost:{args.port}/docs"
        log_warn("Node.js not detected and no prebuilt bundle found. API Docs will be opened.")

    # 4. Target Browser URL
    target_browser_url = frontend_url
    if args.demo and target_browser_url:
        target_browser_url = f"{target_browser_url.rstrip('/')}/#demo-mode"

    # Print Summary Card
    print(f"""
{GREEN}{BOLD}============================================================================={RESET}
  {BOLD}SYSTEM READY & OPERATIONAL{RESET}
  
  * {BOLD}Operational Dashboard UI:{RESET}     {CYAN}{frontend_url}{RESET}
  * {BOLD}SIH Presentation Demo Mode:{RESET}   {CYAN}{frontend_url}/#demo-mode{RESET}
  * {BOLD}Interactive OpenAPI Docs:{RESET}     {CYAN}http://localhost:{args.port}/docs{RESET}
  * {BOLD}System Health Probe:{RESET}          {CYAN}http://localhost:{args.port}/api/health{RESET}
  * {BOLD}7-Stage Pipeline Demo API:{RESET}    {CYAN}http://localhost:{args.port}/api/demo/run{RESET}

  {YELLOW}Press Ctrl+C at any time to gracefully terminate all services.{RESET}
{GREEN}{BOLD}============================================================================={RESET}
""")

    # 5. Open Web Browser
    if not args.no_browser and target_browser_url:
        time.sleep(0.5)
        log_system(f"Launching web browser at {target_browser_url}...")
        webbrowser.open(target_browser_url)

    # 6. Keep main process alive while watching child processes
    try:
        while True:
            for p in processes:
                poll = p.poll()
                if poll is not None:
                    log_warn(f"Process PID {p.pid} exited with code {poll}.")
                    shutdown_processes()
                    sys.exit(poll)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("")
        shutdown_processes()
        sys.exit(0)


if __name__ == "__main__":
    run_full_stack()
