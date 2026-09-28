from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DataCategory(str, Enum):
    """
    Strict data category classifying the authenticity and origin of meteorological data.
    Ensures simulated, synthetic, or benchmark datasets are never misrepresented
    as real operational observations.
    """
    REAL_DATA = "REAL DATA"
    SIMULATED_DATA = "SIMULATED DATA"
    DEMO_DATA = "DEMO DATA"


class DataProvenance(BaseModel):
    """
    Metadata capturing the pedigree, origin, authenticity, and legal/scientific disclaimer
    of an ingested meteorological dataset.
    """
    category: DataCategory = Field(description="Strict provenance category")
    label: str = Field(description="Human-readable provenance tag ('REAL DATA', 'SIMULATED DATA', 'DEMO DATA')")
    provider: str = Field(description="Organization, API, sensor network, or simulation engine")
    description: str = Field(description="Detailed description of dataset origin and methodology")
    disclaimer: Optional[str] = Field(default=None, description="Scientific or operational disclaimer")
    is_real: bool = Field(default=False, description="True ONLY if derived from actual atmospheric sensors or operational NWP")
    is_simulated: bool = Field(default=False, description="True if mathematically/synthetically generated")
    is_demo: bool = Field(default=False, description="True if canned prototype/hackathon sample files")
    citation_or_url: Optional[str] = Field(default=None, description="Public DOI, URL, or API documentation")
    license: Optional[str] = Field(default=None, description="Data usage terms (e.g. WMO Resolution 40, Open Database License)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional ingestion provenance flags")

    @classmethod
    def create_real(
        cls,
        provider: str,
        description: str,
        citation_or_url: Optional[str] = None,
        license: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DataProvenance":
        """Factory for genuine operational observations or verified NWP model outputs."""
        return cls(
            category=DataCategory.REAL_DATA,
            label="REAL DATA",
            provider=provider,
            description=description,
            disclaimer="VERIFIED OPERATIONAL/OBSERVATIONAL DATA: Subject to standard sensor calibration and QA protocols.",
            is_real=True,
            is_simulated=False,
            is_demo=False,
            citation_or_url=citation_or_url,
            license=license or "Open Public Sector Meteorology Data",
            metadata=metadata or {},
        )

    @classmethod
    def create_simulated(
        cls,
        provider: str = "Physics-based Synthetic Numerical Simulator",
        description: str = "Synthetically generated atmospheric profile based on hydrodynamic and thermodynamic equations.",
        citation_or_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DataProvenance":
        """Factory for synthetic, numerical, or perturbed model simulation feeds."""
        return cls(
            category=DataCategory.SIMULATED_DATA,
            label="SIMULATED DATA",
            provider=provider,
            description=description,
            disclaimer=(
                "CRITICAL DISCLAIMER: THIS IS SIMULATED / SYNTHETIC DATA GENERATED VIA NUMERICAL RULES. "
                "IT IS NOT REAL IN-SITU OBSERVATIONAL TELEMETRY AND MUST NOT BE PRESENTED AS GROUND TRUTH."
            ),
            is_real=False,
            is_simulated=True,
            is_demo=False,
            citation_or_url=citation_or_url,
            license="Synthetic Testing / Academic Simulation",
            metadata=metadata or {},
        )

    @classmethod
    def create_demo(
        cls,
        provider: str = "MOES Prototype Sample Fixture Repository",
        description: str = "Static benchmark demonstration fixture bundled for offline development, SIH evaluation, and regression testing.",
        citation_or_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "DataProvenance":
        """Factory for packaged sample files (CSV/JSON/NetCDF demo files)."""
        return cls(
            category=DataCategory.DEMO_DATA,
            label="DEMO DATA",
            provider=provider,
            description=description,
            disclaimer=(
                "PROTOTYPE DEMONSTRATION DATA: Canned static test fixture for pipeline demonstration and offline unit testing."
            ),
            is_real=False,
            is_simulated=False,
            is_demo=True,
            citation_or_url=citation_or_url,
            license="Research and Development Prototype License",
            metadata=metadata or {},
        )
