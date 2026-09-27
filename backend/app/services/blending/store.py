import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.config.settings import DATA_DIR
from backend.app.services.blending.schemas import BlendedForecastResult

logger = logging.getLogger("moes.blending.store")
BLENDED_STORE_PATH = DATA_DIR / "processed" / "blended_forecasts.json"


class BlendedForecastStore:
    """
    Storage repository for individual model forecasts and the final dynamically blended forecasts.
    Maintains fast in-memory indexing alongside persistent JSON storage.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or BLENDED_STORE_PATH
        self._records: Dict[str, BlendedForecastResult] = {}
        self.load()

    def save_blended_forecast(self, result: BlendedForecastResult):
        """Stores a blended forecast result."""
        self._records[result.forecast_id] = result
        self.save()

    def get_by_id(self, forecast_id: str) -> Optional[BlendedForecastResult]:
        """Retrieves a blended forecast by its unique ID."""
        return self._records.get(forecast_id)

    def query(
        self,
        station_id: Optional[str] = None,
        variable: Optional[str] = None,
        lead_time_hours: Optional[int] = None,
        limit: int = 50,
    ) -> List[BlendedForecastResult]:
        """Queries stored blended forecasts with filtering."""
        results = list(self._records.values())

        if station_id:
            s_clean = station_id.strip().upper()
            results = [r for r in results if r.station_id and r.station_id.upper() == s_clean]
        if variable:
            v_clean = variable.strip().lower()
            results = [r for r in results if v_clean in r.variable.lower()]
        if lead_time_hours is not None:
            results = [r for r in results if r.lead_time_hours == lead_time_hours]

        # Sort descending by timestamp / creation
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    def count(self) -> int:
        return len(self._records)

    def clear(self):
        """Resets the store (primarily for unit tests)."""
        self._records.clear()
        if self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception as e:
                logger.warning("Could not delete store file: %s", e)

    def save(self):
        """Persists records to disk as JSON."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = {
                "total_records": len(self._records),
                "saved_at": datetime.now().isoformat(),
                "records": [r.model_dump(mode="json") for r in self._records.values()],
            }
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2, default=str)
        except Exception as e:
            logger.error("Failed to persist blended forecasts: %s", e)

    def load(self):
        """Loads records from disk if available."""
        if not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            records = data.get("records", [])
            for rec in records:
                try:
                    obj = BlendedForecastResult.model_validate(rec)
                    self._records[obj.forecast_id] = obj
                except Exception as e:
                    logger.warning("Failed to deserialize blended record: %s", e)
            logger.info("Loaded %d blended forecasts from %s", len(self._records), self.storage_path)
        except Exception as e:
            logger.error("Error loading blended forecast store: %s", e)
