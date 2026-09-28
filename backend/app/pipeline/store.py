import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.config.settings import DATA_DIR
from backend.app.pipeline.schemas import PipelineExecutionReport

logger = logging.getLogger("moes.pipeline.store")
LATEST_RUN_PATH = DATA_DIR / "processed" / "latest_pipeline_run.json"
HISTORY_PATH = DATA_DIR / "processed" / "pipeline_history.json"


class PipelineRunStore:
    """
    Persistence store for automated pipeline execution reports and telemetry.
    """

    def __init__(
        self,
        latest_file: Optional[Path] = None,
        history_file: Optional[Path] = None,
    ):
        self._latest_file = latest_file or LATEST_RUN_PATH
        self._history_file = history_file or HISTORY_PATH
        self._cached_latest: Optional[PipelineExecutionReport] = None
        self._load_latest()

    def _load_latest(self):
        if not self._latest_file.exists():
            return
        try:
            with open(self._latest_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cached_latest = PipelineExecutionReport.model_validate(data)
        except Exception as e:
            logger.warning("Could not deserialize latest pipeline run: %s", e)

    def save_run(self, report: PipelineExecutionReport):
        """Save a new pipeline run report."""
        self._cached_latest = report
        try:
            self._latest_file.parent.mkdir(parents=True, exist_ok=True)
            report_dict = report.model_dump(mode="json")

            with open(self._latest_file, "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=str)

            # Append to history
            history: List[Dict[str, Any]] = []
            if self._history_file.exists():
                try:
                    with open(self._history_file, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    history = []

            history.append(report_dict)
            history = history[-50:]

            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, default=str)

        except Exception as e:
            logger.error("Failed to persist pipeline run report: %s", e)

    def get_latest_run(self) -> Optional[PipelineExecutionReport]:
        """Returns the most recent pipeline execution report."""
        if not self._cached_latest:
            self._load_latest()
        return self._cached_latest

    def get_history(self, limit: int = 20) -> List[PipelineExecutionReport]:
        """Returns historical pipeline runs."""
        if not self._history_file.exists():
            if self._cached_latest:
                return [self._cached_latest]
            return []

        try:
            with open(self._history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            reports = []
            for item in reversed(history):
                try:
                    reports.append(PipelineExecutionReport.model_validate(item))
                    if len(reports) >= limit:
                        break
                except Exception:
                    pass
            return reports
        except Exception as e:
            logger.warning("Error reading pipeline history: %s", e)
            return []

    def clear(self):
        """Resets the store (primarily for unit tests)."""
        self._cached_latest = None
        if self._latest_file.exists():
            try:
                self._latest_file.unlink()
            except Exception:
                pass
        if self._history_file.exists():
            try:
                self._history_file.unlink()
            except Exception:
                pass
