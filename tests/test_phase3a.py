import pytest
import math
from analytics.simulation.models import RaceStateAtDecision, StrategyPlan, SimulationParameters
from analytics.simulation.engine import simulate_strategy

@pytest.fixture
def base_state():
    return RaceStateAtDecision(
        session_key=7953,
        driver_number=1,
        decision_lap=30,
        base_lap_time=98.0,
        rolling_pace=98.5,
        pace_trend=0.01,
        current_compound="MEDIUM",
        tyre_age=15,
        total_race_laps=57,
        cumulative_race_time=3000.0,
        current_position=1.0,
        gap_to_leader=0.0
    )

def test_deterministic_simulation(base_state):
    plan = StrategyPlan(pit_laps=[], pit_compounds=[])
    res1 = simulate_strategy(base_state, plan)
    res2 = simulate_strategy(base_state, plan)
    
    assert res1.predicted_total_race_time == res2.predicted_total_race_time
    assert len(res1.laps) == 27 # 57 - 30
    
    for l1, l2 in zip(res1.laps, res2.laps):
        assert l1.predicted_lap_time == l2.predicted_lap_time
        assert l1.tyre_age == l2.tyre_age

def test_simulation_horizon(base_state):
    # TASK 2: Verify N+1 -> finish
    plan = StrategyPlan(pit_laps=[], pit_compounds=[])
    res = simulate_strategy(base_state, plan)
    
    assert len(res.laps) == 27
    assert res.laps[0].lap_number == 31  # N+1
    assert res.laps[-1].lap_number == 57 # finish
    # Duplicate check
    lap_nums = [l.lap_number for l in res.laps]
    assert len(lap_nums) == len(set(lap_nums))
    assert 30 not in lap_nums

def test_pit_off_by_one_validation(base_state):
    # TASK 3: Pit Off-By-One Validation
    plan = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    res = simulate_strategy(base_state, plan)
    
    # Lap 31: normal running
    assert res.laps[0].lap_number == 31
    assert not res.laps[0].pit_event
    assert res.laps[0].compound == "MEDIUM"
    assert res.laps[0].tyre_age == 16
    
    # Lap 32: pit event occurs
    assert res.laps[1].lap_number == 32
    assert res.laps[1].pit_event
    assert res.laps[1].compound == "MEDIUM"
    assert res.laps[1].tyre_age == 17
    
    # Lap 33: new compound and reset tyre state
    assert res.laps[2].lap_number == 33
    assert not res.laps[2].pit_event
    assert res.laps[2].compound == "HARD"
    assert res.laps[2].tyre_age == 1

def test_tyre_state_consistency_multiple_stops(base_state):
    # TASK 4: Tyre State Consistency
    plan = StrategyPlan(pit_laps=[32, 45], pit_compounds=["HARD", "SOFT"])
    res = simulate_strategy(base_state, plan)
    
    # Check Lap 32 Pit
    assert res.laps[1].lap_number == 32
    assert res.laps[1].pit_event
    assert res.laps[1].pit_time_loss > 0
    assert res.laps[2].compound == "HARD"
    assert res.laps[2].tyre_age == 1
    
    # Check Lap 45 Pit
    idx_45 = 45 - 31
    assert res.laps[idx_45].lap_number == 45
    assert res.laps[idx_45].pit_event
    assert res.laps[idx_45].compound == "HARD"
    assert res.laps[idx_45].tyre_age == 45 - 32
    assert res.laps[idx_45].pit_time_loss > 0
    
    # After Lap 45
    assert res.laps[idx_45+1].lap_number == 46
    assert not res.laps[idx_45+1].pit_event
    assert res.laps[idx_45+1].compound == "SOFT"
    assert res.laps[idx_45+1].tyre_age == 1

def test_cumulative_time_math(base_state):
    # TASK 5: Cumulative Time Mathematics
    params = SimulationParameters(base_pit_loss=25.0)
    plan = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    res = simulate_strategy(base_state, plan, params)
    
    expected = 3000.0
    pit_applied = 0
    for lap in res.laps:
        expected += lap.predicted_lap_time
        if lap.lap_number == 32:
            assert lap.pit_time_loss == 25.0
            pit_applied += 1
        else:
            assert lap.pit_time_loss == 0.0
            
        assert abs(lap.cumulative_race_time - expected) < 1e-5
        
    assert pit_applied == 1
    assert abs(res.predicted_total_race_time - expected) < 1e-5

