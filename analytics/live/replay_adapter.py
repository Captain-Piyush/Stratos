from typing import List, Iterator
import pandas as pd
from datetime import datetime
from analytics.live.events import RaceEvent, EventType

class ReplayStreamAdapter:
    def __init__(self, db_connection, session_key: int):
        self.db = db_connection
        self.session_key = session_key

    def _convert_timestamp(self, ts_str) -> datetime:
        if isinstance(ts_str, datetime):
            return ts_str
        return pd.to_datetime(ts_str.replace('Z', '+00:00')).to_pydatetime()

    def generate_events(self) -> Iterator[RaceEvent]:
        all_events = []
        
        # 1. Session start
        session = self.db.get_collection('sessions').find_one({"session_key": self.session_key})
        if session and session.get('date_start'):
            start_ts = self._convert_timestamp(session['date_start'])
            all_events.append(RaceEvent(
                session_key=self.session_key,
                timestamp=start_ts,
                event_type=EventType.SESSION_STARTED,
                source="replay.sessions",
                payload={}
            ))
            
        # 2. Laps
        for lap in self.db.get_collection('laps').find({"session_key": self.session_key}):
            if lap.get('date_start') and lap.get('lap_duration'):
                ts = self._convert_timestamp(lap['date_start']) + pd.Timedelta(seconds=lap['lap_duration'])
                all_events.append(RaceEvent(
                    session_key=self.session_key,
                    timestamp=ts,
                    event_type=EventType.LAP_COMPLETED,
                    source="replay.laps",
                    payload={
                        "driver_number": lap['driver_number'],
                        "lap_number": lap['lap_number'],
                        "lap_duration": lap['lap_duration']
                    }
                ))
                
        # 3. Pit stops
        for pit in self.db.get_collection('pit_stops').find({"session_key": self.session_key}):
            if pit.get('date'):
                ts = self._convert_timestamp(pit['date'])
                all_events.append(RaceEvent(
                    session_key=self.session_key,
                    timestamp=ts,
                    event_type=EventType.PIT_EVENT,
                    source="replay.pit_stops",
                    payload={
                        "driver_number": pit['driver_number'],
                        "is_pit": True,
                        "lap": pit['lap_number'],
                        "pit_duration": pit.get('pit_duration')
                    }
                ))
                
        # 4. Stints
        # (For real-time we may need to synthesize these when compounds change, but in replay we can just use the DB stints)
        for stint in self.db.get_collection('stints').find({"session_key": self.session_key}):
            # stint update happens at the start of the stint. Stints in OpenF1 don't have exact timestamps, 
            # so we'll map them to lap start times or session start
            if 'lap_start' in stint:
                # Approximate timestamp: find the lap start time from laps collection
                lap = self.db.get_collection('laps').find_one({"session_key": self.session_key, "driver_number": stint['driver_number'], "lap_number": stint['lap_start']})
                ts = start_ts # fallback
                if lap and lap.get('date_start'):
                    ts = self._convert_timestamp(lap['date_start'])
                    
                all_events.append(RaceEvent(
                    session_key=self.session_key,
                    timestamp=ts,
                    event_type=EventType.STINT_UPDATE,
                    source="replay.stints",
                    payload={
                        "driver_number": stint['driver_number'],
                        "compound": stint.get('compound', 'UNKNOWN'),
                        "tyre_age_at_start": stint.get('tyre_age_at_start', 0),
                        "stint_number": stint.get('stint_number', 1)
                    }
                ))
                
        # 5. Weather
        for w in self.db.get_collection('weather').find({"session_key": self.session_key}):
            if w.get('date'):
                ts = self._convert_timestamp(w['date'])
                all_events.append(RaceEvent(
                    session_key=self.session_key,
                    timestamp=ts,
                    event_type=EventType.WEATHER_UPDATE,
                    source="replay.weather",
                    payload={
                        "air_temperature": w.get('air_temperature'),
                        "track_temperature": w.get('track_temperature'),
                        "rainfall": w.get('rainfall', 0) > 0
                    }
                ))
                
        # 6. Race Control
        for rc in self.db.get_collection('race_control').find({"session_key": self.session_key}):
            if rc.get('date'):
                ts = self._convert_timestamp(rc['date'])
                all_events.append(RaceEvent(
                    session_key=self.session_key,
                    timestamp=ts,
                    event_type=EventType.RACE_CONTROL,
                    source="replay.race_control",
                    payload={
                        "message": rc.get('message'),
                        "category": rc.get('category')
                    }
                ))

        # Sort all events chronologically
        all_events.sort(key=lambda x: x.timestamp)
        
        for i, ev in enumerate(all_events):
            ev.sequence_number = i
            yield ev
