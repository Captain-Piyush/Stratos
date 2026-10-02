from analytics.live.state import CanonicalRaceState
import pandas as pd

class FeatureUpdateBridge:
    """
    Bridges the CanonicalRaceState into structures expected by Phase 2 (features)
    and Phase 3 (decision engine) without redefining those features or doing future lookaheads.
    """
    
    @staticmethod
    def extract_race_snapshot(state: CanonicalRaceState, driver_number: int, current_lap: int) -> dict:
        """
        Extracts a dictionary compatible with Phase 2/3 feature expectations.
        Uses ONLY information available in the live state up to current_lap.
        """
        driver = state.driver_states.get(driver_number)
        if not driver:
            return {}

        snapshot = {
            "session_key": state.session_key,
            "driver_number": driver_number,
            "lap_number": current_lap,
            "position": driver.position,
            "gap_to_leader": driver.gap_to_leader,
            "compound": driver.current_compound,
            "tyre_age": driver.tyre_age,
            "stint": driver.stints,
            "is_pit_out_lap": driver.is_in_pit, # Approximated based on state
            "safety_car": state.global_status == "SAFETY_CAR",
            "vsc": state.global_status == "VSC",
            "track_temperature": state.weather.track_temperature if state.weather else None,
            "air_temperature": state.weather.air_temperature if state.weather else None,
            "rainfall": state.weather.rainfall if state.weather else False,
            "fractional_laps_remaining": float((state.race_distance or 57) - current_lap),
            "lap_duration": driver.last_lap_time
        }
        
        # Calculate trailing averages (e.g. 5-lap pace) using lap_history
        if len(driver.lap_history) > 0:
            snapshot["rolling_pace"] = sum(driver.lap_history[-5:]) / len(driver.lap_history[-5:])
        else:
            snapshot["rolling_pace"] = None
            
        return snapshot
