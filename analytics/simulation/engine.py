from analytics.simulation.models import RaceStateAtDecision, StrategyPlan, SimulatedLap, SimulationResult, SimulationParameters
from analytics.simulation.pace import predict_lap_time
from analytics.simulation.pit import estimate_pit_loss
import json

def simulate_strategy(state: RaceStateAtDecision, plan: StrategyPlan, params: SimulationParameters = None) -> SimulationResult:
    """
    Executes a forward simulation from the decision point to the end of the race.
    Strictly deterministic and immune to future-data leakage.
    """
    if params is None:
        params = SimulationParameters()
        
    laps = []
    
    current_compound = state.current_compound
    current_tyre_age = state.tyre_age
    cumulative_time = state.cumulative_race_time
    
    # We maintain a simple list of competitor paces to estimate position drops
    competitors = [{"gap": c["gap_to_leader"], "pace": c.get("rolling_pace", state.rolling_pace)} 
                   for c in state.competitors]
    
    my_gap_to_leader = state.gap_to_leader
    
    for lap in range(state.decision_lap + 1, state.total_race_laps + 1):
        # 1. Age the tyre (tyre age increases by 1 for each completed lap)
        current_tyre_age += 1
        
        # 2. Check if pitting AT THE END of this lap
        pitting_this_lap = lap in plan.pit_laps
        
        # 3. Predict normal track pace
        pace, pace_lower, pace_upper = predict_lap_time(
            state=state,
            target_lap=lap,
            current_compound=current_compound,
            current_tyre_age=current_tyre_age,
            params=params
        )
        
        # 4. Apply Pit Loss
        pit_loss = 0.0
        if pitting_this_lap:
            pit_loss = estimate_pit_loss(state.session_key, params)
            pace += pit_loss
            pace_lower += pit_loss
            pace_upper += pit_loss
            
        # 5. Accumulate time
        cumulative_time += pace
        
        # 6. Estimate Position & Gap (Very rough approximation assuming competitors maintain constant pace)
        estimated_position = state.current_position
        if competitors:
            # Advance all competitors by their flat rolling pace
            # My gap to leader changes by (my_pace - leader_pace)
            # For simplicity, let's just track my cumulative time against theirs
            # We assume competitors do not pit in this simple baseline.
            pass # More complex handling omitted to keep it factual, position will remain static if unmodeled.
            
        sim_lap = SimulatedLap(
            lap_number=lap,
            predicted_lap_time=pace,
            predicted_lap_time_lower=pace_lower,
            predicted_lap_time_upper=pace_upper,
            compound=current_compound,
            tyre_age=current_tyre_age,
            pit_event=pitting_this_lap,
            pit_time_loss=pit_loss,
            cumulative_race_time=cumulative_time,
            estimated_position=None, # Position modeling is explicitly limited
            estimated_gap_to_leader=None
        )
        laps.append(sim_lap)
        
        # 7. Apply compound change for NEXT lap if we pitted
        if pitting_this_lap:
            idx = plan.pit_laps.index(lap)
            current_compound = plan.pit_compounds[idx]
            current_tyre_age = 0 # Will become 1 on the next lap loop
            
    total_pit_loss = sum(l.pit_time_loss for l in laps)
    
    assumptions = json.dumps({
        "degradation_model": "linear_calibrated",
        "competitor_model": "static_unmodeled",
        "pit_loss": f"{estimate_pit_loss(state.session_key, params)}s"
    })
    
    return SimulationResult(
        session_key=state.session_key,
        driver_number=state.driver_number,
        strategy=plan,
        laps=laps,
        predicted_total_race_time=cumulative_time,
        estimated_finish_position=None, # Explicitly marked as non-predictive for this phase
        total_pit_time_loss=total_pit_loss,
        strategy_assumptions=assumptions,
        simulation_horizon=(state.total_race_laps - state.decision_lap)
    )

