#!/usr/bin/env python
"""
Automated Multi-Model Meteorological Forecast Processing Workflow
Hybrid AI–NWP Multi-Model Blending System
Smart India Hackathon (SIH) Operational Pipeline Runner

Usage:
    python run_pipeline.py                      # Run a single full pipeline execution
    python run_pipeline.py --once               # Explicit single pass execution
    python run_pipeline.py --interval 300       # Scheduled recurring execution every 5 minutes
    python run_pipeline.py --schedule 3600      # Scheduled execution every 1 hour
    python run_pipeline.py --stations BOM,DEL   # Run for specific station observatories
    python run_pipeline.py --variables rainfall # Run for specific variable
    python run_pipeline.py --verbose            # Enable detailed debug logging
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to sys.path to enable direct command-line execution
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.pipeline.schemas import PipelineConfig, PipelineExecutionReport
from backend.app.pipeline.scheduler import PipelineScheduler
from backend.app.pipeline.workflow import AutomatedForecastPipeline


def setup_pipeline_logging(verbose: bool = False):
    """Configures high-visibility console and file logging."""
    log_level = logging.DEBUG if verbose else logging.INFO
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    # Configure root and pipeline loggers
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    # Remove existing handlers to avoid duplicates
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
    root_logger.addHandler(handler)


def print_banner():
    """Prints ASCII banner for the SIH operational pipeline."""
    banner = r"""
