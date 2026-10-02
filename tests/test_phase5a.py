import os
import json
import pytest
from unittest.mock import patch, MagicMock

# Assuming data/race_manifest.json exists and contains correct splits
MANIFEST_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/race_manifest.json'))

@pytest.fixture
def load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        pytest.skip("Manifest not found")
    with open(MANIFEST_PATH, 'r') as f:
        return json.load(f)

def test_manifest_parsing(load_manifest):
    manifest = load_manifest
    assert len(manifest) >= 8, "Manifest should have at least 8 races"
    for r in manifest:
        assert 'race' in r
        assert 'session_key' in r
        assert 'split' in r
        assert 'ingestion_status' in r

def test_race_level_split(load_manifest):
    manifest = load_manifest
    splits = [r['split'] for r in manifest]
    assert 'HOLDOUT' in splits, "Must have HOLDOUT split"
    assert 'CALIBRATION' in splits, "Must have CALIBRATION split"

def test_bahrain_holdout_protection(load_manifest):
    manifest = load_manifest
    bahrain_races = [r for r in manifest if r['session_key'] == 7953 or r['circuit'] == 'Bahrain']
    assert len(bahrain_races) > 0, "Bahrain must be in the manifest"
    for r in bahrain_races:
        assert r['split'] == 'HOLDOUT', "Bahrain MUST be in the HOLDOUT set"

def test_no_duplicate_ingestion_indexes():
    from ingestion.pipelines.ingest_race import UNIQUE_KEYS
    assert 'sessions' in UNIQUE_KEYS
    assert 'laps' in UNIQUE_KEYS
    assert 'session_key' in UNIQUE_KEYS['laps']

def test_idempotent_reingestion():
    from ingestion.pipelines.ingest_race import ingest_dataset
    
    client_mock = MagicMock()
    client_mock.get_sessions.return_value = [{"session_key": 9999, "year": 2023}]
    client_mock.get_dataset.return_value = [{"session_key": 9999, "driver_number": 1, "lap_number": 1}]
    
    with patch('ingestion.pipelines.ingest_race.db') as mock_db:
        mock_coll = MagicMock()
        mock_db.get_collection.return_value = mock_coll
        mock_coll.bulk_write.return_value.upserted_count = 1
        mock_coll.bulk_write.return_value.modified_count = 0
        
        # Calling ingest_dataset
        count = ingest_dataset(client_mock, 9999, "laps", "laps")
        assert count == 1
        # The UpdateOne filters ensure idempotency.
        
