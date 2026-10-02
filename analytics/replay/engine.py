from datetime import datetime
from typing import List, Optional
import pandas as pd

from database.connection import db
from analytics.features.builder import build_feature_dataset
from analytics.simulation.models import RaceStateAtDecision, StrategyPlan, SimulationParameters
from analytics.simulation.montecarlo import MonteCarloParameters, compare_strategies
from analytics.simulation.decision import evaluate_decision, DecisionObjective, RiskPreferences, DecisionConstraints, DecisionResult
from analytics.replay.models import ReplaySnapshot, DecisionSnapshot, HistoricalOutcome, OutcomeStatus

def get_decision_lap_cutoff(session_key: int, driver_number: int, decision_lap: int) -> Optional[datetime]:
    if db.db is None:
        db.connect()
    laps_cursor = db.get_collection("laps").find({"session_key": session_key, "driver_number": driver_number, "lap_number": decision_lap})
    laps = list(laps_cursor)
    if not laps:
        return None
    lap = laps[0]
    start_date_str = lap.get("date_start")
    if not start_date_str:
        return None
    try:
        start_date = pd.to_datetime(start_date_str.replace("Z", "+00:00"))
        duration = lap.get("lap_duration")
        if pd.isna(duration):
            return start_date
        return start_date + pd.Timedelta(seconds=duration)
    except:
        return None

def create_replay_snapshot(session_key: int, driver_number: int, decision_lap: int) -> ReplaySnapshot:
    cutoff_time = get_decision_lap_cutoff(session_key, driver_number, decision_lap)
    if not cutoff_time:
        raise ValueError(f"Could not determine cutoff time for Lap {decision_lap}")
        
    df = build_feature_dataset(session_key, max_lap=decision_lap, cutoff_time=cutoff_time)
    
    if df.empty:
        raise ValueError("Feature dataset is empty.")
        
    driver_laps = df[(df['driver_number'] == driver_number) & (df['lap_number'] <= decision_lap)].sort_values('lap_number')
    if driver_laps.empty:
        raise ValueError("No data found for driver up to decision lap.")
        
    last_lap = driver_laps.iloc[-1]
    # Determine actual total race laps for the given driver
    total_laps_cursor = db.get_collection("laps").find({"session_key": session_key, "driver_number": driver_number}).sort("lap_number", -1).limit(1)
    total_laps_list = list(total_laps_cursor)
    total_race_laps = total_laps_list[0]["lap_number"] if total_laps_list else 57

    state = RaceStateAtDecision(
        session_key=session_key,
        driver_number=driver_number,
        decision_lap=decision_lap,
        base_lap_time=last_lap.get("lap_time", 90.0),
        rolling_pace=last_lap.get("rolling_mean_pace_3", last_lap.get("lap_time", 90.0)),
        pace_trend=last_lap.get("pace_trend", 0.0) if pd.notnull(last_lap.get("pace_trend")) else 0.0,
        current_compound=last_lap.get("tyre_compound", "UNKNOWN"),
        tyre_age=int(last_lap.get("tyre_age", 1)) if pd.notnull(last_lap.get("tyre_age")) else 1,
        total_race_laps=total_race_laps, 
        cumulative_race_time=0.0, 
        current_position=last_lap.get("position", 1.0) if pd.notnull(last_lap.get("position")) else 1.0,
        gap_to_leader=last_lap.get("gap_to_leader", 0.0) if pd.notnull(last_lap.get("gap_to_leader")) else 0.0,
        air_temperature=last_lap.get("air_temperature", 25.0) if pd.notnull(last_lap.get("air_temperature")) else 25.0,
        track_temperature=last_lap.get("track_temperature", 35.0) if pd.notnull(last_lap.get("track_temperature")) else 35.0,
        safety_car_active=bool(last_lap.get("safety_car_active", False))
    )
    
    max_laps = list(db.get_collection("laps").find({"session_key": session_key}).sort("lap_number", -1).limit(1))
    if max_laps:
        state.total_race_laps = max_laps[0]["lap_number"]
    
    cum_time = driver_laps['lap_time'].sum()
    state.cumulative_race_time = cum_time
    
    return ReplaySnapshot(
        session_key=session_key,
        driver_number=driver_number,
        decision_lap=decision_lap,
        race_distance=state.total_race_laps,
        race_state_at_decision=state,
        available_features=last_lap.to_dict(),
        snapshot_timestamp=cutoff_time
    )

def evaluate_historical_decision(
    snapshot: ReplaySnapshot,
    candidate_strategies: List[StrategyPlan],
    sim_params: SimulationParameters,
    mc_params: MonteCarloParameters,
    objective: DecisionObjective,
    risk: RiskPreferences,
    constraints: DecisionConstraints,
    baseline_index: Optional[int] = None
) -> DecisionSnapshot:
    
    mc_result = compare_strategies(
        snapshot.race_state_at_decision,
        candidate_strategies,
        sim_params,
        mc_params,
        baseline_index
    )
    
    decision = evaluate_decision(
        candidate_strategies,
        mc_result,
        objective,
        risk,
        constraints,
        baseline_index
    )
    
    return DecisionSnapshot(
        decision_time=datetime.utcnow(),
        selected_strategy=decision.selected_strategy,
        candidate_strategies=candidate_strategies,
        decision_objective=objective,
        decision_score=decision.decision_score,
        confidence=decision.confidence,
        explanation=decision.explanation,
        monte_carlo_summary=mc_result.distributions,
        model_version=decision.model_version,
        probability_vs_baseline=decision.probability_vs_baseline
    )

