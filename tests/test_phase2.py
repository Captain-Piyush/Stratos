import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from analytics.features.builder import build_feature_dataset
from datetime import datetime, timedelta, timezone

@pytest.fixture
def mock_db_collections():
    with patch('analytics.features.builder.db') as mock_db:
        mock_db.db = True
        
        def _get_collection(name):
            mock_coll = MagicMock()
            if name == "laps":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 91.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 3, "lap_duration": 92.0, "date_start": "2023-01-01T12:03:01+00:00", "is_pit_out_lap": False},
                    # Pit lap
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "lap_duration": 110.0, "date_start": "2023-01-01T12:04:33+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 2, "lap_number": 1, "lap_duration": 92.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False}
                ]
            elif name == "stints":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 3, "compound": "SOFT", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 1, "stint_number": 2, "lap_start": 4, "lap_end": 10, "compound": "HARD", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 2, "stint_number": 1, "lap_start": 1, "lap_end": 10, "compound": "SOFT", "tyre_age_at_start": 0}
                ]
            elif name == "pit_stops":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "date": "2023-01-01T12:05:00+00:00"}
                ]
            elif name == "race_control":
                # SC active during lap 2
                mock_coll.find.return_value = [
                    {"session_key": 1, "date": "2023-01-01T12:01:40+00:00", "message": "SAFETY CAR DEPLOYED"}
                ]
            elif name == "positions":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 2, "date": "2023-01-01T12:03:00+00:00"},
                    {"session_key": 1, "driver_number": 2, "position": 2, "date": "2023-01-01T12:01:29+00:00"}
                ]
            elif name == "intervals":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "gap_to_leader": 0.0, "interval": 0.0, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 2, "gap_to_leader": 1.5, "interval": 1.5, "date": "2023-01-01T12:01:29+00:00"}
                ]
            elif name == "weather":
                mock_coll.find.return_value = [
                    {"session_key": 1, "date": "2023-01-01T12:00:00+00:00", "air_temperature": 25.0}
                ]
            elif name == "drivers":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "team_name": "Red Bull Racing"},
                    {"session_key": 1, "driver_number": 2, "team_name": "Red Bull Racing"}
                ]
            return mock_coll
            
        mock_db.get_collection.side_effect = _get_collection
        yield mock_db

def test_feature_builder_validity_and_pace(mock_db_collections):
    df = build_feature_dataset(1)
    assert not df.empty
    
    # Driver 1 checks
    d1 = df[df['driver_number'] == 1].set_index('lap_number')
    
    # Lap 1: normal lap
    assert d1.at[1, 'lap_time_valid'] == True
    assert d1.at[1, 'rolling_mean_pace_3'] == 90.0
    
    # Lap 2: affected by SC
    assert d1.at[2, 'safety_car_active'] == True
    assert d1.at[2, 'lap_time_valid'] == False
    # Rolling mean for lap 2 should exclude lap 2 itself because it's invalid
    # Actually rolling uses the last valid laps, so it just carries over lap 1 if we dropna before rolling
    # But in pandas rolling(), it includes the NaN if we just do rolling. Let's see how we implemented:
    # `valid_laps = d_laps[d_laps['lap_time_valid']]['lap_duration']`
    # So valid laps for driver 1 are laps 1, 3.
    # Therefore, d1 at lap 2 rolling_mean_pace_3 might be NaN since it was filtered out of the index.
    # We should just assert lap 3 rolling mean
    assert d1.at[3, 'rolling_mean_pace_3'] == 91.0 # (90+92)/2 = 91.0
    
    # Lap 4: pit in
    assert d1.at[4, 'pit_in'] == True
    assert d1.at[4, 'lap_time_valid'] == False

def test_feature_builder_tyres(mock_db_collections):
    df = build_feature_dataset(1)
    d1 = df[df['driver_number'] == 1].set_index('lap_number')
    
    assert d1.at[1, 'tyre_compound'] == "SOFT"
    assert d1.at[1, 'tyre_age'] == 1
    assert d1.at[3, 'tyre_age'] == 3
    
    assert d1.at[4, 'tyre_compound'] == "HARD"
    assert d1.at[4, 'tyre_age'] == 1
    assert d1.at[4, 'stint_number'] == 2

def test_feature_builder_gaps_and_traffic(mock_db_collections):
    df = build_feature_dataset(1)
    
    # Lap 1 positions
    d1_l1 = df[(df['driver_number'] == 1) & (df['lap_number'] == 1)].iloc[0]
    d2_l1 = df[(df['driver_number'] == 2) & (df['lap_number'] == 1)].iloc[0]
    
    assert d1_l1['position'] == 1
    assert d1_l1['gap_to_leader'] == 0.0
    assert d1_l1['gap_valid'] == True
    
    assert d2_l1['position'] == 2
    assert d2_l1['gap_to_leader'] == 1.5
    assert d2_l1['gap_to_ahead'] == 1.5
    
    # Traffic
    assert d1_l1['cars_within_2s'] == 1 # Driver 2 is at +1.5s
    assert d2_l1['cars_within_2s'] == 1 # Driver 1 is at -1.5s
    assert d1_l1['cars_within_1s'] == 0
    assert d2_l1['cars_within_1s'] == 0

