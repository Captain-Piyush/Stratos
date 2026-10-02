import os
import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class OpenF1Client:
    def __init__(self):
        self.base_url = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")

    def get_sessions(self, year: int = None, country_name: str = None, session_key: int = None) -> List[Dict[str, Any]]:
        """Fetch session data from OpenF1."""
        url = f"{self.base_url}/sessions"
        params = {}
        if year:
            params["year"] = year
        if country_name:
            params["country_name"] = country_name
        if session_key:
            params["session_key"] = session_key
            
        try:
            logger.info(f"Fetching OpenF1 data from {url} with params {params}")
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching data from OpenF1: {e}")
            raise

    def get_dataset(self, endpoint: str, session_key: int) -> List[Dict[str, Any]]:
        """Fetch an arbitrary dataset for a given session."""
        url = f"{self.base_url}/{endpoint}"
        params = {"session_key": session_key}
        
        try:
            logger.info(f"Fetching {endpoint} for session {session_key}")
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            # If the API returns nothing or error dict, handle it gracefully
            if isinstance(data, dict) and "error" in data:
                logger.warning(f"Error in {endpoint} response: {data}")
                return []
            return data
        except requests.RequestException as e:
            logger.error(f"Error fetching {endpoint}: {e}")
            return []
