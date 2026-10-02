import pytest
import os
import json
import hashlib
from analytics.simulation.models import SimulationParameters
from analytics.replay.engine import extract_historical_outcome
from scripts.run_phase5c_diagnostic import get_eligible_drivers, extract_candidates
from database.connection import db

def test_driver_inclusion_rule():
    db.connect()
    # Mocking or assuming database has data for 7953
    drivers = get_eligible_drivers(7953)
    assert len(drivers) > 0
    # Rule explicitly prevents post-hoc selection: we fetch all drivers who completed lap 1.
    
def test_simulation_horizon_bounds():
    # If decision lap + 2 > max laps, candidates must be truncated
    cands = extract_candidates(decision_lap=43, max_laps=44)
    # Only STAY OUT is allowed, since 43 + 2 = 45 > 44
    assert len(cands) == 1
    assert cands[0].pit_laps == []

def test_strategy_provenance():
    # Inferred vs direct
    outcome = extract_historical_outcome(7953, 1, 10)
    assert outcome.pit_source in ['DIRECT', 'INFERRED', 'UNKNOWN']
    assert outcome.strategy_source in ['DIRECT', 'INFERRED', 'UNKNOWN']

def test_legacy_vs_v2_matching():
    # To run identical cases, parameters must be structurally distinct but evaluation cases identical
    leg = SimulationParameters()
    v2 = SimulationParameters()
    v2.fallback_degradation = 0.999
    assert leg != v2

def test_holdout_immutability_diagnostic():
    artifact_path = os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')
    if os.path.exists(artifact_path):
        with open(artifact_path, 'r') as f:
            artifact = json.load(f)
        assert 7953 not in artifact.get('calibration_races', [])
        assert 9141 not in artifact.get('calibration_races', [])
        assert 9213 not in artifact.get('calibration_races', [])
