from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import os
import sys
from datetime import datetime

# Add the project root to the path so we can import from analytics
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.connection import db
from analytics.live.state import CanonicalRaceState
from analytics.live.processor import process_event
from analytics.live.engine import LiveDecisionEngine
from analytics.live.replay_adapter import ReplayStreamAdapter
from analytics.live.session_discovery import LiveSessionDiscovery
from analytics.live.openf1.auth import OpenF1AuthService
from analytics.live.openf1.transport import OpenF1Transport
from analytics.live.openf1.mapper import OpenF1EventMapper
from analytics.replay.engine import extract_historical_outcome
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AppState:
    def __init__(self):
        self.canonical_state = None
        self.active_session_key = 9213 # Default to Austin
        self.is_live = False
        self.connected_clients = set()

app_state = AppState()

@app.on_event("startup")
async def startup_event():
    db.connect()
    app_state.canonical_state = CanonicalRaceState(session_key=app_state.active_session_key)

@app.get("/api/state")
async def get_state():
    if app_state.canonical_state is None:
        return {"status": "INITIALIZING"}
    
    return {
        "status": "LIVE" if app_state.is_live else "REPLAY",
        "state": app_state.canonical_state.model_dump()
    }

@app.get("/api/calibration")
async def get_calibration():
    import json
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json'))
    if os.path.exists(model_path):
        with open(model_path, 'r') as f:
            return json.load(f)
    return {}

@app.get("/api/validation")
async def get_validation_results():
    return {
        "dataset": {
            "total_races": 14,
            "calibration_races": 11,
            "holdout_races": 3
        },
        "holdouts": ["Bahrain 2023", "Spa 2023", "Austin 2023"],
        "metrics": {
            "finish_comparable_observations": 364,
            "dnf": 26,
            "unknown": 0,
            "corrected_mae": 68.89,
            "corrected_median_ae": 12.05,
            "p10_p90_coverage_percent": 30.6,
            "p25_p75_coverage_percent": 19.8
        },
        "interpretation": "V2 reproduced the predictive performance of the hardcoded baseline on the current holdout set while replacing manually specified race-model parameters with empirically calibrated parameters."
    }

@app.get("/api/outcomes/{session_key}/{driver_number}/{decision_lap}")
async def get_historical_outcome(session_key: int, driver_number: int, decision_lap: int):
    # Security/Hindsight Hardening: Enforce server-side cutoff
    # Ensure outcome data cannot be fetched before the replay or live cursor has crossed the boundary
    if app_state.canonical_state is None:
        return {"outcome_status": "OUTCOME_LOCKED", "reason": "No active state"}
        
    if app_state.active_session_key != session_key:
        return {"outcome_status": "OUTCOME_LOCKED", "reason": "Session mismatch"}
        
    current_lap = app_state.canonical_state.current_leader_lap
    if current_lap <= decision_lap:
        return {"outcome_status": "OUTCOME_LOCKED", "reason": "Cursor before or exactly at decision boundary"}

    outcome = extract_historical_outcome(session_key, driver_number, decision_lap)
    
    # We must convert dataclass to dict since it's not a Pydantic model
    import dataclasses
    if dataclasses.is_dataclass(outcome):
        # Handle enums
        res = dataclasses.asdict(outcome)
        res["outcome_status"] = res["outcome_status"].value
        return res
    return {}

@app.websocket("/api/decisions/stream")
async def decision_stream(websocket: WebSocket):
    await websocket.accept()
    app_state.connected_clients.add(websocket)
    try:
        while True:
            # Keep connection open, client might send commands like "PLAY", "PAUSE"
            data = await websocket.receive_text()
            if data.startswith("START_REPLAY"):
                async def safe_run_replay(ws):
                    try:
                        await run_replay(ws)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"Error in run_replay: {e}", flush=True)
                asyncio.create_task(safe_run_replay(websocket))
            elif data.startswith("START_LIVE"):
                async def safe_run_live(ws):
                    try:
                        await run_live(ws)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        print(f"Error in run_live: {e}", flush=True)
                asyncio.create_task(safe_run_live(websocket))
    except WebSocketDisconnect:
        app_state.connected_clients.remove(websocket)