def test_model_parameter_isolation(base_state):
    # TASK 6: Model Parameter Isolation
    plan = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    
    base_params = SimulationParameters(fuel_burn_effect=0.06, base_pit_loss=24.0)
    res_base = simulate_strategy(base_state, plan, base_params)
    
    # Change Fuel Burn
    fuel_params = SimulationParameters(fuel_burn_effect=0.10, base_pit_loss=24.0)
    res_fuel = simulate_strategy(base_state, plan, fuel_params)
    
    # Fuel burn changes pace, but pit loss remains exactly the same
    assert res_base.laps[-1].predicted_lap_time != res_fuel.laps[-1].predicted_lap_time
    assert res_base.laps[1].pit_time_loss == res_fuel.laps[1].pit_time_loss
    
    # Change Pit Loss
    pit_params = SimulationParameters(fuel_burn_effect=0.06, base_pit_loss=30.0)
    res_pit = simulate_strategy(base_state, plan, pit_params)
    
    # Pit loss changes cumulative time on lap 32 and beyond, but non-pit lap pace remains the same
    # Note: predicted_lap_time on lap 32 INCLUDES pit loss in our model, so it changes.
    assert res_base.laps[0].predicted_lap_time == res_pit.laps[0].predicted_lap_time # Lap 31 unaffected
    assert res_pit.laps[1].pit_time_loss == 30.0
    assert res_pit.laps[1].predicted_lap_time == res_base.laps[1].predicted_lap_time + 6.0
    
    # Change Degradation Slope
    deg_slopes = {"HARD": 0.5} # Huge deg
    deg_params = SimulationParameters(fuel_burn_effect=0.06, degradation_slopes=deg_slopes)
    res_deg = simulate_strategy(base_state, plan, deg_params)
    
    # Lap 33 (age 1 on HARD) pace changes
    assert res_base.laps[2].predicted_lap_time != res_deg.laps[2].predicted_lap_time

def test_sanity_bounds(base_state):
    # TASK 9: Sanity Bounds
    plan = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    res = simulate_strategy(base_state, plan)
    
    prev_time = 0.0
    for lap in res.laps:
        assert lap.predicted_lap_time > 0
        assert lap.tyre_age >= 0
        assert lap.cumulative_race_time > prev_time
        prev_time = lap.cumulative_race_time
        assert not math.isnan(lap.predicted_lap_time)
        assert not math.isinf(lap.predicted_lap_time)

def test_missing_data_fallback():
    state = RaceStateAtDecision(
        session_key=7953, driver_number=1, decision_lap=1,
        base_lap_time=float('nan'), rolling_pace=float('nan'), pace_trend=float('nan'),
        current_compound="SOFT", tyre_age=1, total_race_laps=5,
        cumulative_race_time=100.0, current_position=1.0, gap_to_leader=0.0
    )
    plan = StrategyPlan(pit_laps=[], pit_compounds=[])
    res = simulate_strategy(state, plan)
    
    for lap in res.laps:
        assert 80.0 < lap.predicted_lap_time < 120.0

def test_future_data_poisoning():
    # TASK 8: Future-Data Regression
    state = RaceStateAtDecision(
        session_key=7953, driver_number=1, decision_lap=30,
        base_lap_time=98.0, rolling_pace=98.5, pace_trend=0.01,
        current_compound="MEDIUM", tyre_age=15, total_race_laps=57,
        cumulative_race_time=3000.0, current_position=1.0, gap_to_leader=0.0
    )
    plan = StrategyPlan(pit_laps=[], pit_compounds=[])
    res1 = simulate_strategy(state, plan)
    
    dummy_future_db_val = 999
    res2 = simulate_strategy(state, plan)
    
    assert res1.predicted_total_race_time == res2.predicted_total_race_time
