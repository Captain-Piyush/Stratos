from typing import Optional, Iterator
from datetime import datetime
import pandas as pd
from analytics.live.events import RaceEvent, EventType

class OpenF1EventMapper:
    @staticmethod
    def _parse_time(ts_str: str) -> Optional[datetime]:
        if not ts_str:
            return None
        return pd.to_datetime(ts_str.replace('Z', '+00:00')).to_pydatetime()

    @staticmethod
    def map_message(topic: str, payload: dict, global_sequence: int = 0) -> Iterator[RaceEvent]:
        # Topic format: e.g. "v1/laps" or "v1/sessions"
        if not payload:
            return
            
        session_key = payload.get('session_key')
        if not session_key:
            return
            
        timestamp_str = payload.get('date') or payload.get('date_start')
        timestamp = OpenF1EventMapper._parse_time(timestamp_str) if timestamp_str else datetime.utcnow()
        
        if 'sessions' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.SESSION_STARTED, # Overly simplified for demo
                source=f"openf1.{topic}",
                payload=payload,
                sequence_number=global_sequence
            )
            
        elif 'laps' in topic:
            lap_duration = payload.get('lap_duration')
            if lap_duration is not None:
                if payload.get('date_start'):
                    timestamp = OpenF1EventMapper._parse_time(payload['date_start']) + pd.Timedelta(seconds=lap_duration)
                yield RaceEvent(
                    session_key=session_key,
                    timestamp=timestamp,
                    event_type=EventType.LAP_COMPLETED,
                    source=f"openf1.{topic}",
                    payload={
                        "driver_number": payload.get('driver_number'),
                        "lap_number": payload.get('lap_number'),
                        "lap_duration": lap_duration
                    },
                    sequence_number=global_sequence
                )
                
        elif 'positions' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.POSITION_UPDATE,
                source=f"openf1.{topic}",
                payload={
                    "driver_number": payload.get('driver_number'),
                    "position": payload.get('position')
                },
                sequence_number=global_sequence
            )
            
        elif 'intervals' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.INTERVAL_UPDATE,
                source=f"openf1.{topic}",
                payload={
                    "driver_number": payload.get('driver_number'),
                    "gap_to_leader": payload.get('gap_to_leader'),
                    "interval": payload.get('interval')
                },
                sequence_number=global_sequence
            )
            
        elif 'stints' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.STINT_UPDATE,
                source=f"openf1.{topic}",
                payload={
                    "driver_number": payload.get('driver_number'),
                    "compound": payload.get('compound'),
                    "tyre_age_at_start": payload.get('tyre_age_at_start'),
                    "stint_number": payload.get('stint_number')
                },
                sequence_number=global_sequence
            )
            
        elif 'pit_stops' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.PIT_EVENT,
                source=f"openf1.{topic}",
                payload={
                    "driver_number": payload.get('driver_number'),
                    "is_pit": True,
                    "lap": payload.get('lap_number')
                },
                sequence_number=global_sequence
            )
            
        elif 'weather' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.WEATHER_UPDATE,
                source=f"openf1.{topic}",
                payload={
                    "air_temperature": payload.get('air_temperature'),
                    "track_temperature": payload.get('track_temperature'),
                    "rainfall": payload.get('rainfall', 0) > 0
                },
                sequence_number=global_sequence
            )
            
        elif 'race_control' in topic:
            yield RaceEvent(
                session_key=session_key,
                timestamp=timestamp,
                event_type=EventType.RACE_CONTROL,
                source=f"openf1.{topic}",
                payload={
                    "message": payload.get('message'),
                    "category": payload.get('category')
                },
                sequence_number=global_sequence
            )
