from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ObservationRecord(BaseModel):
    """
    Standardized Ground-Truth Weather Observation Record.
    Contains concurrent multi-variable measurements at a specific time and location.
    All values are stored in canonical units:
      - temperature: Celsius (°C)
      - rainfall: Millimeters (mm)
      - wind_speed: Kilometers per hour (km/h)
      - wind_direction: Degrees clockwise from True North (0-360°)
    """
    timestamp: datetime = Field(description="Observation valid timestamp (UTC or local)")
    latitude: float = Field(ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(ge=-180.0, le=180.0, description="Longitude in decimal degrees")

    # Multi-variable observed values
    temperature: Optional[float] = Field(default=None, description="Observed 2m temperature (°C)")
    rainfall: Optional[float] = Field(default=None, ge=0.0, description="Observed rainfall / precipitation (mm)")
    wind_speed: Optional[float] = Field(default=None, ge=0.0, description="Observed 10m wind speed (km/h)")
    wind_direction: Optional[float] = Field(default=None, ge=0.0, le=360.0, description="Observed wind direction (degrees)")

    # Metadata & Quality Assurance
    station_id: Optional[str] = Field(default=None, description="Observatory / Station code")
    station_name: Optional[str] = Field(default=None, description="Observatory name")
    elevation_m: Optional[float] = Field(default=None, description="Elevation in meters above MSL")
    source: str = Field(default="IMD_GROUND_TRUTH", description="Observation network or data provider")
    quality_flags: Dict[str, str] = Field(
        default_factory=dict,
        description="Per-variable quality flags, e.g. {'rainfall': 'VALID', 'temperature': 'CLAMPED'}"
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        return round(v, 4)

    @field_validator("temperature", "rainfall", "wind_speed", "wind_direction")
    @classmethod
    def round_values(cls, v: Optional[float]) -> Optional[float]:
        return round(v, 2) if v is not None else None


class ObservationValidationIssue(BaseModel):
    record_index: Optional[int] = None
    station_id: Optional[str] = None
    field: str
    issue_type: str  # "MISSING_VALUE", "OUT_OF_BOUNDS", "PARSING_ERROR", "UNIT_CONVERTED"
    message: str
    action_taken: str  # "CLAMPED", "FLAGGED", "CONVERTED", "DROPPED"
    original_value: Optional[Any] = None
    resolved_value: Optional[Any] = None


class ObservationIngestionReport(BaseModel):
    source_name: str
    source_file: Optional[str] = None
    total_records_read: int = 0
    valid_records_count: int = 0
    records_with_missing_vars: int = 0
    rejected_records_count: int = 0
    issues: List[ObservationValidationIssue] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0

    def mark_complete(self):
        self.completed_at = datetime.now()
        self.duration_ms = round((self.completed_at - self.started_at).total_seconds() * 1000.0, 2)
