import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app import app, app_state
from analytics.live.state import CanonicalRaceState

def test_outcome_endpoint_security():
    with TestClient(app) as client:
        # Mock the server state for Bahrain 2023
        app_state.active_session_key = 7953
        app_state.canonical_state = CanonicalRaceState(session_key=7953, current_leader_lap=30)
        
        # A. Cursor exactly at decision boundary (Lap 30) -> Should be LOCKED
        response_at = client.get("/api/outcomes/7953/1/30")
        assert response_at.json().get("outcome_status") == "OUTCOME_LOCKED"
        
        # B. Cursor before decision boundary (requesting Lap 35 when cursor is at 30) -> Should be LOCKED
        response_before = client.get("/api/outcomes/7953/1/35")
        assert response_before.json().get("outcome_status") == "OUTCOME_LOCKED"
        
        # C. Cursor after decision boundary (requesting Lap 25 when cursor is at 30) -> Should UNLOCK
        response_after = client.get("/api/outcomes/7953/1/25")
        assert response_after.json().get("outcome_status") not in ["OUTCOME_LOCKED"]
        
        # D. Moving replay cursor backward
        # Move cursor back to Lap 20
        app_state.canonical_state.current_leader_lap = 20
        # Requesting Lap 25 again should now be LOCKED
        response_moved_back = client.get("/api/outcomes/7953/1/25")
        assert response_moved_back.json().get("outcome_status") == "OUTCOME_LOCKED"

def test_live_mode_protection():
    with TestClient(app) as client:
        # Mock the server state for a live session
        app_state.active_session_key = 9213
        app_state.is_live = True
        app_state.canonical_state = CanonicalRaceState(session_key=9213, current_leader_lap=10)
        
        # Future outcome should be locked in live mode if the lap hasn't passed
        response_live_future = client.get("/api/outcomes/9213/1/15")
        assert response_live_future.json().get("outcome_status") == "OUTCOME_LOCKED"
        
        # But past events can be accessed
        response_live_past = client.get("/api/outcomes/9213/1/5")
        assert response_live_past.json().get("outcome_status") not in ["OUTCOME_LOCKED"]

def test_direct_api_access_cannot_bypass_cutoff():
    with TestClient(app) as client:
        app_state.canonical_state = None
        # Attempting to fetch an outcome without an active valid state (e.g., direct curling)
        response = client.get("/api/outcomes/7953/1/30")
        assert response.json().get("outcome_status") == "OUTCOME_LOCKED"
