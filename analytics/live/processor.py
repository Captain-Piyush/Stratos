from typing import Tuple, Dict, Any, Optional
from datetime import datetime
import logging
from analytics.live.events import RaceEvent, EventType
from analytics.live.state import CanonicalRaceState, SessionState, DriverState

logger = logging.getLogger(__name__)

class EventOrderingPolicy:
    @staticmethod
    def is_valid_update(current_update_time: Optional[datetime], new_event_time: datetime) -> bool:
        if not current_update_time:
            return True
        # Reject out of order/older events
        return new_event_time >= current_update_time

def _get_or_create_driver(state: CanonicalRaceState, driver_number: int, timestamp: datetime) -> DriverState:
    if driver_number not in state.driver_states:
        state.driver_states[driver_number] = DriverState(
            driver_number=driver_number,
            last_update=timestamp
        )
    return state.driver_states[driver_number]

def process_event(state: CanonicalRaceState, event: RaceEvent) -> Tuple[CanonicalRaceState, bool]:
    """
    Process an event deterministically and return the updated state and a boolean indicating
    if a material decision trigger occurred.
    """
    material_change = False
    
    # Global staleness update based on event time
    if not state.last_event_timestamp or event.timestamp >= state.last_event_timestamp:
        state.last_event_timestamp = event.timestamp
    
    if event.event_type == EventType.SESSION_STARTED:
        state.global_status = SessionState.GREEN
        
    elif event.event_type == EventType.SESSION_FINISHED:
        state.global_status = SessionState.FINISHED
        
    elif event.event_type == EventType.LAP_COMPLETED:
        driver = _get_or_create_driver(state, event.payload['driver_number'], event.timestamp)
        if EventOrderingPolicy.is_valid_update(driver.last_update, event.timestamp):
            new_lap = event.payload.get('lap_number', driver.current_lap + 1)
            if new_lap > driver.current_lap:
                driver.current_lap = new_lap
                driver.tyre_age += 1
                if event.payload.get('lap_duration'):
                    driver.last_lap_time = event.payload['lap_duration']
                    driver.lap_history.append(driver.last_lap_time)
                driver.last_update = event.timestamp
                material_change = True
                if new_lap > state.current_leader_lap:
                    state.current_leader_lap = new_lap

    elif event.event_type == EventType.POSITION_UPDATE:
        driver = _get_or_create_driver(state, event.payload['driver_number'], event.timestamp)
        if EventOrderingPolicy.is_valid_update(driver.last_update, event.timestamp):
            driver.position = event.payload.get('position')
            driver.last_update = event.timestamp
            
            # If coordinates are present, flag GPS as available
            if 'x' in event.payload or 'y' in event.payload:
                state.gps_available = True
            
    elif event.event_type == EventType.INTERVAL_UPDATE:
        driver = _get_or_create_driver(state, event.payload['driver_number'], event.timestamp)
        if EventOrderingPolicy.is_valid_update(driver.last_update, event.timestamp):
            driver.gap_to_leader = event.payload.get('gap_to_leader')
            driver.interval_to_ahead = event.payload.get('interval')
            driver.last_update = event.timestamp
            
    elif event.event_type == EventType.STINT_UPDATE:
        driver = _get_or_create_driver(state, event.payload['driver_number'], event.timestamp)
        if EventOrderingPolicy.is_valid_update(driver.last_update, event.timestamp):
            driver.current_compound = event.payload.get('compound', 'UNKNOWN')
            driver.tyre_age = event.payload.get('tyre_age_at_start', 0)
            driver.stints = event.payload.get('stint_number', 1)
            driver.last_update = event.timestamp
            material_change = True
            
    elif event.event_type == EventType.PIT_EVENT:
        driver = _get_or_create_driver(state, event.payload['driver_number'], event.timestamp)
        if EventOrderingPolicy.is_valid_update(driver.last_update, event.timestamp):
            driver.is_in_pit = event.payload.get('is_pit', False)
            driver.last_update = event.timestamp
            material_change = True
            
    elif event.event_type == EventType.WEATHER_UPDATE:
        if EventOrderingPolicy.is_valid_update(state.weather.last_update, event.timestamp):
            state.weather.air_temperature = event.payload.get('air_temperature', state.weather.air_temperature)
            state.weather.track_temperature = event.payload.get('track_temperature', state.weather.track_temperature)
            state.weather.rainfall = event.payload.get('rainfall', state.weather.rainfall)
            state.weather.last_update = event.timestamp
            material_change = True
            
    elif event.event_type in [EventType.RACE_CONTROL, EventType.SAFETY_CAR, EventType.VSC, EventType.RED_FLAG, EventType.GREEN_FLAG]:
        new_status = state.global_status
        if event.event_type == EventType.SAFETY_CAR:
            new_status = SessionState.SAFETY_CAR
        elif event.event_type == EventType.VSC:
            new_status = SessionState.VSC
        elif event.event_type == EventType.RED_FLAG:
            new_status = SessionState.RED_FLAG
        elif event.event_type == EventType.GREEN_FLAG:
            new_status = SessionState.GREEN
        elif event.event_type == EventType.RACE_CONTROL:
            msg = str(event.payload.get('message', '')).upper()
            if 'SAFETY CAR' in msg and 'DEPLOYED' in msg:
                new_status = SessionState.SAFETY_CAR
            elif 'VIRTUAL SAFETY CAR' in msg and 'DEPLOYED' in msg:
                new_status = SessionState.VSC
            elif 'RED FLAG' in msg:
                new_status = SessionState.RED_FLAG
            elif 'CLEAR' in msg or 'GREEN' in msg:
                new_status = SessionState.GREEN
        
        if new_status != state.global_status:
            state.global_status = new_status
            material_change = True
            
    else:
        logger.warning(f"Unknown event type: {event.event_type}")

    return state, material_change
