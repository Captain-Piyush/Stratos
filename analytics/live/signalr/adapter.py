import asyncio
import json
import logging
import traceback
import zlib
import base64
from datetime import datetime, timezone
from typing import List, Optional
from websockets.asyncio.client import connect

from analytics.live.events import RaceEvent, EventType

logger = logging.getLogger(__name__)

class F1SignalRAdapter:
    def __init__(self):
        self.url = "wss://livetiming.formula1.com/signalrcore"
        self.ws = None
        self.events_queue = asyncio.Queue()
        self.session_key = None
        self.session_info = None
        self.global_seq = 0
        self.is_running = False
        self.reconnect_delay = 1
        self.gps_available = False

    async def connect(self):
        self.is_running = True
        asyncio.create_task(self._run_loop())
        for _ in range(50):
            if self.session_info:
                break
            await asyncio.sleep(0.1)

    def stop(self):
        self.is_running = False
        if self.ws:
            asyncio.create_task(self.ws.close())

    async def _run_loop(self):
        while self.is_running:
            try:
                logger.info(f"Connecting to {self.url}")
                async with connect(self.url, additional_headers={"User-Agent": "BestHTTP"}) as ws:
                    self.ws = ws
                    self.reconnect_delay = 1
                    
                    await ws.send(json.dumps({"protocol": "json", "version": 1}) + "\x1e")
                    handshake = await ws.recv()
                    logger.info("SignalR handshake complete.")

                    subscribe_msg = {
                        "type": 1,
                        "target": "Subscribe",
                        "arguments": [
                            ["Heartbeat", "SessionInfo", "SessionData", "DriverList", "TimingData", "TimingAppData", "TimingStats", "LapCount", "TrackStatus", "RaceControlMessages", "WeatherData", "CarData.z", "Position.z"]
                        ],
                        "invocationId": "1"
                    }
                    await ws.send(json.dumps(subscribe_msg) + "\x1e")
                    logger.info("SignalR subscribed.")
                    
                    while self.is_running:
                        try:
                            msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                            
                            for frame in msg_raw.split("\x1e"):
                                if not frame: continue
                                try:
                                    msg = json.loads(frame)
                                    self._process_message(msg)
                                except json.JSONDecodeError:
                                    continue
                        except asyncio.TimeoutError:
                            logger.warning("SignalR connection timeout (no heartbeat). Reconnecting...")
                            break 
            except Exception as e:
                logger.error(f"SignalR connection error: {e}")
                
            if self.is_running:
                await asyncio.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, 30)

    def _process_message(self, msg):
        msg_type = msg.get("type")
        
        if msg_type == 6:
            return
            
        if msg_type == 3 and "result" in msg:
            res = msg["result"]
            if "SessionInfo" in res:
                self._update_session_info(res["SessionInfo"])
            if "Position.z" in res:
                self.gps_available = True
                
            for k, v in res.items():
                if k not in ["Heartbeat", "SessionInfo", "Position.z", "CarData.z"]:
                    self._dispatch_update(k, v, datetime.now(timezone.utc))

        if msg_type == 1 and msg.get("target") == "feed":
            args = msg.get("arguments", [])
            if args and len(args) > 0:
                data = args[0]
                topic = args[0]
                payload = args[1]
                
                if topic.endswith(".z"):
                    try:
                        decoded = base64.b64decode(payload)
                        decompressed = zlib.decompress(decoded, -zlib.MAX_WBITS)
                        payload = json.loads(decompressed)
                    except:
                        pass
                        
                if topic == "SessionInfo":
                    self._update_session_info(payload)
                else:
                    self._dispatch_update(topic, payload, datetime.now(timezone.utc))

    def _update_session_info(self, info):
        self.session_info = info
        self.session_key = info.get("Key")
        status = info.get("SessionStatus")
        if status == "Started":
            self._queue_event(EventType.SESSION_STARTED, info)
        elif status == "Finalised":
            self._queue_event(EventType.SESSION_FINISHED, info)

    def _dispatch_update(self, topic: str, payload: dict, timestamp: datetime):
        if not self.session_key:
            return

        if topic == "TimingData":
            lines = payload.get("Lines", {})
            for driver_no, driver_data in lines.items():
                try:
                    d_no = int(driver_no)
                except ValueError:
                    continue
                
                if "Position" in driver_data:
                    self._queue_event(EventType.POSITION_UPDATE, {
                        "driver_number": d_no,
                        "position": int(driver_data["Position"])
                    })
                
                if "GapToLeader" in driver_data or "IntervalToPositionAhead" in driver_data:
                    gap = driver_data.get("GapToLeader", "")
                    interval = driver_data.get("IntervalToPositionAhead", {}).get("Value", "")
                    # The processor expects string or float. Usually OpenF1 returns float or string. 
                    # F1 SignalR usually returns strings like "+1.234"
                    try:
                        gap_val = float(gap.replace("+", "")) if gap and gap not in ("LAP", "") else None
                    except: gap_val = None
                    try:
                        int_val = float(interval.replace("+", "")) if interval and interval not in ("LAP", "") else None
                    except: int_val = None
                    
                    self._queue_event(EventType.INTERVAL_UPDATE, {
                        "driver_number": d_no,
                        "gap_to_leader": gap_val,
                        "interval": int_val
                    })
                    
                if "NumberOfLaps" in driver_data:
                    self._queue_event(EventType.LAP_COMPLETED, {
                        "driver_number": d_no,
                        "lap_number": int(driver_data["NumberOfLaps"])
                    })
                
                if "InPit" in driver_data:
                    self._queue_event(EventType.PIT_EVENT, {
                        "driver_number": d_no,
                        "is_pit": driver_data["InPit"]
                    })

        elif topic == "TimingAppData":
            lines = payload.get("Lines", {})
            for driver_no, driver_data in lines.items():
                try:
                    d_no = int(driver_no)
                except ValueError:
                    continue
                
                if "Stints" in driver_data:
                    # Stints is usually a list/dict of stints
                    stints = driver_data["Stints"]
                    if isinstance(stints, list) and len(stints) > 0:
                        current_stint = stints[-1]
                        self._queue_event(EventType.STINT_UPDATE, {
                            "driver_number": d_no,
                            "compound": current_stint.get("Compound", "UNKNOWN"),
                            "tyre_age_at_start": current_stint.get("New", "false") != "true", # simplified
                            "stint_number": len(stints)
                        })

        elif topic == "WeatherData":
            self._queue_event(EventType.WEATHER_UPDATE, {
                "air_temperature": float(payload.get("AirTemp", 0)),
                "track_temperature": float(payload.get("TrackTemp", 0)),
                "rainfall": payload.get("Rainfall", "0") != "0"
            })

        elif topic == "RaceControlMessages":
            messages = payload.get("Messages", [])
            for m in messages:
                self._queue_event(EventType.RACE_CONTROL, {
                    "message": m.get("Message", "")
                })

        elif topic == "TrackStatus":
            val = str(payload.get("Status", "1"))
            if val == "4":
                self._queue_event(EventType.SAFETY_CAR, payload)
            elif val == "5":
                self._queue_event(EventType.RED_FLAG, payload)
            elif val == "6":
                self._queue_event(EventType.VSC, payload)
            elif val == "1":
                self._queue_event(EventType.GREEN_FLAG, payload)

        elif topic == "Position.z":
            self.gps_available = True
            # Parse position data
            entries = payload.get("Position", [])
            for entry in entries:
                for driver_no, pos in entry.items():
                    if driver_no == "Timestamp": continue
                    try:
                        d_no = int(driver_no)
                        self._queue_event(EventType.POSITION_UPDATE, {
                            "driver_number": d_no,
                            "x": pos.get("X", 0),
                            "y": pos.get("Y", 0),
                            "z": pos.get("Z", 0)
                        })
                    except:
                        pass

    def _queue_event(self, event_type: EventType, payload: dict):
        self.global_seq += 1
        ev = RaceEvent(
            session_key=self.session_key or 0,
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            source="F1_SIGNALR",
            payload=payload,
            sequence_number=self.global_seq
        )
        self.events_queue.put_nowait(ev)

    async def get_events(self, timeout: float = 1.0) -> List[RaceEvent]:
        events = []
        try:
            ev = await asyncio.wait_for(self.events_queue.get(), timeout=timeout)
            events.append(ev)
            while not self.events_queue.empty():
                events.append(self.events_queue.get_nowait())
        except asyncio.TimeoutError:
            pass
        return events

    def get_current_session(self):
        return self.session_info
