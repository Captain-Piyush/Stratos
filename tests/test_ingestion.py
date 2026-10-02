import pytest
from unittest.mock import patch, MagicMock
from ingestion.openf1.client import OpenF1Client
from ingestion.pipelines.run_ingestion import run_ingestion

def test_openf1_client_success():
    with patch("ingestion.openf1.client.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = [{"session_key": 9087, "session_name": "Practice 1"}]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        client = OpenF1Client()
        data = client.get_sessions(year=2023, country_name="Monaco")
        
        assert len(data) == 1
        assert data[0]["session_name"] == "Practice 1"
        mock_get.assert_called_once()

@patch("ingestion.pipelines.run_ingestion.db")
@patch("ingestion.pipelines.run_ingestion.OpenF1Client")
def test_run_ingestion_success(mock_client_class, mock_db):
    # Setup mock db
    mock_db.connect.return_value = True
    mock_collection = MagicMock()
    mock_db.get_collection.return_value = mock_collection
    
    mock_insert_result = MagicMock()
    mock_insert_result.inserted_ids = [1, 2]
    mock_collection.insert_many.return_value = mock_insert_result
    
    # Setup mock client
    mock_client_instance = mock_client_class.return_value
    mock_client_instance.get_sessions.return_value = [
        {"session_key": 1, "session_name": "S1"},
        {"session_key": 2, "session_name": "S2"}
    ]
    
    # Run
    result = run_ingestion()
    
    # Assert
    assert result["status"] == "success"
    assert result["count"] == 2
    mock_db.connect.assert_called_once()
    mock_collection.insert_many.assert_called_once()
