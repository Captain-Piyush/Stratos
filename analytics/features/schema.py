"""
STRATOS PHASE 2 - FEATURE SCHEMA

This defines the expected features generated for each driver-lap.
"""

FEATURE_SCHEMA = {
    # Identifiers
    "session_key": {"type": "int", "source": "laps", "description": "OpenF1 Session Key"},
    "driver_number": {"type": "int", "source": "laps", "description": "Driver Number"},
    "lap_number": {"type": "int", "source": "laps", "description": "Lap Number (1-indexed)"},
    
    # Pace Features
    "lap_time": {"type": "float", "source": "laps", "description": "Lap duration in seconds"},
    "lap_time_valid": {"type": "bool", "source": "laps", "description": "True if lap is representative (no pits, no SC/VSC)"},
    "rolling_mean_pace_3": {"type": "float", "source": "derived", "description": "Mean of last 3 valid lap times"},
    "rolling_mean_pace_5": {"type": "float", "source": "derived", "description": "Mean of last 5 valid lap times"},
    "rolling_mean_pace_10": {"type": "float", "source": "derived", "description": "Mean of last 10 valid lap times"},
    "pace_trend": {"type": "float", "source": "derived", "description": "Slope of lap times over last 5 valid laps"},
    "teammate_pace_delta": {"type": "float", "source": "derived", "description": "Difference in lap time vs teammate (negative means faster)"},
    "relative_pace_to_nearby_drivers": {"type": "float", "source": "derived", "description": "Difference in lap time vs average of car ahead and behind"},
    
    # Tyre Features
    "tyre_compound": {"type": "str", "source": "stints", "description": "Tyre compound (SOFT, MEDIUM, HARD, INTERMEDIATE, WET)"},
    "tyre_age": {"type": "int", "source": "stints/laps", "description": "Age of the tyre at the END of the lap"},
    "stint_number": {"type": "int", "source": "stints", "description": "Stint number in the race"},
    "stint_lap_number": {"type": "int", "source": "derived", "description": "Lap number within the current stint"},
    "lap_time_vs_stint_baseline": {"type": "float", "source": "derived", "description": "Delta to first valid lap of the stint"},
    "pace_change_with_tyre_age": {"type": "float", "source": "derived", "description": "Correlation/slope of lap time vs tyre age in current stint"},
    
    # Position & Gap Features
    "position": {"type": "int", "source": "positions", "description": "Track position at the end of the lap"},
    "position_change": {"type": "int", "source": "derived", "description": "Change in position compared to previous lap"},
    "gap_to_leader": {"type": "float", "source": "intervals", "description": "Gap to race leader in seconds"},
    "gap_to_ahead": {"type": "float", "source": "intervals", "description": "Gap to car directly ahead in seconds"},
    "gap_to_behind": {"type": "float", "source": "derived", "description": "Gap to car directly behind in seconds"},
    "gap_change": {"type": "float", "source": "derived", "description": "Change in gap to ahead compared to previous lap"},
    "closing_rate": {"type": "float", "source": "derived", "description": "Rate at which gap to ahead is closing"},
    "opening_rate": {"type": "float", "source": "derived", "description": "Rate at which gap to behind is opening"},
    "gap_valid": {"type": "bool", "source": "derived", "description": "True if gap data is reliable for this lap"},
    
    # Traffic Features
    "cars_within_1s": {"type": "int", "source": "derived", "description": "Estimated number of cars within 1s ahead/behind"},
    "cars_within_2s": {"type": "int", "source": "derived", "description": "Estimated number of cars within 2s ahead/behind"},
    "following_driver": {"type": "int", "source": "derived", "description": "Driver number of the car behind"},
    "driver_being_followed": {"type": "int", "source": "derived", "description": "Driver number of the car ahead"},
    
    # Pit & Track State
    "pit_in": {"type": "bool", "source": "laps", "description": "True if driver entered pit lane this lap"},
    "pit_out": {"type": "bool", "source": "laps", "description": "True if driver exited pit lane this lap"},
    "laps_since_pit": {"type": "int", "source": "derived", "description": "Laps completed since last pit exit"},
    "safety_car_active": {"type": "bool", "source": "race_control", "description": "True if SC deployed during lap"},
    "virtual_safety_car_active": {"type": "bool", "source": "race_control", "description": "True if VSC deployed during lap"},
    "red_flag_context": {"type": "bool", "source": "race_control", "description": "True if Red Flag deployed during lap"},
    
    # Weather (Aligned to end of lap)
    "air_temperature": {"type": "float", "source": "weather", "description": "Air temp"},
    "track_temperature": {"type": "float", "source": "weather", "description": "Track temp"},
    "humidity": {"type": "float", "source": "weather", "description": "Humidity %"},
    "rainfall": {"type": "float", "source": "weather", "description": "Rainfall indicator"},
    
    # Quality Flags
    "weather_alignment_quality": {"type": "str", "source": "derived", "description": "GOOD if within 5m, FAIR if within 15m, POOR otherwise"}
}