def extract_historical_outcome(session_key: int, driver_number: int, decision_lap: int) -> HistoricalOutcome:
    pits = list(db.get_collection("pit_stops").find({
        "session_key": session_key, 
        "driver_number": driver_number,
        "lap_number": {"$gt": decision_lap}
    }).sort("lap_number", 1))
    
    stints = list(db.get_collection("stints").find({
        "session_key": session_key, 
        "driver_number": driver_number,
    }).sort("stint_number", 1))

    actual_pit_laps = []
    actual_compounds = []
    pit_source = "UNKNOWN"
    strategy_source = "UNKNOWN"
    
    if pits:
        pit_source = "DIRECT"
        actual_pit_laps = [p["lap_number"] for p in pits]
        for pit_lap in actual_pit_laps:
            compound = "UNKNOWN"
            for s in stints:
                if s.get("lap_start", 0) == pit_lap or s.get("lap_start", 0) == pit_lap + 1:
                    compound = s.get("compound", "UNKNOWN")
                    break
            actual_compounds.append(compound)
        strategy_source = "DIRECT" if all(c != "UNKNOWN" for c in actual_compounds) else "INFERRED"
    else:
        # Fallback to stints to infer pit stops
        future_stints = [s for s in stints if s.get("lap_start", 0) > decision_lap]
        if future_stints:
            pit_source = "INFERRED"
            strategy_source = "INFERRED"
            for s in future_stints:
                pit_lap = s.get("lap_start", 0) - 1
                if pit_lap > decision_lap:
                    actual_pit_laps.append(pit_lap)
                    actual_compounds.append(s.get("compound", "UNKNOWN"))

    laps = list(db.get_collection("laps").find({
        "session_key": session_key, 
        "driver_number": driver_number
    }))
    
    future_laps = [l for l in laps if l.get("lap_number", 0) > decision_lap and l.get("lap_duration") is not None]
    
    if actual_pit_laps:
        actual_strategy = f"PIT LAPS {actual_pit_laps} -> {actual_compounds}"
    else:
        if future_laps:
            actual_strategy = "STAY OUT"
            pit_source = "DIRECT" if pits else "INFERRED"
            strategy_source = "INFERRED"
        else:
            actual_strategy = "UNKNOWN"
            pit_source = "UNKNOWN"
            strategy_source = "UNKNOWN"

    pos_data = list(db.get_collection("positions").find({
        "session_key": session_key, 
        "driver_number": driver_number
    }).sort("date", -1).limit(1))
    
    actual_finish_pos = pos_data[0]["position"] if pos_data else None
    
    # Determine Outcome Status (FINISHED vs RETIRED)
    session_laps_cursor = db.get_collection("laps").find({"session_key": session_key})
    session_laps_list = list(session_laps_cursor)
    
    if not session_laps_list:
        outcome_status = OutcomeStatus.UNKNOWN
        retirement_lap = None
    else:
        driver_end_times = {}
        driver_laps = {}
        for l in session_laps_list:
            d = l.get('driver_number')
            if 'date_start' in l and l.get('lap_duration'):
                t = pd.to_datetime(l['date_start'].replace('Z', '+00:00')) + pd.Timedelta(seconds=l['lap_duration'])
                if d not in driver_end_times or t > driver_end_times[d]:
                    driver_end_times[d] = t
                    driver_laps[d] = l.get('lap_number', 0)
                    
        max_laps = max(driver_laps.values()) if driver_laps else 0
        if max_laps == 0:
            outcome_status = OutcomeStatus.UNKNOWN
            retirement_lap = None
        else:
            winner_time = min([t for d, t in driver_end_times.items() if driver_laps[d] == max_laps])
            driver_max_lap = driver_laps.get(driver_number, 0)
            
            if driver_max_lap == 0:
                outcome_status = OutcomeStatus.UNKNOWN
                retirement_lap = None
            else:
                driver_end = driver_end_times[driver_number]
                if driver_end >= winner_time - pd.Timedelta(seconds=300):
                    outcome_status = OutcomeStatus.FINISHED
                    retirement_lap = None
                else:
                    outcome_status = OutcomeStatus.RETIRED
                    retirement_lap = driver_max_lap
        
    total_time = None
    outcome_from_decision = None
    if laps:
        total_time = sum([l.get("lap_duration", 0) for l in laps if l.get("lap_duration") is not None])
        if future_laps:
            outcome_from_decision = sum([l.get("lap_duration", 0) for l in future_laps])
            
    return HistoricalOutcome(
        actual_strategy,
        pit_source,
        strategy_source,
        actual_pit_laps,
        actual_compounds,
        actual_finish_pos,
        total_time,
        outcome_from_decision,
        outcome_status,
        retirement_lap,
        None # retirement_reason
    )
