import pytest
import pandas as pd
import json
import os
from unittest.mock import patch, MagicMock

from analytics.calibration.dataset import build_calibration_dataset, CACHE_DIR, PROGRESS_FILE
from analytics.calibration.guard import HoldoutContaminationError
from analytics.calibration.engine import run_calibration_pipeline

@pytest.fixture
def mock_cache_env(tmp_path):
    with patch('analytics.calibration.dataset.CACHE_DIR', str(tmp_path / 'cache')), \
         patch('analytics.calibration.dataset.PROGRESS_FILE', str(tmp_path / 'progress.json')), \
         patch('analytics.calibration.engine.CALIBRATION_ARTIFACT_PATH', str(tmp_path / 'model_v1.json')), \
         patch('analytics.calibration.engine.REPORT_PATH', str(tmp_path / 'report.md')):
        yield tmp_path

def test_cache_reuse(mock_cache_env):
    with patch('analytics.calibration.dataset.build_feature_dataset') as mock_builder, \
         patch('analytics.calibration.dataset.db') as mock_db:
         
        # Return a dummy dataframe
        dummy_df = pd.DataFrame({
            'session_key': [1000], 'driver_number': [1], 'lap_number': [1], 'lap_duration': [90.0],
            'pit_in': [False], 'pit_out': [False], 'safety_car_active': [False], 'virtual_safety_car_active': [False],
            'red_flag_context': [False], 'lap_time': [90.0], 'tyre_compound': ['SOFT'], 'tyre_age': [1]
        })
        mock_builder.return_value = dummy_df
        
        # First run (should build and cache)
        df, stats = build_calibration_dataset([1000], force=False)
        assert mock_builder.call_count == 1
        
        # Second run (should reuse)
        df2, stats2 = build_calibration_dataset([1000], force=False)
        assert mock_builder.call_count == 1 # Still 1!
        
        # Force run (should rebuild)
        df3, stats3 = build_calibration_dataset([1000], force=True)
        assert mock_builder.call_count == 2
        
def test_interrupted_run_recovery(mock_cache_env):
    with patch('analytics.calibration.dataset.build_feature_dataset') as mock_builder, \
         patch('analytics.calibration.dataset.db') as mock_db:
         
        dummy_df = pd.DataFrame({
            'session_key': [1001], 'driver_number': [1], 'lap_number': [1], 'lap_duration': [90.0],
            'pit_in': [False], 'pit_out': [False], 'safety_car_active': [False], 'virtual_safety_car_active': [False],
            'red_flag_context': [False], 'lap_time': [90.0], 'tyre_compound': ['SOFT'], 'tyre_age': [1]
        })
        
        # Simulate failure on first run for session 1002
        def side_effect(sk):
            if sk == 1002:
                raise ValueError("Simulated DB error")
            return dummy_df
            
        mock_builder.side_effect = side_effect
        
        # Run with 1001 and 1002 (1001 should succeed, 1002 should fail)
        df, stats = build_calibration_dataset([1001, 1002], force=False)
        assert len(df) == 1 # Only 1001 succeeded
        
        # Check progress file
        with open(str(mock_cache_env / 'progress.json'), 'r') as f:
            progress = json.load(f)
        assert progress['1001']['status'] == 'COMPLETE'
        assert progress['1002']['status'] == 'FAILED'
        
        # Run again, fixing the error
        mock_builder.side_effect = None
        mock_builder.return_value = dummy_df
        
        df2, stats2 = build_calibration_dataset([1001, 1002], force=False)
        assert len(df2) == 2 # Both 1001 and 1002
        assert mock_builder.call_count == 3 # 1001 (cached), 1002 (failed), 1002 (retried)
        
def test_holdout_protection(mock_cache_env):
    with patch('analytics.calibration.guard.load_manifest') as mock_manifest:
        mock_manifest.return_value = [
            {"session_key": 9999, "split": "HOLDOUT"}
        ]
        with pytest.raises(HoldoutContaminationError):
            build_calibration_dataset([9999])
