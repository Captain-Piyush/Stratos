import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app import app

from backend.app import app, app_state
from analytics.live.state import CanonicalRaceState

def test_fastapi_outcomes_endpoint():
    with TestClient(app) as client:
        app_state.active_session_key = 7953
        app_state.canonical_state = CanonicalRaceState(session_key=7953, current_leader_lap=40)
        
        # Test that the historical outcome endpoint is reachable
        # Using Bahrain 2023 (session 7953), driver 1 (VER), Lap 30
        response = client.get("/api/outcomes/7953/1/30")
        assert response.status_code == 200
        data = response.json()
        assert "outcome_status" in data
        assert "actual_pit_laps" in data
    
def test_historical_outcome_structure():
    with TestClient(app) as client:
        app_state.active_session_key = 9213
        app_state.canonical_state = CanonicalRaceState(session_key=9213, current_leader_lap=20)
        # Verify the structure matches the frontend TypeScript interface requirements
        response = client.get("/api/outcomes/9213/1/10")
        data = response.json()
        
        assert "actual_strategy" in data
        assert "pit_source" in data
        assert "strategy_source" in data
        assert "actual_compounds" in data
        assert "actual_finish_position" in data
        assert "actual_race_time" in data
        assert "actual_outcome_from_decision_point" in data
        assert "retirement_lap" in data
        assert "retirement_reason" in data

def test_demo_flow_bahrain_lap30():
    with TestClient(app) as client:
        app_state.active_session_key = 7953
        app_state.canonical_state = CanonicalRaceState(session_key=7953, current_leader_lap=40)
        # The demo flow explicitly tests Bahrain 2023, Driver VER, Lap 30
        response = client.get("/api/outcomes/7953/1/30")
        data = response.json()
        assert data["outcome_status"] in ["FINISHED", "RETIRED", "UNKNOWN"]
