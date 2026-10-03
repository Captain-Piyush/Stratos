import logging
from typing import Optional, Tuple, List
import requests
import pandas as pd
from datetime import datetime, timezone

from analytics.live.events import RaceEvent
from analytics.live.openf1.mapper import OpenF1EventMapper
from ingestion.openf1.client import OpenF1Client

logger = logging.getLogger(__name__)

class LiveSessionDiscovery:
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.client = OpenF1Client()
        
    def get_current_live_session(self) -> Optional[dict]:
        """
        Uses OpenF1 REST API to find the latest ACTIVE race session.
        Explicitly distinguishes Practice, Qualifying, Sprint, Race.
        Returns a session descriptor dict.
        """
        try:
            sessions = self.client.get_sessions()
            if not sessions:
                return None
            
            # Filter for Race sessions and sort by date_start
            race_sessions = [s for s in sessions if s.get('session_type') == 'Race' and s.get('date_start')]
            if not race_sessions:
                return None
                
            race_sessions.sort(key=lambda x: x['date_start'])
            latest_session = race_sessions[-1]
            
            # Check if it's currently active (e.g., started within the last 4 hours)
            date_start_str = latest_session.get('date_start')
            if date_start_str:
                date_start = pd.to_datetime(date_start_str.replace('Z', '+00:00')).to_pydatetime()
                diff_seconds = (datetime.now(timezone.utc) - date_start).total_seconds()
                
                # If session hasn't started yet, or started more than 4 hours ago, it's not active
                if diff_seconds < 0 or diff_seconds > 4 * 3600:
                    return None
            
            return latest_session
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to discover live session (HTTP error): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to discover live session: {e}")
            return None
            
        return None
        
    def initialize_live_handoff(self, session_key: int) -> List[RaceEvent]:
        """
        Backfills from historical data and returns a sorted list of RaceEvents to hand off to live.
        """
        logger.info(f"Initializing backfill for session {session_key}")
        
        datasets = ['sessions', 'laps', 'positions', 'intervals', 'stints', 'pit_stops', 'weather', 'race_control']
        events = []
        global_seq = 0
        
        for dataset in datasets:
            try:
                data = self.client.get_dataset(dataset, session_key)
                for item in data:
                    global_seq += 1
                    mapped_events = list(OpenF1EventMapper.map_message(f"v1/{dataset}", item, global_seq))
                    events.extend(mapped_events)
            except Exception as e:
                logger.warning(f"Failed to fetch or map dataset {dataset} for backfill: {e}")
                
        # Sort by timestamp
        events.sort(key=lambda x: x.timestamp)
        return events

