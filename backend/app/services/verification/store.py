import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from backend.app.config.settings import DATA_DIR
from backend.app.data.ingestion.schema import ForecastVariable, Season, WeatherRegime
from backend.app.services.verification.schemas import (
    ComprehensiveSkillScore,
    HistoricalSkillRecord,
    MetricDimensionSlice,
)

logger = logging.getLogger("moes.verification.store")
SKILL_STORE_PATH = DATA_DIR / "processed" / "historical_skill_scores.json"


_STORE_DEFAULT = object()


class SkillScoreStore:
    """
    Persistent repository for historical model verification skill scores.
    Enables rapid hierarchical querying for adaptive multi-model weighting.
    """

    def __init__(self, storage_path: Optional[Path] = _STORE_DEFAULT, in_memory: bool = False):
        if storage_path is _STORE_DEFAULT:
            self.storage_path = SKILL_STORE_PATH
            self.in_memory = in_memory
        else:
            self.storage_path = storage_path
            self.in_memory = in_memory or (storage_path is None)

        self._records: List[HistoricalSkillRecord] = []
        if not self.in_memory and self.storage_path:
            self.load()

    def add_record(self, record: HistoricalSkillRecord):
        # Replace existing matching slice if present
        self._records = [
            r for r in self._records
            if not self._slices_match(r.dimension, record.dimension)
        ]
        self._records.append(record)

    def add_records(self, records: List[HistoricalSkillRecord]):
        if not records:
            return
        incoming_keys = {self._dimension_key(r.dimension) for r in records}
        self._records = [
            r for r in self._records
            if self._dimension_key(r.dimension) not in incoming_keys
        ]
        self._records.extend(records)
        self.save()

    def get_all_records(self) -> List[HistoricalSkillRecord]:
        return self._records

    def query(
        self,
        model_name: Optional[str] = None,
        variable: Optional[ForecastVariable] = None,
        lead_time_hours: Optional[int] = None,
        region: Optional[str] = None,
        season: Optional[Season] = None,
        weather_regime: Optional[WeatherRegime] = None,
    ) -> List[HistoricalSkillRecord]:
        results = self._records

        if model_name:
            results = [r for r in results if model_name.lower() in r.dimension.model_name.lower()]
        if variable:
            results = [r for r in results if r.dimension.variable == variable]
        if lead_time_hours is not None:
            results = [r for r in results if r.dimension.lead_time_hours == lead_time_hours]
        if region:
            results = [r for r in results if r.dimension.region and region.lower() in r.dimension.region.lower()]
        if season:
            results = [r for r in results if r.dimension.season == season]
        if weather_regime:
            results = [r for r in results if r.dimension.weather_regime == weather_regime]

        return results

    def get_adaptive_skill_weight(
        self,
        model_name: str,
        variable: ForecastVariable,
        lead_time_hours: int,
        region: Optional[str] = None,
        season: Optional[Season] = None,
        weather_regime: Optional[WeatherRegime] = None,
    ) -> float:
        """
        Hierarchical retrieval for adaptive weighting engine:
        1. Exact (Model, Variable, LeadTime, Region, Regime)
        2. Region & LeadTime fallback
        3. LeadTime fallback
        4. Overall Model Variable fallback
        5. Safe default: 0.50
        """
        # 1. Exact match
        matches = self.query(
            model_name=model_name,
            variable=variable,
            lead_time_hours=lead_time_hours,
            region=region,
            weather_regime=weather_regime,
        )
        if matches:
            return matches[0].metrics.composite_skill_score

        # 2. Lead time & Region fallback
        matches = self.query(
            model_name=model_name,
            variable=variable,
            lead_time_hours=lead_time_hours,
            region=region,
        )
        if matches:
            return matches[0].metrics.composite_skill_score

        # 3. Lead time fallback
        matches = self.query(
            model_name=model_name,
            variable=variable,
            lead_time_hours=lead_time_hours,
        )
        if matches:
            return matches[0].metrics.composite_skill_score

        # 4. Overall model skill fallback
        matches = self.query(model_name=model_name, variable=variable)
        if matches:
            return matches[0].metrics.composite_skill_score

        return 0.50

    def save(self):
        """Persist records to disk in structured JSON format."""
        if self.in_memory or not self.storage_path:
            return
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            serializable = [r.model_dump(mode="json") for r in self._records]
            with open(self.storage_path, mode="w", encoding="utf-8") as f:
                json.dump({"total_records": len(self._records), "records": serializable}, f, indent=2)
            logger.info("Saved %d historical skill records to %s", len(self._records), self.storage_path.name)
        except Exception as e:
            logger.exception("Failed to save historical skill store: %s", e)

    def load(self):
        """Load records from disk if present."""
        if self.in_memory or not self.storage_path or not self.storage_path.exists():
            return
        try:
            with open(self.storage_path, mode="r", encoding="utf-8") as f:
                data = json.load(f)
            raw_list = data.get("records", [])
            self._records = [HistoricalSkillRecord.model_validate(r) for r in raw_list]
            logger.info("Loaded %d historical skill records from %s", len(self._records), self.storage_path.name)
        except Exception as e:
            logger.warning("Could not read skill store from %s: %s", self.storage_path, e)

    def clear(self):
        self._records.clear()
        if not self.in_memory and self.storage_path and self.storage_path.exists():
            try:
                self.storage_path.unlink()
            except Exception:
                pass

    @staticmethod
    def _dimension_key(s: MetricDimensionSlice) -> tuple:
        return (
            s.model_name.lower(),
            s.variable,
            s.region,
            s.lead_time_hours,
            s.season,
            s.weather_regime,
        )

    @staticmethod
    def _slices_match(s1: MetricDimensionSlice, s2: MetricDimensionSlice) -> bool:
        return (
            s1.model_name.lower() == s2.model_name.lower()
            and s1.variable == s2.variable
            and s1.region == s2.region
            and s1.lead_time_hours == s2.lead_time_hours
            and s1.season == s2.season
            and s1.weather_regime == s2.weather_regime
        )
