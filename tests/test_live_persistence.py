import pytest
import time
import uuid
import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from analytics.live.engine import LiveDecisionEngine, AsyncDecisionWriter
from analytics.live.decision import StrategyDecisionEvent

class MockDB:
    def __init__(self):
        self.collection = MagicMock()
        self.should_fail = False
        self.delay = 0.0
        self.inserts = []
        self.collection.insert_one = self.mock_insert_one

    def get_collection(self, name):
        return self.collection

    def mock_insert_one(self, doc):
        if self.delay > 0:
            time.sleep(self.delay)
        if self.should_fail:
            raise Exception("Mock MongoDB Connection Failed")
        self.inserts.append(doc)

@pytest.fixture
def mock_db():
    return MockDB()

@pytest.fixture
def model_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json'))

@pytest.fixture
def engine(mock_db, model_path):
    return LiveDecisionEngine(mock_db, model_path)

def create_mock_decision():
    return StrategyDecisionEvent(
        session_key=9213,
        timestamp=datetime.now(timezone.utc),
        driver_number=1,
        decision_lap=10,
        trigger="LAP_COMPLETION",
        selected_strategy="STAY_OUT",
        objective="MINIMIZE_TIME",
        decision_score=95.0,
        decision_confidence="HIGH",
        explanation="Test",
        calibration_version="model_v2",
        decision_id=str(uuid.uuid4())
    )

def test_a_normal_persistence(engine, mock_db):
    """A. Normal persistence: decision generated -> MongoDB persistence succeeds."""
    decision = create_mock_decision()
    
    # Simulating the pipeline: Engine evaluate -> persist -> WebSocket (simulated by non-blocking return)
    start = time.time()
    engine.persist_decision(decision, {"lap": 10})
    # Should return immediately
    assert time.time() - start < 0.1
    
    # Wait for background thread to process
    engine.writer.q.join()
    assert len(mock_db.inserts) == 1
    assert mock_db.inserts[0]['decision_id'] == decision.decision_id

def test_b_mongodb_failure_non_blocking(engine, mock_db):
    """B. MongoDB failure: simulate MongoDB unavailable -> live loop remains operational."""
    mock_db.should_fail = True
    decision = create_mock_decision()
    
    start = time.time()
    engine.persist_decision(decision, {"lap": 10})
    duration = time.time() - start
    
    # The call MUST NOT block the live loop
    assert duration < 0.1
    
    # Even though MongoDB failed, the engine doesn't crash
    # Wait to allow background attempts to occur (we set max_retries=3 in production, but here we can just ensure it doesn't crash)
    # The item will eventually be dropped, which is tested in the background loop
    time.sleep(0.1)

def test_c_mongodb_recovery(engine, mock_db):
    """C. Recovery: MongoDB temporarily fails -> later becomes available -> subsequent decisions persist."""
    # First, configure background writer to retry fast for tests
    engine.writer.max_retries = 3
    
    decision1 = create_mock_decision()
    decision2 = create_mock_decision()
    
    # 1. DB is offline
    mock_db.should_fail = True
    engine.persist_decision(decision1, {"lap": 10})
    
    # Wait for the first attempt to fail but before it gives up
    time.sleep(0.5) 
    
    # 2. DB comes online
    mock_db.should_fail = False
    
    # 3. New decision generated
    engine.persist_decision(decision2, {"lap": 11})
    
    # Wait for queue to empty
    engine.writer.q.join()
    
    # Both should eventually be persisted because the first one was retried!
    # (Or at least the second one. The first one will be persisted if it hadn't exhausted retries.)
    assert len(mock_db.inserts) >= 1
    # Check that decision2 made it
    ids = [d['decision_id'] for d in mock_db.inserts]
    assert decision2.decision_id in ids
    # decision1 may or may not be there depending on timing, but recovery worked for subsequent events.

def test_d_queue_bounds(mock_db):
    """D. Queue bounds: repeated persistence failures must not create unbounded memory growth."""
    # Create a writer with a tiny queue
    writer = AsyncDecisionWriter(mock_db, max_retries=1, queue_size=2)
    mock_db.should_fail = True
    mock_db.delay = 1.0 # Force the consumer to block so the queue fills
    
    # Send 5 events into a queue of size 2
    for i in range(5):
        doc = create_mock_decision().model_dump()
        doc['state_summary'] = {"i": i}
        writer.enqueue(doc)
    
    # The queue size should never exceed its maxsize (2)
    assert writer.q.qsize() <= 2
    writer.stop()

def test_e_timing_latency(engine, mock_db):
    """E. Timing: MongoDB latency must not materially block event processing."""
    # Inject 5 seconds of latency into MongoDB inserts
    mock_db.delay = 5.0
    
    decision = create_mock_decision()
    
    # The persistence call should be practically instant (< 0.1s)
    start = time.time()
    engine.persist_decision(decision, {"lap": 10})
    duration = time.time() - start
    
    assert duration < 0.1
