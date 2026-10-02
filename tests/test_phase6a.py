import pytest
from datetime import datetime, timezone
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import db
from analytics.live.events import RaceEvent, EventType
from analytics.live.state import CanonicalRaceState, SessionState
from analytics.live.processor import process_event
from analytics.live.replay_adapter import ReplayStreamAdapter

@pytest.fixture(scope="module")
def setup_db():
    db.connect()

def test_event_ordering_and_duplicate():
    state = CanonicalRaceState(session_key=123)
    t1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2023, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
    
    # Process event
    ev1 = RaceEvent(session_key=123, timestamp=t1, event_type=EventType.POSITION_UPDATE, source="test", payload={"driver_number": 1, "position": 2})
    process_event(state, ev1)
    assert state.driver_states[1].position == 2
    
    # Process older event (out of order, should be ignored)
    t0 = datetime(2023, 1, 1, 11, 59, 0, tzinfo=timezone.utc)
    ev0 = RaceEvent(session_key=123, timestamp=t0, event_type=EventType.POSITION_UPDATE, source="test", payload={"driver_number": 1, "position": 5})
    process_event(state, ev0)
    assert state.driver_states[1].position == 2
    
    # Process duplicate event (same timestamp)
    ev1_dup = RaceEvent(session_key=123, timestamp=t1, event_type=EventType.POSITION_UPDATE, source="test", payload={"driver_number": 1, "position": 10})
    process_event(state, ev1_dup)
    assert state.driver_states[1].position == 10  # Idempotently overwrites with same timestamp if it arrives

    # Process newer event
    ev2 = RaceEvent(session_key=123, timestamp=t2, event_type=EventType.POSITION_UPDATE, source="test", payload={"driver_number": 1, "position": 1})
    process_event(state, ev2)
    assert state.driver_states[1].position == 1
    
def test_staleness_detection():
    state = CanonicalRaceState(session_key=123, stale_threshold_seconds=60)
    t1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ev1 = RaceEvent(session_key=123, timestamp=t1, event_type=EventType.POSITION_UPDATE, source="test", payload={"driver_number": 1, "position": 2})
    process_event(state, ev1)
    
    # check staleness with time < 60s
    state.check_staleness(current_time=datetime(2023, 1, 1, 12, 0, 30, tzinfo=timezone.utc))
    assert not state.driver_states[1].status_stale
    
    # check staleness with time > 60s
    state.check_staleness(current_time=datetime(2023, 1, 1, 12, 1, 30, tzinfo=timezone.utc))
    assert state.driver_states[1].status_stale

def test_safety_car_transitions():
    state = CanonicalRaceState(session_key=123)
    t1 = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ev = RaceEvent(session_key=123, timestamp=t1, event_type=EventType.RACE_CONTROL, source="test", payload={"message": "SAFETY CAR DEPLOYED"})
    process_event(state, ev)
    assert state.global_status == SessionState.SAFETY_CAR
    
    t2 = datetime(2023, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
    ev2 = RaceEvent(session_key=123, timestamp=t2, event_type=EventType.RACE_CONTROL, source="test", payload={"message": "CLEAR"})
    process_event(state, ev2)
    assert state.global_status == SessionState.GREEN
    
def test_replay_parity(setup_db):
    session_key = 7953
    adapter = ReplayStreamAdapter(db, session_key)
    
    state = CanonicalRaceState(session_key=session_key)
    for event in adapter.generate_events():
        process_event(state, event)
        
    assert state.global_status != SessionState.UNKNOWN
    # By the end of race 7953, Driver 1 should have 57 laps completed
    assert state.driver_states[1].current_lap == 57
    assert state.current_leader_lap == 57