async def run_replay(websocket: WebSocket):
    print("Starting run_replay...", flush=True)
    app_state.is_live = False
    adapter = ReplayStreamAdapter(db, app_state.active_session_key)
    print("Adapter created", flush=True)
    engine = LiveDecisionEngine(db, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')))
    engine.throttle_seconds = 0
    print("Engine created", flush=True)
    
    app_state.canonical_state = CanonicalRaceState(session_key=app_state.active_session_key)
    print("Starting generation...", flush=True)
    
    event_count = 0
    for ev in adapter.generate_events():
        event_count += 1
        print(f"Processing event {event_count}: {ev.event_type}", flush=True)
        # Mock fresh weather
        app_state.canonical_state.weather.last_update = ev.timestamp
        print("Calling process_event", flush=True)
        st, mat = process_event(app_state.canonical_state, ev)
        print(f"process_event returned, mat={mat}. Calling evaluate...", flush=True)
        dec = engine.evaluate(st, mat, current_time=ev.timestamp)
        print("evaluate returned", flush=True)
        
        # Broadcast state update periodically or on material change
        if mat:
            state_msg = {
                "type": "STATE_UPDATE",
                "payload": app_state.canonical_state.model_dump(mode='json')
            }
            try:
                await websocket.send_json(state_msg)
            except Exception as e:
                print(f"Failed to send state: {e}")
                break
                
        if dec and dec.selected_strategy != "DECISION_WITHHELD":
            dec_msg = {
                "type": "DECISION_EVENT",
                "payload": dec.model_dump(mode='json')
            }
            try:
                await websocket.send_json(dec_msg)
                engine.persist_decision(dec, app_state.canonical_state.model_dump(mode='json'))
            except:
                break
                
        await asyncio.sleep(0.01) # Fast replay

async def run_live(websocket: WebSocket):
    print("Starting run_live...", flush=True)
    app_state.is_live = True
    
    await websocket.send_json({"type": "STATUS_UPDATE", "status": "CONNECTING"})
    
    discovery = LiveSessionDiscovery()
    session_data = discovery.get_current_live_session()
    
    if not session_data:
        await websocket.send_json({"type": "STATUS_UPDATE", "status": "NO_ACTIVE_SESSION"})
        return
        
    session_key = session_data['session_key']
    app_state.active_session_key = session_key
    app_state.canonical_state = CanonicalRaceState(session_key=session_key)
    
    engine = LiveDecisionEngine(db, os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/calibration/model_v2.json')))
    
    try:
        auth_service = OpenF1AuthService()
        token = auth_service.get_token() # Will raise if no credentials
    except Exception as e:
        await websocket.send_json({"type": "STATUS_UPDATE", "status": "CREDENTIALS_NOT_AVAILABLE"})
        return

    # Backfill
    backfill_events = discovery.initialize_live_handoff(session_key)
    for ev in backfill_events:
        app_state.canonical_state.weather.last_update = ev.timestamp
        process_event(app_state.canonical_state, ev)
        
    await websocket.send_json({"type": "STATE_UPDATE", "payload": app_state.canonical_state.model_dump(mode='json')})
    
    # Start transport
    transport = OpenF1Transport(auth_service)
    transport.start()
    await websocket.send_json({"type": "STATUS_UPDATE", "status": "LIVE"})
    
    global_seq = len(backfill_events)
    consecutive_empty = 0
    
    try:
        while True:
            messages = transport.get_messages(timeout=1.0)
            
            if not messages:
                consecutive_empty += 1
                if consecutive_empty > 30: # 30 seconds no data
                    await websocket.send_json({"type": "STATUS_UPDATE", "status": "LIVE_DATA_UNAVAILABLE"})
                    consecutive_empty = 0
                await asyncio.sleep(0.1)
                continue
                
            consecutive_empty = 0
            material_change = False
            last_timestamp = None
            
            for topic, payload in messages:
                global_seq += 1
                for ev in OpenF1EventMapper.map_message(topic, payload, global_seq):
                    app_state.canonical_state.weather.last_update = ev.timestamp
                    last_timestamp = ev.timestamp
                    _, mat = process_event(app_state.canonical_state, ev)
                    material_change = material_change or mat
                    
            if material_change and last_timestamp:
                await websocket.send_json({"type": "STATE_UPDATE", "payload": app_state.canonical_state.model_dump(mode='json')})
                
                dec = engine.evaluate(app_state.canonical_state, material_change, current_time=last_timestamp)
                if dec and dec.selected_strategy != "DECISION_WITHHELD":
                    dec_msg = {
                        "type": "DECISION_EVENT",
                        "payload": dec.model_dump(mode='json')
                    }
                    try:
                        await websocket.send_json(dec_msg)
                        engine.persist_decision(dec, app_state.canonical_state.model_dump(mode='json'))
                    except Exception as e:
                        print(f"Failed to send decision: {e}")
                        break
                        
            await asyncio.sleep(0.1)
    finally:
        transport.stop()

