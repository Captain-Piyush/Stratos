from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_FINISHED = "SESSION_FINISHED"
    LAP_COMPLETED = "LAP_COMPLETED"
    POSITION_UPDATE = "POSITION_UPDATE"
    INTERVAL_UPDATE = "INTERVAL_UPDATE"
    STINT_UPDATE = "STINT_UPDATE"
    PIT_EVENT = "PIT_EVENT"
    WEATHER_UPDATE = "WEATHER_UPDATE"
    RACE_CONTROL = "RACE_CONTROL"
    SAFETY_CAR = "SAFETY_CAR"
    VSC = "VSC"
    RED_FLAG = "RED_FLAG"
    GREEN_FLAG = "GREEN_FLAG"
    
class RaceEvent(BaseModel):
    session_key: int
    timestamp: datetime
    event_type: EventType
    source: str
    payload: Dict[str, Any]
    sequence_number: Optional[int] = None