def test_feature_builder_teammate_pace(mock_db_collections):
    df = build_feature_dataset(1)
    d1 = df[df['driver_number'] == 1].set_index('lap_number')
    d2 = df[df['driver_number'] == 2].set_index('lap_number')
    
    # Lap 1 D1=90.0, D2=92.0
    assert d1.at[1, 'teammate_pace_delta'] == -2.0
    assert d2.at[1, 'teammate_pace_delta'] == 2.0

def test_feature_builder_leakage_poisoning(mock_db_collections):
    """
    TASK 1 - FUTURE-DATA POISONING TEST
    Prove that modifying future records (lap N+1, N+2, future intervals, etc)
    does not alter the features computed for lap N.
    """
    # 1. Generate clean dataset and capture Lap 1 features
    df_clean = build_feature_dataset(1)
    lap1_clean_d1 = df_clean[(df_clean['driver_number'] == 1) & (df_clean['lap_number'] == 1)].iloc[0].copy()
    
    # 2. Poison the future data in the mock database
    # We will inject extreme values for Lap 2 and Lap 3
    # mock_db_collections is the mock DB. 
    # Because we need to change the return_value, we must rebuild the mock responses.
    
    with patch('analytics.features.builder.db') as mock_db:
        mock_db.db = True
        def _get_poisoned_collection(name):
            mock_coll = MagicMock()
            if name == "laps":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 1.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False}, # Poisoned lap time
                    {"session_key": 1, "driver_number": 1, "lap_number": 3, "lap_duration": 999.0, "date_start": "2023-01-01T12:01:31+00:00", "is_pit_out_lap": False}, # Poisoned lap time
                    {"session_key": 1, "driver_number": 2, "lap_number": 1, "lap_duration": 92.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False}
                ]
            elif name == "stints":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 3, "compound": "SOFT", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 2, "stint_number": 1, "lap_start": 1, "lap_end": 10, "compound": "SOFT", "tyre_age_at_start": 0}
                ]
            elif name == "pit_stops":
                mock_coll.find.return_value = []
            elif name == "race_control":
                # Poison future with SC
                mock_coll.find.return_value = [
                    {"session_key": 1, "date": "2023-01-01T12:01:31+00:00", "message": "SAFETY CAR DEPLOYED"}
                ]
            elif name == "positions":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 1, "position": 20, "date": "2023-01-01T12:01:31+00:00"}, # Poisoned future position
                    {"session_key": 1, "driver_number": 2, "position": 2, "date": "2023-01-01T12:01:29+00:00"}
                ]
            elif name == "intervals":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "gap_to_leader": 0.0, "interval": 0.0, "date": "2023-01-01T12:01:29+00:00"},
                    {"session_key": 1, "driver_number": 1, "gap_to_leader": 999.0, "interval": 999.0, "date": "2023-01-01T12:01:31+00:00"}, # Poisoned future gap
                    {"session_key": 1, "driver_number": 2, "gap_to_leader": 1.5, "interval": 1.5, "date": "2023-01-01T12:01:29+00:00"}
                ]
            elif name == "weather":
                mock_coll.find.return_value = [
                    {"session_key": 1, "date": "2023-01-01T12:00:00+00:00", "air_temperature": 25.0},
                    {"session_key": 1, "date": "2023-01-01T12:01:31+00:00", "air_temperature": -50.0} # Poisoned future weather
                ]
            elif name == "drivers":
                mock_coll.find.return_value = [
                    {"session_key": 1, "driver_number": 1, "team_name": "Red Bull Racing"},
                    {"session_key": 1, "driver_number": 2, "team_name": "Red Bull Racing"}
                ]
            return mock_coll
            
        mock_db.get_collection.side_effect = _get_poisoned_collection
        
        # 3. Rebuild features
        df_poisoned = build_feature_dataset(1)
        lap1_poisoned_d1 = df_poisoned[(df_poisoned['driver_number'] == 1) & (df_poisoned['lap_number'] == 1)].iloc[0]
        
        # 4. Assert Lap 1 features remain unchanged
        for col in lap1_clean_d1.index:
            # Pandas NaN != NaN, so we handle that
            if pd.isna(lap1_clean_d1[col]):
                assert pd.isna(lap1_poisoned_d1[col]), f"Feature {col} leaked: was NaN, is now {lap1_poisoned_d1[col]}"
            else:
                assert lap1_clean_d1[col] == lap1_poisoned_d1[col], f"Feature {col} leaked: was {lap1_clean_d1[col]}, is now {lap1_poisoned_d1[col]}"

