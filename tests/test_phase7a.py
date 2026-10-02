import pytest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app import app, app_state
from analytics.live.decision import StrategyDecisionEvent

client = TestClient(app)

def test_fastapi_state_endpoint():
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    if data["status"] != "INITIALIZING":
        assert "state" in data
        assert "session_key" in data["state"]

def test_frontend_types_match():
    # Simple check that backend types export correctly
    # Real validation happens in TypeScript
    event = StrategyDecisionEvent(
        session_key=123,
        timestamp="2023-01-01T12:00:00Z",
        driver_number=1,
        decision_lap=1,
        selected_strategy="STAY_OUT",
        objective="MINIMIZE_TIME",
        decision_score=100.0,
        decision_confidence="HIGH",
        explanation="Test",
        calibration_version="test"
    )
    assert event.decision_confidence in ["HIGH", "MEDIUM", "LOW"]

# Note: WebSocket testing can be done with TestClient.websocket_connect
def test_websocket_connection():
    with client.websocket_connect("/api/decisions/stream") as websocket:
        # Check connection can be established
        pass
