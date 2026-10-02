import pytest
import os
from datetime import datetime, timezone
import sys
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import db
from analytics.live.openf1.auth import OpenF1AuthService
from analytics.live.openf1.mapper import OpenF1EventMapper
from analytics.live.state import CanonicalRaceState
from analytics.live.processor import process_event
from analytics.live.engine import LiveDecisionEngine, CandidateGenerator
from analytics.live.replay_adapter import ReplayStreamAdapter

@pytest.fixture(scope="module")
def setup_db():
    db.connect()

def test_auth_configuration():
    os.environ["OPENF1_USERNAME"] = "test_user"
    os.environ["OPENF1_PASSWORD"] = "test_pass"
    auth = OpenF1AuthService()
    assert auth.username == "test_user"
    assert auth.password == "test_pass"

def test_openf1_event_mapping():
    payload = {
        "session_key": 9213,
        "date": "2023-10-22T20:40:41.809000Z",
        "driver_number": 77,
        "position": 5
    }
    events = list(OpenF1EventMapper.map_message("v1/positions", payload))
    assert len(events) == 1
    ev = events[0]
    assert ev.session_key == 9213
    assert ev.payload["position"] == 5
    assert ev.source == "openf1.v1/positions"
    assert ev.timestamp == datetime(2023, 10, 22, 20, 40, 41, 809000, tzinfo=timezone.utc)

def test_candidate_generation():
    generator = CandidateGenerator()
    candidates = generator.generate(current_lap=10, max_laps=57)
    # Expected: Stay out + 3 options per compound
    assert len(candidates) > 1
    assert candidates[0] == [] # Stay out

def test_stale_weather_withholds_decision(setup_db):
    state = CanonicalRaceState(session_key=123, stale_threshold_seconds=60)
    # Simulate weather update long ago
    state.weather.last_update = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    
    engine = LiveDecisionEngine(db, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')))
    engine.throttle_seconds = 0
    
    current_time = datetime(2023, 1, 1, 12, 2, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    decision = engine.evaluate(state, material_change=True, current_time=current_time)
    
    assert decision is not None
    assert decision.selected_strategy == "DECISION_WITHHELD"
    assert decision.explanation == "STALE_WEATHER"
    
def test_replay_live_equivalence(setup_db):
    session_key = 7953
    adapter = ReplayStreamAdapter(db, session_key)
    
    state = CanonicalRaceState(session_key=session_key)
    engine = LiveDecisionEngine(db, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')))
    engine.throttle_seconds = 0
    
    decisions = []
    
    # Simulate live loop
    for event in adapter.generate_events():
        state, material_change = process_event(state, event)
        decision = engine.evaluate(state, material_change, current_time=event.timestamp)
        if decision and decision.selected_strategy != "DECISION_WITHHELD":
            decisions.append(decision)
            
    assert len(decisions) > 0
    # Final state should be identical
    assert state.current_leader_lap == 57
    assert state.driver_states[1].current_lap == 57
