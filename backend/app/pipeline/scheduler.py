import logging
import signal
import sys
import threading
import time
from datetime import datetime
from typing import Callable, Optional

from backend.app.pipeline.schemas import PipelineConfig, PipelineExecutionReport
from backend.app.pipeline.workflow import AutomatedForecastPipeline

logger = logging.getLogger("moes.pipeline.scheduler")


class PipelineScheduler:
    """
    Automated Meteorological Forecast Pipeline Scheduler.
    
    Supports:
    - Interval-based scheduled execution (e.g. every 60s, 300s, 3600s)
    - Foreground loop with graceful OS signal handling (SIGINT/SIGTERM)
    - Background thread execution with start()/stop() control
    - Maximum iteration limits for test automation
    """

    def __init__(
        self,
        pipeline: Optional[AutomatedForecastPipeline] = None,
        config: Optional[PipelineConfig] = None,
        on_complete_callback: Optional[Callable[[PipelineExecutionReport], None]] = None,
    ):
        self.pipeline = pipeline or AutomatedForecastPipeline()
        self.config = config or PipelineConfig()
        self.on_complete_callback = on_complete_callback
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._iteration_count = 0
        self._last_report: Optional[PipelineExecutionReport] = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    @property
    def last_report(self) -> Optional[PipelineExecutionReport]:
        return self._last_report

    def run_interval(
        self,
        interval_seconds: int = 300,
        max_iterations: Optional[int] = None,
        blocking: bool = True,
    ):
        """
        Runs the pipeline repeatedly every `interval_seconds`.
        If blocking=True, runs on the current thread and hooks SIGINT/SIGTERM.
        If blocking=False, spawns a background worker thread.
        """
        if self._running:
            logger.warning("PipelineScheduler is already running.")
            return

        self._running = True
        self._stop_event.clear()

        def _worker():
            logger.info(
                "PipelineScheduler started: recurring every %ds (max_iterations=%s)",
                interval_seconds,
                max_iterations,
            )

            # First run immediately on startup
            while not self._stop_event.is_set():
                iter_t0 = time.time()
                self._iteration_count += 1
                logger.info(
                    "--- Scheduled Pipeline Trigger [Cycle #%d at %s] ---",
                    self._iteration_count,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

                try:
                    report = self.pipeline.run(config=self.config)
                    self._last_report = report
                    if self.on_complete_callback:
                        try:
                            self.on_complete_callback(report)
                        except Exception as cb_err:
                            logger.error("Callback error: %s", cb_err)
                except Exception as run_err:
                    logger.exception("Scheduled pipeline iteration failed: %s", run_err)

                if max_iterations and self._iteration_count >= max_iterations:
                    logger.info("Reached maximum iterations limit (%d). Stopping.", max_iterations)
                    break

                # Sleep until next interval or stop event
                elapsed = time.time() - iter_t0
                remaining = max(1.0, interval_seconds - elapsed)
                logger.info("Cycle #%d complete. Sleeping for %.1fs until next forecast cycle...", self._iteration_count, remaining)

                if self._stop_event.wait(timeout=remaining):
                    break

            self._running = False
            logger.info("PipelineScheduler stopped.")

        if blocking:
            # Set up graceful OS signal handlers
            def _signal_handler(signum, frame):
                logger.info("Received termination signal (%d). Shutting down scheduler gracefully...", signum)
                self.stop()

            try:
                signal.signal(signal.SIGINT, _signal_handler)
                if hasattr(signal, "SIGTERM"):
                    signal.signal(signal.SIGTERM, _signal_handler)
            except Exception:
                pass  # In non-main thread signals may not be bindable

            _worker()
        else:
            self._thread = threading.Thread(target=_worker, name="ForecastPipelineSchedulerThread", daemon=True)
            self._thread.start()

    def stop(self):
        """Stops the recurring schedule gracefully."""
        if not self._running:
            return
        logger.info("Signaling PipelineScheduler to halt...")
        self._stop_event.set()
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
