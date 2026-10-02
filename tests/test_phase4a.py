import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from analytics.replay.models import ReplaySnapshot, DecisionSnapshot, HistoricalOutcome
from analytics.replay.engine import (
    get_decision_lap_cutoff,
    create_replay_snapshot,
    evaluate_historical_decision,
    extract_historical_outcome
)
from analytics.simulation.models import StrategyPlan, SimulationParameters
from analytics.simulation.montecarlo import MonteCarloParameters
from analytics.simulation.decision import DecisionObjective, RiskPreferences, DecisionConstraints

class FakeCursor:
    def __init__(self, data):
        self.data = data
    def __iter__(self):
        return iter(self.data)
    def sort(self, *args, **kwargs):
        return self
    def limit(self, n):
        return self.data[-n:] if self.data else []

@pytest.fixture
def mock_db_replay():
    with patch('analytics.features.builder.db') as mock_db, \
         patch('analytics.replay.engine.db', new=mock_db):
        mock_db.db = True
        
        def _get_collection(name):
            mock_coll = MagicMock()
            data = []
            if name == "laps":
                data = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 91.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 3, "lap_duration": 92.0, "date_start": "2023-01-01T12:03:01+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "lap_duration": 110.0, "date_start": "2023-01-01T12:04:33+00:00", "is_pit_out_lap": False}
                ]
            elif name == "stints":
                data = [
                    {"session_key": 1, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 3, "compound": "SOFT", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 1, "stint_number": 2, "lap_start": 4, "lap_end": 10, "compound": "HARD", "tyre_age_at_start": 0}
                ]
            elif name == "pit_stops":
                data = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "date": "2023-01-01T12:05:00+00:00"}
                ]
            elif name == "race_control":
                data = []
            elif name == "positions":
                data = [
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:03:00+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 2, "date": "2023-01-01T12:04:33+00:00"}
                ]
            elif name == "intervals":
                data = []
            elif name == "weather":
                data = []
            elif name == "drivers":
                data = [{"session_key": 1, "driver_number": 1, "team_name": "RBR"}]
            
            mock_coll.find.return_value = FakeCursor(data)
            return mock_coll
            
        mock_db.get_collection.side_effect = _get_collection
        yield mock_db

def test_cutoff_mechanism(mock_db_replay):
    cutoff = get_decision_lap_cutoff(1, 1, 2)
    assert cutoff is not None
    
    snap = create_replay_snapshot(1, 1, 2)
    assert snap.decision_lap == 2
    # Lap 2 duration 91, Lap 1 duration 90 -> total time 181
    assert snap.race_state_at_decision.cumulative_race_time == 181.0
    
    # Should not contain Lap 3 or 4 data
    assert snap.available_features['lap_number'] == 2

def test_decision_immutability(mock_db_replay):
    snap = create_replay_snapshot(1, 1, 2)
    s1 = StrategyPlan([4], ["HARD"])
    
    dec = evaluate_historical_decision(
        snap, [s1], SimulationParameters(), MonteCarloParameters(number_of_runs=10),
        DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints()
    )
    
    # Decision is frozen
    assert dec.decision_objective == DecisionObjective.MIN_EXPECTED_TIME
    assert len(dec.monte_carlo_summary) == 1
    assert dec.decision_time is not None

def test_actual_strategy_extraction(mock_db_replay):
    outcome = extract_historical_outcome(1, 1, 2)
    # The DB has a pit stop on Lap 4 for Driver 1
    assert 4 in outcome.actual_pit_laps
    assert "HARD" in outcome.actual_compounds
    assert outcome.actual_finish_position == 2 # From Lap 4 position
    
def test_future_data_poisoning_replay(mock_db_replay):
    # Base decision
    snap1 = create_replay_snapshot(1, 1, 2)
    s1 = StrategyPlan([4], ["HARD"])
    dec1 = evaluate_historical_decision(
        snap1, [s1], SimulationParameters(), MonteCarloParameters(number_of_runs=50, random_seed=42),
        DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints()
    )
    
    # Poison the DB by changing Lap 4 position and time massively
    with patch('analytics.features.builder.db') as mock_db, \
         patch('analytics.replay.engine.db', new=mock_db):
        mock_db.db = True
        
        def _get_poison_collection(name):
            mock_coll = MagicMock()
            data = []
            if name == "laps":
                data = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 91.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 3, "lap_duration": 9999.0, "date_start": "2023-01-01T12:03:01+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "lap_duration": 9999.0, "date_start": "2023-01-01T12:04:33+00:00", "is_pit_out_lap": False}
                ]
            elif name == "stints":
                data = [
                    {"session_key": 1, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 3, "compound": "SOFT", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 1, "stint_number": 2, "lap_start": 4, "lap_end": 10, "compound": "HARD", "tyre_age_at_start": 0}
                ]
            elif name == "pit_stops":
                data = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "date": "2023-01-01T12:05:00+00:00"}
                ]
            elif name == "race_control":
                data = [{"session_key": 1, "date": "2023-01-01T12:03:02+00:00", "message": "RED FLAG"}]
            elif name == "positions":
                data = [
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 20, "date": "2023-01-01T12:03:00+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 20, "date": "2023-01-01T12:04:33+00:00"}
                ]
            elif name == "intervals": data = []
            elif name == "weather": data = []
            elif name == "drivers": data = [{"session_key": 1, "driver_number": 1, "team_name": "RBR"}]
            
            mock_coll.find.return_value = FakeCursor(data)
            return mock_coll
            
        mock_db.get_collection.side_effect = _get_poison_collection
        
        snap2 = create_replay_snapshot(1, 1, 2)
        dec2 = evaluate_historical_decision(
            snap2, [s1], SimulationParameters(), MonteCarloParameters(number_of_runs=50, random_seed=42),
            DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints()
        )
        
        # Decision must be 100% identical
        assert dec1.decision_score == dec2.decision_score
        assert dec1.confidence == dec2.confidence
        assert snap1.race_state_at_decision.base_lap_time == snap2.race_state_at_decision.base_lap_time

def test_deterministic_replay(mock_db_replay):
    snap1 = create_replay_snapshot(1, 1, 2)
    s1 = StrategyPlan([4], ["HARD"])
    dec1 = evaluate_historical_decision(
        snap1, [s1], SimulationParameters(), MonteCarloParameters(number_of_runs=50, random_seed=42),
        DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints()
    )
    
    snap2 = create_replay_snapshot(1, 1, 2)
    dec2 = evaluate_historical_decision(
        snap2, [s1], SimulationParameters(), MonteCarloParameters(number_of_runs=50, random_seed=42),
        DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints()
    )
    
    assert dec1.decision_score == dec2.decision_score
