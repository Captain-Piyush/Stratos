import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analytics.live.state import CanonicalRaceState, DriverState, WeatherState
from analytics.live.decision import StrategyDecisionEvent, CandidateSummary

def test_driver_state_lap_history():
    # Verify lap history is available for Pace and Tyre charts
    driver = DriverState(
        driver_number=1,
        current_lap=10,
        current_compound="MEDIUM",
        tyre_age=5,
        last_update="2023-01-01T12:00:00Z",
        lap_history=[90.1, 90.5, 90.8, 91.2, 91.5]
    )
    assert len(driver.lap_history) == 5
    assert driver.lap_history[-1] == 91.5

def test_weather_stale_partial_data():
    # Verify partial data indication (Weather stale)
    weather = WeatherState(status_stale=True)
    state = CanonicalRaceState(
        session_key=123,
        current_leader_lap=10,
        weather=weather
    )
    # The frontend reads this flag explicitly for PARTIAL DATA
    assert state.weather.status_stale is True

def test_decision_event_inspector_fields():
    # Verify fields exist for the Historical Inspector
    candidate = CandidateSummary(
        strategy_id="PIT_35_MED",
        description="Pit Lap 35",
        expected_time=5000.0,
        median_time=4990.0,
        p10_time=4950.0,
        p90_time=5050.0,
        decision_score=95.0,
        probability_vs_baseline=0.6,
        is_valid=True,
        constraint_status="VALID",
        is_selected=True
    )
    event = StrategyDecisionEvent(
        session_key=123,
        timestamp="2023-01-01T12:00:00Z",
        driver_number=1,
        decision_lap=34,
        trigger="LAP_COMPLETION",
        selected_strategy="PIT_35_MED",
        objective="MINIMIZE_TIME",
        decision_score=95.0,
        decision_confidence="HIGH",
        candidate_summary=[candidate],
        explanation="Best candidate",
        software_version="6.0.0",
        simulation_version="3.0.0",
        decision_version="3.1.0",
        calibration_version="model_v2",
        monte_carlo_seed=42,
        state_snapshot_hash="hash",
        decision_id="dec123"
    )
    assert event.calibration_version == "model_v2"
    assert event.monte_carlo_seed == 42
    assert len(event.candidate_summary) == 1
    assert event.candidate_summary[0].p10_time is not None
