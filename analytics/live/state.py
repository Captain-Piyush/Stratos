from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum

class SessionState(str, Enum):
    PRE_RACE = "PRE_RACE"
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    VSC = "VSC"
    SAFETY_CAR = "SAFETY_CAR"
    RED_FLAG = "RED_FLAG"
    FINISHED = "FINISHED"
    UNKNOWN = "UNKNOWN"

class DriverState(BaseModel):
    driver_number: int
    current_lap: int = 0
    position: Optional[int] = None
    gap_to_leader: Optional[float] = None
    interval_to_ahead: Optional[float] = None
    current_compound: str = "UNKNOWN"
    tyre_age: int = 0
    stints: int = 1
    last_lap_time: Optional[float] = None
    is_in_pit: bool = False
    is_retired: bool = False
    last_update: datetime
    lap_history: List[float] = Field(default_factory=list)
    status_stale: bool = False

class WeatherState(BaseModel):
    air_temperature: Optional[float] = None
    track_temperature: Optional[float] = None
    rainfall: Optional[bool] = None
    last_update: Optional[datetime] = None
    status_stale: bool = False

class CanonicalRaceState(BaseModel):
    session_key: int
    race_distance: Optional[int] = None
    global_status: SessionState = SessionState.UNKNOWN
    current_leader_lap: int = 0
    driver_states: Dict[int, DriverState] = Field(default_factory=dict)
    weather: WeatherState = Field(default_factory=WeatherState)
    last_event_timestamp: Optional[datetime] = None
    stale_threshold_seconds: int = 300
    gps_available: bool = False

    def check_staleness(self, current_time: datetime = None):
        if current_time is None:
            current_time = datetime.now(timezone.utc)
            
        for driver in self.driver_states.values():
            if (current_time - driver.last_update).total_seconds() > self.stale_threshold_seconds:
                driver.status_stale = True
            else:
                driver.status_stale = False
                
        if self.weather.last_update and (current_time - self.weather.last_update).total_seconds() > self.stale_threshold_seconds:
            self.weather.status_stale = True
        else:
            self.weather.status_stale = False
