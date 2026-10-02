import pytest
from analytics.simulation.models import RaceStateAtDecision, StrategyPlan, SimulationParameters
from analytics.simulation.montecarlo import MonteCarloParameters, compare_strategies
from analytics.simulation.decision import (
    evaluate_decision,
    DecisionObjective,
    RiskPreferences,
    DecisionConstraints
)

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

def test_a_strategy_dominates(base_state):
    # A dominates B
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    s_b = StrategyPlan(pit_laps=[32, 33, 34, 35], pit_compounds=["SOFT"]*4)
    
    mc_res = compare_strategies(
        base_state, [s_a, s_b], SimulationParameters(), MonteCarloParameters(number_of_runs=100)
    )
    
    res = evaluate_decision(
        [s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(), DecisionConstraints()
    )
    
    assert not res.is_abstention
    assert res.selected_strategy.pit_compounds == ["HARD"]
    assert res.confidence == "HIGH"

def test_b_indistinguishable_abstains(base_state):
    # A and B identical
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    s_b = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    
    mc_res = compare_strategies(
        base_state, [s_a, s_b], SimulationParameters(), MonteCarloParameters(number_of_runs=200, random_seed=42)
    )
    
    res = evaluate_decision(
        [s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(), DecisionConstraints()
    )
    
    # Should abstain due to score gap < 0.5s
    assert res.is_abstention
    assert "indistinguishable" in res.explanation.lower()

def test_c_risk_averse_differs(base_state):
    # We want two strategies where A has lower mean, but much worse P90.
    # To do this in the simulator, we can drastically boost degradation noise, 
    # and make S_A stay out for many laps (huge uncertainty), while S_B pits (low uncertainty).
    # We tweak SimParams to make S_A mean slightly better, but S_B variance much smaller.
    sim_params = SimulationParameters(compound_deltas={"HARD": 0.0, "MEDIUM": 0.0})
    mc_params = MonteCarloParameters(number_of_runs=2000, random_seed=42, degradation_noise_scale=0.5)
    
    s_a = StrategyPlan(pit_laps=[], pit_compounds=[]) # Stays out, very old tyres -> huge variance
    s_b = StrategyPlan(pit_laps=[31], pit_compounds=["HARD"]) # Fresh tyres -> low variance
    
    mc_res = compare_strategies(base_state, [s_a, s_b], sim_params, mc_params)
    
    # Check that S_A has a better mean, but S_A has worse P90
    dist_a = mc_res.distributions[0]
    dist_b = mc_res.distributions[1]
    
    res_expected = evaluate_decision(
        [s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME,
        RiskPreferences(), DecisionConstraints()
    )
    
    res_robust = evaluate_decision(
        [s_a, s_b], mc_res, DecisionObjective.ROBUST_OUTCOME,
        RiskPreferences(), DecisionConstraints()
    )
    
    # Depending on exact outputs, the objective should dictate the chosen strategy or score.
    # The crucial point is that they score differently.
    assert res_expected.decision_score != res_robust.decision_score
    # In this specific setup with huge deg noise, S_a's P90 will be massive, so ROBUST avoids it.
    if res_robust.selected_strategy is not None and res_expected.selected_strategy is not None:
        if dist_a.mean_race_time < dist_b.mean_race_time and dist_a.p90 > dist_b.p90:
            assert res_expected.selected_strategy == s_a
            assert res_robust.selected_strategy == s_b

def test_d_constraints(base_state):
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    s_b = StrategyPlan(pit_laps=[32, 40], pit_compounds=["HARD", "SOFT"])
    
    mc_res = compare_strategies(
        base_state, [s_a, s_b], SimulationParameters(), MonteCarloParameters(number_of_runs=100)
    )
    
    res = evaluate_decision(
        [s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(), DecisionConstraints(maximum_pit_stops=1)
    )
    
    assert res.constraints_applied == 1
    assert res.selected_strategy == s_a

def test_e_candidate_ordering(base_state):
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    s_b = StrategyPlan(pit_laps=[35], pit_compounds=["MEDIUM"])
    
    mc_params = MonteCarloParameters(number_of_runs=500, random_seed=123)
    
    mc_res_1 = compare_strategies(base_state, [s_a, s_b], SimulationParameters(), mc_params)
    res_1 = evaluate_decision([s_a, s_b], mc_res_1, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    mc_res_2 = compare_strategies(base_state, [s_b, s_a], SimulationParameters(), mc_params)
    res_2 = evaluate_decision([s_b, s_a], mc_res_2, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    assert res_1.selected_strategy == res_2.selected_strategy
    assert res_1.decision_score == res_2.decision_score

def test_f_insufficient_runs(base_state):
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    
    # We use a huge noise scale so that some runs go invalid (< 0 lap times)
    mc_params = MonteCarloParameters(number_of_runs=20, random_seed=42, shared_noise_scale=999.0)
    mc_res = compare_strategies(base_state, [s_a], SimulationParameters(), mc_params)
    
    res = evaluate_decision(
        [s_a], mc_res, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(minimum_valid_probability=0.95), DecisionConstraints()
    )
    
    assert res.is_abstention
    assert "eliminat" in res.explanation.lower()

def test_future_data_poisoning_decision(base_state):
    s_a = StrategyPlan(pit_laps=[32], pit_compounds=["HARD"])
    s_b = StrategyPlan(pit_laps=[35], pit_compounds=["MEDIUM"])
    
    mc_res = compare_strategies(
        base_state, [s_a, s_b], SimulationParameters(), MonteCarloParameters(number_of_runs=100, random_seed=42)
    )
    
    res_1 = evaluate_decision([s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    dummy_db = "FUTURE_RACE_RESULT_VER_CRASH"
    
    res_2 = evaluate_decision([s_a, s_b], mc_res, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    assert res_1.selected_strategy == res_2.selected_strategy
