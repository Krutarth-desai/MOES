import math
from datetime import timedelta
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from backend.app.data.ingestion.schema import ForecastVariable, StandardForecastRecord
from backend.app.data.observation.schema import ObservationRecord
from backend.app.utils.geo import haversine_distance_km


class MatchingConfig(BaseModel):
    max_spatial_distance_km: float = Field(
        default=40.0,
        description="Maximum permissible great-circle distance between forecast point and station"
    )
    max_temporal_offset_minutes: int = Field(
        default=60,
        description="Maximum permissible time difference between forecast valid time and observation"
    )
    prefer_station_id_match: bool = Field(
        default=True,
        description="Prioritize exact observatory ID match before geometric distance search"
    )


class MatchedPair(BaseModel):
    """
    Linked pair connecting a single forecast prediction with its verified ground-truth measurement.
    """
    model_name: str
    station_id: Optional[str]
    region: str
    lead_time_hours: int
    variable: ForecastVariable
    forecast_timestamp: str
    observation_timestamp: str

    # Coordinate alignment
    forecast_lat: float
    forecast_lon: float
    observation_lat: float
    observation_lon: float
    spatial_distance_km: float
    temporal_offset_minutes: float

    # Verified values and error metrics
    forecast_value: float
    observed_value: float
    error: float = Field(description="Signed forecast error: (forecast - observed)")
    absolute_error: float = Field(description="Absolute error: |forecast - observed|")
    squared_error: float = Field(description="Squared error: (forecast - observed)^2")


class SpatialTemporalMatcher:
    """
    Aligns and pairs multi-model forecast predictions with ground-truth observations.
    Performs dual spatial-temporal matching with configurable tolerance windows.
    """

    def __init__(self, config: Optional[MatchingConfig] = None):
        self.config = config or MatchingConfig()

    def match(
        self,
        forecast_records: List[StandardForecastRecord],
        observation_records: List[ObservationRecord],
    ) -> List[MatchedPair]:
        matched_pairs: List[MatchedPair] = []
        if not forecast_records or not observation_records:
            return matched_pairs

        # 1. Index observations for fast matching
        # Key: (station_id, observation_timestamp) -> ObservationRecord
        station_time_index: Dict[Tuple[str, str], ObservationRecord] = {}
        for obs in observation_records:
            if obs.station_id:
                # Key by station and truncated minute string
                key = (obs.station_id.upper(), obs.timestamp.strftime("%Y-%m-%d %H:%M"))
                station_time_index[key] = obs

        # 2. Iterate through forecasts
        for fcst in forecast_records:
            # Verified valid timestamp
            target_time = fcst.timestamp
            target_var = fcst.forecast_variable
            matched_obs: Optional[ObservationRecord] = None
            dist_km: float = 0.0
            time_offset_min: float = 0.0

            # Attempt 1: Exact Station ID & Timestamp Match
            if self.config.prefer_station_id_match and fcst.station_id:
                direct_key = (fcst.station_id.upper(), target_time.strftime("%Y-%m-%d %H:%M"))
                if direct_key in station_time_index:
                    candidate = station_time_index[direct_key]
                    matched_obs = candidate
                    dist_km = haversine_distance_km(fcst.latitude, fcst.longitude, candidate.latitude, candidate.longitude)
                    time_offset_min = 0.0

            # Attempt 2: Spatiotemporal search across tolerance windows
            if not matched_obs:
                best_dist = float("inf")
                best_candidate: Optional[ObservationRecord] = None
                best_offset_min: float = float("inf")

                for obs in observation_records:
                    # Check temporal window: |t_obs - t_fcst| <= tolerance
                    offset_seconds = abs((obs.timestamp - target_time).total_seconds())
                    offset_minutes = offset_seconds / 60.0
                    if offset_minutes > self.config.max_temporal_offset_minutes:
                        continue

                    # If station_id matches, strongly prefer
                    if fcst.station_id and obs.station_id and fcst.station_id.upper() == obs.station_id.upper():
                        best_candidate = obs
                        best_dist = haversine_distance_km(fcst.latitude, fcst.longitude, obs.latitude, obs.longitude)
                        best_offset_min = offset_minutes
                        break

                    # Check spatial distance
                    d = haversine_distance_km(fcst.latitude, fcst.longitude, obs.latitude, obs.longitude)
                    if d <= self.config.max_spatial_distance_km:
                        # Minimize combined space-time cost
                        if d < best_dist:
                            best_dist = d
                            best_candidate = obs
                            best_offset_min = offset_minutes

                if best_candidate:
                    matched_obs = best_candidate
                    dist_km = best_dist
                    time_offset_min = best_offset_min

            if not matched_obs:
                continue

            # Extract the corresponding observed variable
            obs_val: Optional[float] = None
            if target_var == ForecastVariable.TEMPERATURE:
                obs_val = matched_obs.temperature
            elif target_var == ForecastVariable.RAINFALL:
                obs_val = matched_obs.rainfall
            elif target_var == ForecastVariable.WIND_SPEED:
                obs_val = matched_obs.wind_speed
            elif target_var == ForecastVariable.WIND_DIRECTION:
                obs_val = matched_obs.wind_direction

            if obs_val is None:
                # Target variable missing from observation
                continue

            # Calculate forecast errors
            signed_err = round(fcst.forecast_value - obs_val, 2)
            abs_err = round(abs(signed_err), 2)
            sq_err = round(signed_err ** 2, 4)

            pair = MatchedPair(
                model_name=fcst.source_name,
                station_id=fcst.station_id or matched_obs.station_id,
                region=fcst.region,
                lead_time_hours=fcst.lead_time_hours,
                variable=target_var,
                forecast_timestamp=target_time.isoformat(),
                observation_timestamp=matched_obs.timestamp.isoformat(),
                forecast_lat=fcst.latitude,
                forecast_lon=fcst.longitude,
                observation_lat=matched_obs.latitude,
                observation_lon=matched_obs.longitude,
                spatial_distance_km=round(dist_km, 2),
                temporal_offset_minutes=round(time_offset_min, 1),
                forecast_value=fcst.forecast_value,
                observed_value=obs_val,
                error=signed_err,
                absolute_error=abs_err,
                squared_error=sq_err,
            )
            matched_pairs.append(pair)

        return matched_pairs
