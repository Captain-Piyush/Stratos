from typing import Iterator
from datetime import datetime
from analytics.live.events import RaceEvent

class LiveIngestionAdapter:
    """
    Adapter for live ingestion from OpenF1 endpoints.
    Currently a skeleton to be filled out with actual API connections.
    It isolates provider-specific logic from the deterministic event processor.
    """
    def __init__(self, session_key: int):
        self.session_key = session_key

    def fetch_live_events(self) -> Iterator[RaceEvent]:
        # TODO: Implement connection to OpenF1 WebSockets or polling endpoints.
        # This yields RaceEvent objects continuously as they arrive.
        yield from []
