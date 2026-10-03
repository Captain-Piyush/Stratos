import pytest
import asyncio
from datetime import datetime, timezone
from analytics.live.signalr.adapter import F1SignalRAdapter
from analytics.live.events import EventType

@pytest.fixture
def mock_adapter():
    adapter = F1SignalRAdapter()
    return adapter

def test_session_discovery(mock_adapter):
    mock_adapter._update_session_info({
        "Key": 1234,
        "SessionStatus": "Started"
    })
    assert mock_adapter.session_key == 1234
    
    # Check queue for SESSION_STARTED
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.SESSION_STARTED
    assert ev.session_key == 1234

def test_message_normalization(mock_adapter):
    mock_adapter.session_key = 1234
    
    # TimingData
    payload = {
        "Lines": {
            "1": {
                "Position": "1",
                "GapToLeader": "",
                "IntervalToPositionAhead": {"Value": ""},
                "NumberOfLaps": 10,
                "InPit": True
            },
            "44": {
                "Position": "2",
                "GapToLeader": "+1.2",
                "IntervalToPositionAhead": {"Value": "+1.2"}
            }
        }
    }
    
    mock_adapter._dispatch_update("TimingData", payload, datetime.now(timezone.utc))
    
    events = []
    while not mock_adapter.events_queue.empty():
        events.append(mock_adapter.events_queue.get_nowait())
        
    event_types = [e.event_type for e in events]
    assert EventType.POSITION_UPDATE in event_types
    assert EventType.INTERVAL_UPDATE in event_types
    assert EventType.LAP_COMPLETED in event_types
    assert EventType.PIT_EVENT in event_types

    # Find gap for 44
    gap_ev = next(e for e in events if e.event_type == EventType.INTERVAL_UPDATE and e.payload['driver_number'] == 44)
    assert gap_ev.payload['gap_to_leader'] == 1.2

def test_stint_update(mock_adapter):
    mock_adapter.session_key = 1234
    payload = {
        "Lines": {
            "1": {
                "Stints": [{"Compound": "SOFT", "New": "true"}]
            }
        }
    }
    mock_adapter._dispatch_update("TimingAppData", payload, datetime.now(timezone.utc))
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.STINT_UPDATE
    assert ev.payload['compound'] == 'SOFT'

def test_weather_update(mock_adapter):
    mock_adapter.session_key = 1234
    mock_adapter._dispatch_update("WeatherData", {"AirTemp": "25.0", "TrackTemp": "40.0"}, datetime.now(timezone.utc))
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.WEATHER_UPDATE
    assert ev.payload['air_temperature'] == 25.0

def test_race_control(mock_adapter):
    mock_adapter.session_key = 1234
    mock_adapter._dispatch_update("RaceControlMessages", {"Messages": [{"Message": "SAFETY CAR DEPLOYED"}]}, datetime.now(timezone.utc))
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.RACE_CONTROL

def test_track_status(mock_adapter):
    mock_adapter.session_key = 1234
    mock_adapter._dispatch_update("TrackStatus", {"Status": "4"}, datetime.now(timezone.utc))
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.SAFETY_CAR

def test_no_gps_mode(mock_adapter):
    assert mock_adapter.gps_available == False
    mock_adapter.session_key = 1234
    mock_adapter._dispatch_update("TimingData", {}, datetime.now(timezone.utc))
    assert mock_adapter.gps_available == False

def test_gps_available(mock_adapter):
    mock_adapter.session_key = 1234
    mock_adapter._dispatch_update("Position.z", {"Position": [{"1": {"X": 10, "Y": 20, "Z": 30}}]}, datetime.now(timezone.utc))
    assert mock_adapter.gps_available == True
    ev = mock_adapter.events_queue.get_nowait()
    assert ev.event_type == EventType.POSITION_UPDATE
    assert ev.payload['x'] == 10

def test_reconnect_logic():
    adapter = F1SignalRAdapter()
    assert adapter.reconnect_delay == 1
