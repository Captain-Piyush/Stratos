import os
import requests
import time
import logging

logger = logging.getLogger(__name__)

class OpenF1AuthService:
    def __init__(self):
        self.username = os.environ.get("OPENF1_USERNAME")
        self.password = os.environ.get("OPENF1_PASSWORD")
        self.token_url = "https://api.openf1.org/token"
        self._access_token = None
        self._token_expiry = 0

    def get_token(self) -> str:
        if not self.username or not self.password:
            # If no creds are provided, we might still try without auth if supported, or just raise
            raise ValueError("OPENF1_USERNAME and OPENF1_PASSWORD must be set in environment.")

        if self._access_token and time.time() < self._token_expiry:
            return self._access_token

        return self.authenticate()

    def authenticate(self) -> str:
        try:
            logger.info("Authenticating with OpenF1 API...")
            response = requests.post(self.token_url, data={
                "username": self.username,
                "password": self.password,
                "grant_type": "password"
            }, timeout=10)
            
            response.raise_for_status()
            data = response.json()
            
            self._access_token = data.get("access_token")
            # Default to 3600 seconds expiry minus a buffer (300s) if expires_in is present
            expires_in = data.get("expires_in", 3600) - 300
            self._token_expiry = time.time() + expires_in
            
            logger.info("Successfully authenticated with OpenF1.")
            return self._access_token
        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise ConnectionError(f"Failed to authenticate with OpenF1: {e}")