================================================================================
   _  _ __   __ ___   ___  ___  ___    ___  ___  ___  _  _  ___  _  _   ___ 
  | || |\ \ / /| _ ) | _ \|_ _||   \  | _ )|   \| __|| \| |/   \| || | / __|
  | __ | \ V / | _ \ |   / | | | |) | | _ \| |) | _| | .` || - || || | \__ \
  |_||_|  |_|  |___/ |_|_\|___||___/  |___/|___/|___||_|\_||_|_||_||_| |___/
          AUTOMATED METEOROLOGICAL FORECAST PROCESSING WORKFLOW
================================================================================
    """
    print(banner)


def parse_arguments():
    """Parses command-line arguments for single-pass and scheduled runs."""
    parser = argparse.ArgumentParser(
        description="Automated Forecast Processing Workflow for Hybrid AI-NWP Blending System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Execution Mode
    mode_group = parser.add_argument_group("Execution Mode")
    mode_group.add_argument(
        "--once",
        action="store_true",
        default=False,
        help="Run a single pass of the 12-step pipeline and exit (default if no scheduling set).",
    )
    mode_group.add_argument(
        "--interval",
        type=int,
        default=None,
        metavar="SECONDS",
        help="Run on a scheduled interval (e.g. --interval 300 for every 5 minutes).",
    )
    mode_group.add_argument(
        "--schedule",
        type=str,
        default=None,
        metavar="SECONDS_OR_CRON",
        help="Alias for scheduled recurring execution in seconds (e.g. --schedule 3600 for hourly).",
    )
    mode_group.add_argument(
        "--iterations",
        type=int,
        default=None,
        metavar="COUNT",
        help="Maximum iterations for scheduled execution before exiting.",
    )

    # Target Scope Options
    scope_group = parser.add_argument_group("Pipeline Parameters & Target Scope")
    scope_group.add_argument(
        "--stations",
        type=str,
        default="all",
        help="Comma-separated station IDs (e.g. BOM,DEL,BLR,CCU) or 'all' (default: all reference stations).",
    )
    scope_group.add_argument(
        "--variables",
        type=str,
        default="rainfall,temperature,wind_speed,wind_direction",
        help="Comma-separated meteorological variables to blend (default: all 4).",
    )
    scope_group.add_argument(
        "--lead-times",
        type=str,
        default="6,12,24,48",
        help="Comma-separated forecast lead times in hours (default: 6,12,24,48).",
    )
    scope_group.add_argument(
        "--season",
        type=str,
        default="monsoon",
        choices=["monsoon", "post_monsoon", "winter", "pre_monsoon"],
        help="Climatological season context for adaptive weight engine (default: monsoon).",
    )
    scope_group.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Execute calculations and validation without persisting records to disk.",
    )
    scope_group.add_argument(
        "--no-dashboard-update",
        action="store_true",
        default=False,
        help="Skip updating dashboard JSON telemetry files.",
    )

    # Data Source Selection & Provenance
    source_group = parser.add_argument_group("Data Sources & Meteorological Formats")
    source_group.add_argument(
        "--forecast-source",
        type=str,
        default=None,
        choices=["demo", "simulated", "netcdf", "csv", "json", "openmeteo", "hybrid"],
        help="Select forecast data source type (default: from config/env or 'demo').",
    )
    source_group.add_argument(
        "--observation-source",
        type=str,
        default=None,
        choices=["demo", "simulated", "netcdf", "csv", "json", "openmeteo", "hybrid"],
        help="Select observation ground truth source type (default: from config/env or 'demo').",
    )
    source_group.add_argument(
        "--forecast-path",
        type=str,
        default=None,
        help="Custom path to NetCDF, CSV, or JSON forecast file or directory.",
    )
    source_group.add_argument(
        "--observation-path",
        type=str,
        default=None,
        help="Custom path to NetCDF, CSV, or JSON observation file or directory.",
    )
    source_group.add_argument(
        "--provenance",
        type=str,
        default=None,
        choices=["REAL DATA", "SIMULATED DATA", "DEMO DATA"],
        help="Override data provenance classification tag.",
    )

    # Output & Diagnostics
    diag_group = parser.add_argument_group("Diagnostics & Output")
    diag_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable detailed debug-level logging.",
    )
    diag_group.add_argument(
        "--json-output",
        type=str,
        default=None,
        metavar="PATH",
        help="Write the complete execution report JSON to a custom file path.",
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    setup_pipeline_logging(verbose=args.verbose)
    print_banner()

    # Parse stations
    stations_list = None
    if args.stations and args.stations.strip().lower() != "all":
        stations_list = [s.strip().upper() for s in args.stations.split(",") if s.strip()]

    # Parse variables
    variables_list = [v.strip().lower() for v in args.variables.split(",") if v.strip()]

    # Parse lead times
    lead_times_list = [int(lt.strip()) for lt in args.lead_times.split(",") if lt.strip()]

    # Assemble PipelineConfig
    config = PipelineConfig(
        stations=stations_list,
        variables=variables_list,
        lead_times=lead_times_list,
        season=args.season,
        dry_run=args.dry_run,
        persist_results=not args.dry_run,
        notify_dashboard=not args.no_dashboard_update,
    )

    from backend.app.data.sources.factory import ForecastSourceFactory, ObservationSourceFactory

    forecast_source = ForecastSourceFactory.create(
        source_type=args.forecast_source,
        path=args.forecast_path,
        category=args.provenance,
    )
    observation_source = ObservationSourceFactory.create(
        source_type=args.observation_source,
        path=args.observation_path,
        category=args.provenance,
    )

    logging.info("--------------------------------------------------------------------------------")
    logging.info("DATA PROVENANCE CONTEXT:")
    logging.info("  Forecast Source   : %s [%s]", forecast_source.source_name, forecast_source.data_category.value)
    logging.info("  Observation Source: %s [%s]", observation_source.source_name, observation_source.data_category.value)
    if forecast_source.provenance.disclaimer:
        logging.info("  Forecast Notice   : %s", forecast_source.provenance.disclaimer)
    if observation_source.provenance.disclaimer:
        logging.info("  Observation Notice: %s", observation_source.provenance.disclaimer)
    logging.info("--------------------------------------------------------------------------------")

    pipeline = AutomatedForecastPipeline(
        forecast_source=forecast_source,
        observation_source=observation_source,
    )

    # Determine whether scheduled or single execution
    schedule_interval = args.interval
    if schedule_interval is None and args.schedule is not None:
        try:
            schedule_interval = int(args.schedule.strip())
        except ValueError:
            logging.warning("Non-integer schedule string '%s' interpreted as hourly (3600s)", args.schedule)
            schedule_interval = 3600

    if schedule_interval and schedule_interval > 0:
        # Scheduled Recurring Execution
        logging.info("Starting pipeline in SCHEDULED MODE (interval: %ds, max_iterations: %s)", schedule_interval, args.iterations)
        scheduler = PipelineScheduler(pipeline=pipeline, config=config)
        try:
            scheduler.run_interval(
                interval_seconds=schedule_interval,
                max_iterations=args.iterations,
                blocking=True,
            )
        except KeyboardInterrupt:
            logging.info("Interrupted by user. Shutting down scheduler.")
            scheduler.stop()
        sys.exit(0)

    # Single-pass Execution (Default / --once)
    logging.info("Executing single automated forecast processing run...")
    report = pipeline.run(config=config)

    # Optional custom JSON output export
    if args.json_output:
        out_path = Path(args.json_output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2, default=str)
        logging.info("Custom execution report written to: %s", out_path)

    # Exit with appropriate status code
    if report.status == "FAILED":
        logging.error("Pipeline run completed with status FAILED.")
        sys.exit(1)
    else:
        logging.info("Pipeline run completed successfully with status: %s", report.status)
        sys.exit(0)


if __name__ == "__main__":
    main()
