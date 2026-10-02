import math
from typing import Tuple
from analytics.simulation.models import RaceStateAtDecision, SimulationParameters

def estimate_tyre_degradation(compound: str, tyre_age: int, params: SimulationParameters) -> float:
    """
    Estimates the time loss due to tyre wear.
    Uses pre-calibrated slopes to guarantee no future-data leakage.
    """
    comp = compound.upper() if compound else "UNKNOWN"
    rate = params.degradation_slopes.get(comp, params.fallback_degradation)
    
    # Linear degradation for simplicity in Phase 3A
    return rate * tyre_age

def predict_lap_time(state: RaceStateAtDecision, 
                     target_lap: int, 
                     current_compound: str, 
                     current_tyre_age: int,
                     params: SimulationParameters) -> Tuple[float, float, float]:
    """
    Predicts the expected lap time for a future lap.
    
    Logic:
    Base Pace (at decision point)
    - Revert the tyre degradation effect embedded in the base pace
    - Revert the fuel effect embedded in the base pace
    + Add the new tyre degradation effect for the current tyre age and compound
    + Add the new compound delta (if compound changed)
    + Add the fuel effect for the new target lap
    
    Uncertainty:
    Residual uncertainty grows by 0.1s per lap into the future.
    """
    # 1. Establish Driver's True Base Pace (0 age, SOFT compound, at decision lap weight)
    # The rolling pace from Phase 2 already embeds the degradation of the tyre they were on.
    old_comp = state.current_compound.upper() if state.current_compound else "UNKNOWN"
    
    # Remove degradation of old tyre
    old_deg = estimate_tyre_degradation(old_comp, state.tyre_age, params)
    
    # Remove compound delta of old tyre to normalize to SOFT
    old_delta = params.compound_deltas.get(old_comp, params.fallback_compound_delta)
    
    # Base theoretical pace on SOFT tyres at age 0 at the decision lap fuel load
    # If rolling pace is NaN (e.g. out lap), fallback to base_lap_time
    reference_pace = state.rolling_pace if not math.isnan(state.rolling_pace) else state.base_lap_time
    if math.isnan(reference_pace):
        # Fallback to an arbitrary normal lap time if absolutely no data exists
        reference_pace = 95.0 
        
    normalized_base_pace = reference_pace - old_deg - old_delta
    
    # 2. Project to target lap
    # Fuel difference (target lap is later, car is lighter, so pace drops)
    laps_advanced = target_lap - state.decision_lap
    fuel_improvement = laps_advanced * params.fuel_burn_effect
    
    # New tyre degradation
    new_comp = current_compound.upper() if current_compound else "UNKNOWN"
    new_deg = estimate_tyre_degradation(new_comp, current_tyre_age, params)
    
    # New compound delta
    new_delta = params.compound_deltas.get(new_comp, params.fallback_compound_delta)
    
    # Calculate final predicted pace
    predicted_time = normalized_base_pace - fuel_improvement + new_deg + new_delta
    
    # 3. Uncertainty model
    # Uncertainty grows over time. Baseline +/- 0.3s, + 0.1s per lap advanced.
    uncertainty = params.baseline_uncertainty + (laps_advanced * params.uncertainty_growth_per_lap)
    
    lower_bound = predicted_time - uncertainty
    upper_bound = predicted_time + uncertainty
    
    return predicted_time, lower_bound, upper_bound
