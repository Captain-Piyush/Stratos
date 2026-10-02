import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from database.connection import db

logger = logging.getLogger(__name__)

def get_race_state(session_key: int, lap_number: int) -> Dict[str, Any]:
    """Reconstruct the factual race state for a specific session and lap."""
    
    if db.db is None:
        db.connect()
        
    state = {
        "session_key": session_key,
        "lap_number": lap_number,
        "drivers": [],
        "weather": None,
        "race_control": []
    }
    
    # 1. Fetch Drivers
    drivers_cursor = db.get_collection("drivers").find({"session_key": session_key})
    drivers_map = {d["driver_number"]: d for d in drivers_cursor}
    
    if not drivers_map:
        logger.warning(f"No drivers found for session {session_key}")
        return state
        
    # 2. Fetch Laps
    laps_cursor = db.get_collection("laps").find({"session_key": session_key, "lap_number": lap_number})
    laps_map = {l["driver_number"]: l for l in laps_cursor}
    
    # 3. Fetch Stints
    stints_cursor = db.get_collection("stints").find({"session_key": session_key})
    stints_map = {}
    for s in stints_cursor:
        dn = s["driver_number"]
        if dn not in stints_map:
            stints_map[dn] = []
        stints_map[dn].append(s)
        
    # 4. Fetch Pit Stops
    pits_cursor = db.get_collection("pit_stops").find({"session_key": session_key, "lap_number": lap_number})
    pits_map = {p["driver_number"]: p for p in pits_cursor}

    # Helper function to parse OpenF1 ISO strings
    def parse_date(date_str):
        if not date_str: return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            return None
    
    # 5. Assemble Driver State
    for driver_number, driver_info in drivers_map.items():
        lap_info = laps_map.get(driver_number)
        if not lap_info:
            continue
            
        # Determine Lap End Time to query position and interval
        lap_end_time = None
        date_start_str = lap_info.get("date_start")
        lap_duration = lap_info.get("lap_duration")
        if date_start_str and lap_duration:
            dt_start = parse_date(date_start_str)
            if dt_start:
                lap_end_time = dt_start + timedelta(seconds=lap_duration)
                
        # Determine Stint
        current_stint = None
        for s in stints_map.get(driver_number, []):
            lap_start = s.get("lap_start", 0)
            lap_end = s.get("lap_end", 999)
            if lap_start <= lap_number <= lap_end:
                current_stint = s
                break
                
        # Fetch Position
        position = None
        if lap_end_time:
            iso_end = lap_end_time.isoformat()
            # Find the last position recorded before or exactly at the end of the lap
            pos_doc = db.get_collection("positions").find_one(
                {"session_key": session_key, "driver_number": driver_number, "date": {"$lte": iso_end}},
                sort=[("date", -1)]
            )
            if pos_doc:
                position = pos_doc.get("position")
                
        # Fetch Interval
        gap = None
        if lap_end_time:
            iso_end = lap_end_time.isoformat()
            int_doc = db.get_collection("intervals").find_one(
                {"session_key": session_key, "driver_number": driver_number, "date": {"$lte": iso_end}},
                sort=[("date", -1)]
            )
            if int_doc:
                gap = int_doc.get("gap_to_leader")

        tyre_age = None
        if current_stint:
            # Tyre age is the laps completed in this stint + starting age
            tyre_age = (lap_number - current_stint.get("lap_start", 0) + current_stint.get("tyre_age_at_start", 0))

        driver_state = {
            "driver_number": driver_number,
            "name": driver_info.get("name_acronym"),
            "position": position,
            "lap": lap_number,
            "lap_timing": lap_duration,
            "tyre_compound": current_stint.get("compound") if current_stint else None,
            "tyre_age": tyre_age,
            "gap_to_leader": gap,
            "pit_status": "IN PIT" if driver_number in pits_map else "ON TRACK"
        }
        state["drivers"].append(driver_state)
        
    # Sort drivers by position
    state["drivers"] = sorted(state["drivers"], key=lambda x: x["position"] if x["position"] is not None else 999)

    # 6. Weather & Race Control (closest to the lap time of the leader, or just first available if lap mapping is hard)
    # Since weather is periodic, let's grab the weather from around the lap end time of the leader (if any)
    leader = state["drivers"][0] if state["drivers"] else None
    ref_time = None
    if leader:
        l_lap = laps_map.get(leader["driver_number"])
        if l_lap and l_lap.get("date_start") and l_lap.get("lap_duration"):
            dt_start = parse_date(l_lap["date_start"])
            if dt_start:
                ref_time = (dt_start + timedelta(seconds=l_lap["lap_duration"])).isoformat()
    
    if ref_time:
        weather_doc = db.get_collection("weather").find_one(
            {"session_key": session_key, "date": {"$lte": ref_time}},
            sort=[("date", -1)]
        )
    else:
        weather_doc = db.get_collection("weather").find_one({"session_key": session_key})
        
    if weather_doc:
        weather_doc.pop("_id", None)
        state["weather"] = weather_doc
        
    rc_cursor = db.get_collection("race_control").find({"session_key": session_key}).limit(5)
    for rc in rc_cursor:
        rc.pop("_id", None)
        state["race_control"].append(rc)
        
    return state
