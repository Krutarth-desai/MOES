from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Graceful fallback if pydantic-settings is not yet installed
    class BaseSettings(BaseModel):
        pass
    SettingsConfigDict = None

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "configs"
DATA_DIR = ROOT_DIR / "data"
SAMPLE_DIR = DATA_DIR / "sample"


class DomainConfig(BaseModel):
    name: str = "India-SouthAsia"
    min_lat: float = 6.0
    max_lat: float = 38.5
    min_lon: float = 68.0
    max_lon: float = 98.5
    resolution: float = 0.25


class ModelMetadata(BaseModel):
    id: str
    name: str
    category: str  # "nwp" or "ai"
    native_resolution: float = 0.25


class Settings(BaseSettings):
    app_name: str = "Hybrid AI-NWP Forecast Blending System"
    app_version: str = "0.1.0"
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: List[str] = ["*"]

    # Active provider type: "simulated", "openmeteo", "ecmwf_opendata", "custom"
    forecast_provider: str = "simulated"

    # Domain bounds
    domain: DomainConfig = Field(default_factory=DomainConfig)

    # Lead times supported in hours
    lead_times_hours: List[int] = [24, 48, 72, 96, 120, 144, 168]

    # Models tracked in the blending engine
    active_models: List[ModelMetadata] = [
        ModelMetadata(id="gfs", name="NOAA GFS", category="nwp"),
        ModelMetadata(id="ecmwf", name="ECMWF IFS", category="nwp"),
        ModelMetadata(id="graphcast", name="DeepMind GraphCast", category="ai"),
        ModelMetadata(id="pangu", name="Pangu-Weather", category="ai"),
    ]

    # Config directory path
    config_dir: Path = CONFIG_DIR

    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )


settings = Settings()
