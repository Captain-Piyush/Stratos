import pytest
import os
import json
import pandas as pd
from analytics.simulation.models import SimulationParameters, CalibrationProfile

@pytest.fixture
def mock_artifact():
    artifact_path = os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')
    if not os.path.exists(artifact_path):
        pytest.skip("Model artifact not found. Run calibration pipeline first.")
    with open(artifact_path, 'r') as f:
        return json.load(f)

def test_artifact_schema_provenance(mock_artifact):
    """Verifies that all parameters in the artifact schema contain explicit provenance."""
    # Fuel burn
    fuel = mock_artifact['fuel_burn_effect']
    assert 'value' in fuel
    assert fuel['source'] == 'PRIOR'
    assert fuel['quality_status'] == 'ACCEPTED'
    
    # Degradation and compound
    for comp in ['SOFT', 'MEDIUM', 'HARD']:
        deg = mock_artifact['degradation_slopes'][comp]
        assert 'value' in deg
        assert deg['source'] == 'CALIBRATED'
        assert deg['quality_status'] == 'ACCEPTED'
        
        delta = mock_artifact['compound_deltas'][comp]
        assert 'value' in delta
        assert delta['source'] == 'CALIBRATED'
        
    # Pit loss
    pit = mock_artifact['pit_loss']
    assert 'value' in pit
    assert pit['source'] in ['CALIBRATED', 'FALLBACK']
    
    # Circuit pit loss
    for circuit, c_pit in mock_artifact['circuit_pit_loss'].items():
        assert 'value' in c_pit
        assert c_pit['source'] in ['CALIBRATED', 'FALLBACK']
        if c_pit['source'] == 'FALLBACK':
            assert c_pit['quality_status'] == 'REJECTED'
            
    # Residuals
    assert 'value' in mock_artifact['residuals']['std']
    assert mock_artifact['residuals']['std']['source'] == 'CALIBRATED'

def test_circuit_9173_fallback(mock_artifact):
    """Verifies that Circuit 9173 fails quality gates due to red flags and falls back."""
    c_pit = mock_artifact['circuit_pit_loss'].get("9173", None)
    if c_pit:
        assert c_pit['source'] == 'FALLBACK'
        assert c_pit['quality_status'] == 'REJECTED'
        
def test_fallback_semantics():
    """Verifies that compound fallback values are explicit in the profile and loaded correctly."""
    profile = CalibrationProfile(
        version='v2',
        calibration_date='2026-10-01',
        calibration_races=[],
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
    
    assert params.fallback_degradation == 0.08
    assert params.fallback_compound_delta == 0.6
    assert params.fuel_burn_effect == 0.06
    assert params.base_pit_loss == 24.0
