import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.app.config.settings import DATA_DIR
from backend.app.services.backtesting.schemas import (
    BacktestRunResult,
    ComparisonReportRow,
)

logger = logging.getLogger("moes.backtesting.store")
DEFAULT_BACKTEST_STORE_PATH = DATA_DIR / "processed" / "backtest_results.json"


class BacktestResultStore:
    """
    Persistent repository for historical backtesting and skill comparison run artifacts.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_BACKTEST_STORE_PATH
        self._runs: Dict[str, BacktestRunResult] = {}
        self._latest_id: Optional[str] = None
        self.load()

    def save_run(self, result: BacktestRunResult):
        """Stores and persists a backtesting run result."""
        self._runs[result.backtest_id] = result
        self._latest_id = result.backtest_id
        self.save()

    def get_latest(self) -> Optional[BacktestRunResult]:
        """Retrieves the most recent backtest execution result."""
        if not self._latest_id:
            if self._runs:
                # Fallback to newest by evaluated_at
                latest = max(self._runs.values(), key=lambda r: r.evaluated_at)
                self._latest_id = latest.backtest_id
                return latest
            return None
        return self._runs.get(self._latest_id)

    def get_by_id(self, backtest_id: str) -> Optional[BacktestRunResult]:
        """Retrieves a specific run by deterministic ID."""
        return self._runs.get(backtest_id)

    def query_report_rows(
        self,
        backtest_id: Optional[str] = None,
        variable: Optional[str] = None,
        lead_time_hours: Optional[int] = None,
        region: Optional[str] = None,
        model_name: Optional[str] = None,
        metric: Optional[str] = None,
    ) -> List[ComparisonReportRow]:
        """
        Filters and queries dimensional comparison report rows (model | variable | lead time | region | metric).
        """
        run = self.get_by_id(backtest_id) if backtest_id else self.get_latest()
        if not run:
            return []

        rows = run.dimensional_report

        if variable:
            v_clean = variable.strip().lower()
            rows = [r for r in rows if v_clean in r.variable.lower()]
        if lead_time_hours is not None:
            rows = [r for r in rows if r.lead_time_hours == lead_time_hours]
        if region:
            r_clean = region.strip().lower()
            rows = [r for r in rows if r.region and r_clean in r.region.lower()]
        if model_name:
            m_clean = model_name.strip().lower()
            rows = [r for r in rows if m_clean in r.model_name.lower()]
        if metric:
            met_clean = metric.strip().upper()
            rows = [r for r in rows if r.metric.upper() == met_clean]

        return rows

    def clear(self):
        """Clears memory and persisted file."""
        self._runs.clear()
        self._latest_id = None
        if self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception as e:
                logger.warning("Could not delete backtest store file: %s", e)

    def save(self):
        """Saves repository to disk as JSON."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "total_runs": len(self._runs),
                "latest_id": self._latest_id,
                "saved_at": datetime.now().isoformat(),
                "runs": [r.model_dump(mode="json") for r in self._runs.values()],
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to persist backtest results: %s", e)

    def load(self):
        """Loads repository from disk."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            runs_list = data.get("runs", [])
            for r_dict in runs_list:
                try:
                    obj = BacktestRunResult.model_validate(r_dict)
                    self._runs[obj.backtest_id] = obj
                except Exception as e:
                    logger.warning("Failed to deserialize backtest run: %s", e)
            self._latest_id = data.get("latest_id") or (max(self._runs.values(), key=lambda r: r.evaluated_at).backtest_id if self._runs else None)
            logger.info("Loaded %d backtest run records from %s", len(self._runs), self.storage_path)
        except Exception as e:
            logger.error("Error reading backtest store: %s", e)
