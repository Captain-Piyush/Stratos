import pytest
from unittest.mock import patch, MagicMock
from ingestion.pipelines.ingest_race import ingest_dataset
from backend.services.race_state import get_race_state

@patch("ingestion.pipelines.ingest_race.db")
def test_idempotent_ingestion(mock_db):
    mock_raw = MagicMock()
    mock_norm = MagicMock()
    mock_db.get_collection.side_effect = lambda name: mock_raw if name.startswith("raw_") else mock_norm
    
    mock_client = MagicMock()
    mock_client.get_dataset.return_value = [
        {"session_key": 999, "driver_number": 1, "stint_number": 1, "compound": "SOFT"}
    ]
    
    mock_bulk_result = MagicMock()
    mock_bulk_result.upserted_count = 1
    mock_bulk_result.modified_count = 0
    mock_norm.bulk_write.return_value = mock_bulk_result
    
    # Run once
    count1 = ingest_dataset(mock_client, 999, "stints", "stints")
    assert count1 == 1
    
    # Change mock to simulate modification (idempotency update)
    mock_bulk_result.upserted_count = 0
    mock_bulk_result.modified_count = 1
    count2 = ingest_dataset(mock_client, 999, "stints", "stints")
    assert count2 == 1

@patch("ingestion.pipelines.ingest_race.db")
def test_validation_drops_malformed(mock_db):
    mock_raw = MagicMock()
    mock_norm = MagicMock()
    mock_db.get_collection.side_effect = lambda name: mock_raw if name.startswith("raw_") else mock_norm
    
    mock_client = MagicMock()
    mock_client.get_dataset.return_value = [
        {"session_key": 999, "driver_number": 1}, # Missing lap_number, should drop
        {"session_key": 999, "driver_number": 1, "lap_number": 2} # Valid
    ]
    
    # Bulk write should only be called with 1 valid doc
    ingest_dataset(mock_client, 999, "laps", "laps")
    assert mock_norm.bulk_write.call_args[0][0][0]._filter == {'session_key': 999, 'driver_number': 1, 'lap_number': 2}
    assert len(mock_norm.bulk_write.call_args[0][0]) == 1

@patch("backend.services.race_state.db")
def test_race_state_reconstruction(mock_db):
    mock_drivers = [{"driver_number": 1, "name_acronym": "VER"}]
    mock_laps = [{"driver_number": 1, "lap_number": 10, "lap_duration": 80.5, "date_start": "2023-03-05T15:00:00+00:00"}]
    mock_stints = [{"driver_number": 1, "lap_start": 1, "lap_end": 20, "compound": "HARD", "tyre_age_at_start": 0}]
    
    def mock_get_collection(name):
        mock_coll = MagicMock()
        if name == "drivers": mock_coll.find.return_value = mock_drivers
        elif name == "laps": mock_coll.find.return_value = mock_laps
        elif name == "stints": mock_coll.find.return_value = mock_stints
        elif name == "pit_stops": mock_coll.find.return_value = []
        elif name == "positions": mock_coll.find_one.return_value = {"position": 1}
        elif name == "intervals": mock_coll.find_one.return_value = {"gap_to_leader": 0.0}
        elif name == "weather": mock_coll.find_one.return_value = {"air_temperature": 25.0}
        elif name == "race_control": mock_coll.find.return_value = MagicMock(limit=lambda x: [])
        return mock_coll
        
    mock_db.get_collection.side_effect = mock_get_collection
    mock_db.db = True
    
    state = get_race_state(999, 10)
    
    assert state["session_key"] == 999
    assert state["lap_number"] == 10
    assert len(state["drivers"]) == 1
    assert state["drivers"][0]["name"] == "VER"
    assert state["drivers"][0]["position"] == 1
    assert state["drivers"][0]["gap_to_leader"] == 0.0
    assert state["drivers"][0]["lap"] == 10
    assert state["weather"]["air_temperature"] == 25.0
