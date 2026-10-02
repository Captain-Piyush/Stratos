import pytest
import os
import json
import hashlib
from analytics.simulation.models import SimulationParameters, CalibrationProfile

@pytest.fixture
def model_v2_path():
    return os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')

def hash_dict(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode('utf-8')).hexdigest()

def test_holdout_immutability(model_v2_path):
    """Verifies holdouts are entirely absent from calibration dataset."""
    if not os.path.exists(model_v2_path):
        pytest.skip("Model V2 not found")
        
    with open(model_v2_path, 'r') as f:
        artifact = json.load(f)
        
    holdouts = [7953, 9141, 9213]
    cal_races = artifact.get('calibration_races', [])
    
    for h in holdouts:
        assert h not in cal_races, f"Holdout {h} leaked into calibration!"

def test_model_v2_schema_completeness(model_v2_path):
    """Verifies model V2 contains strict explicitly-typed definitions."""
    if not os.path.exists(model_v2_path):
        pytest.skip("Model V2 not found")
        
    with open(model_v2_path, 'r') as f:
        artifact = json.load(f)
        
    # Check explicitly that legacy dicts are replaced with provenance objects
    assert isinstance(artifact['fuel_burn_effect'], dict)
    assert 'value' in artifact['fuel_burn_effect']
    assert artifact['fallback_degradation']['value'] == 0.08
    assert artifact['fallback_compound_delta']['value'] == 0.6
    
def test_poisoning_isolation():
    """Verify modifying a ValidationCase output does not mutate SimulationParameters."""
    profile = CalibrationProfile(
        version='v2',
        calibration_date='2026-10-01',
        calibration_races=[1],
        degradation_slopes={'SOFT': {'value': 0.1}},
        compound_deltas={'SOFT': {'value': 0.0}},
        fuel_burn_effect={'value': 0.06},
        pit_loss={'value': 24.0, 'quality_status': 'ACCEPTED'},
        circuit_pit_loss={},
        residuals={'std': {'value': 0.5}},
        degradation_uncertainty={'value': 0.05},
        fallback_degradation={'value': 0.08},
        fallback_compound_delta={'value': 0.6}
    )
    
    params = SimulationParameters()
    params.apply_calibration(profile)
    
    initial_deg = params.degradation_slopes['SOFT']
    
    # "Poison" the profile
    profile.degradation_slopes['SOFT']['value'] = 0.99
    
    # Assert SimulationParameters decoupled
    assert params.degradation_slopes['SOFT'] == initial_deg
