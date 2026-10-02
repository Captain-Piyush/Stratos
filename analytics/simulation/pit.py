from analytics.simulation.models import SimulationParameters

def estimate_pit_loss(session_key: int, params: SimulationParameters) -> float:
    """
    Estimates the time lost due to executing a pit stop.
    Includes pit-lane entry, stationary service, and pit-lane exit.
    
    Does NOT use the actual future pit stop duration of the driver in this race
    to prevent data leakage.
    """
    return params.base_pit_loss

