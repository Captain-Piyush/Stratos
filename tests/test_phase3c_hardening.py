import pytest
from typing import List
from dataclasses import replace
from analytics.simulation.decision import (
    score_strategy,
    evaluate_decision,
    DecisionObjective,
    RiskPreferences,
    DecisionConstraints,
    DecisionResult,
    get_percentile
)
from analytics.simulation.models import StrategyPlan
from analytics.simulation.montecarlo import StrategyDistribution, MonteCarloResult, StrategyComparison

def _mock_dist(mean: float, median: float, p10: float, p25: float, p50: float, p75: float, p90: float) -> StrategyDistribution:
    return StrategyDistribution(
        strategy_index=0,
        mean_race_time=mean,
        median_race_time=median,
        standard_deviation=10.0,
        min_race_time=mean-20,
        max_race_time=mean+20,
        p10=p10,
        p25=p25,
        p50=p50,
        p75=p75,
        p90=p90,
        valid_run_count=1000,
        invalid_run_count=0
    )

def test_objective_equations():
    # TASK 1 - OBJECTIVE EQUATION TESTS
    dist = _mock_dist(mean=100.0, median=99.0, p10=90.0, p25=95.0, p50=99.0, p75=105.0, p90=110.0)
    
    score_exp = score_strategy(dist, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences())
    assert score_exp == 100.0
    
    score_med = score_strategy(dist, DecisionObjective.MIN_MEDIAN_TIME, RiskPreferences())
    assert score_med == 99.0
    
    # RISK_ADJUSTED_TIME = Mean + (risk_aversion * max(0, downside - Mean))
    # By default, downside_percentile is 90.0, so P90 is 110.0
    # Downside = 110.0 - 100.0 = 10.0
    # risk_aversion = 1.0 -> score = 100.0 + 10.0 = 110.0
    score_risk = score_strategy(dist, DecisionObjective.RISK_ADJUSTED_TIME, RiskPreferences(risk_aversion=1.0, downside_percentile=90.0))
    assert score_risk == 110.0
    
    score_robust = score_strategy(dist, DecisionObjective.ROBUST_OUTCOME, RiskPreferences(downside_percentile=90.0))
    assert score_robust == 110.0

def test_risk_aversion_monotonicity():
    # TASK 2 - RISK AVERSION MONOTONICITY
    dist_a = _mock_dist(mean=100.0, median=100.0, p10=90.0, p25=95.0, p50=100.0, p75=120.0, p90=130.0) # Downside 30
    dist_b = _mock_dist(mean=105.0, median=105.0, p10=100.0, p25=102.0, p50=105.0, p75=108.0, p90=110.0) # Downside 5
    
    # Aversion = 0 -> behaves like MIN_EXPECTED_TIME
    score_a_0 = score_strategy(dist_a, DecisionObjective.RISK_ADJUSTED_TIME, RiskPreferences(risk_aversion=0.0))
    assert score_a_0 == 100.0 # Just the mean
    
    # As risk aversion increases, penalty increases
    score_a_1 = score_strategy(dist_a, DecisionObjective.RISK_ADJUSTED_TIME, RiskPreferences(risk_aversion=1.0))
    score_a_2 = score_strategy(dist_a, DecisionObjective.RISK_ADJUSTED_TIME, RiskPreferences(risk_aversion=2.0))
    assert score_a_1 == 100.0 + 30.0
    assert score_a_2 == 100.0 + 60.0
    assert score_a_2 > score_a_1 > score_a_0

def test_downside_percentile():
    # TASK 3 - DOWNSIDE PERCENTILE TEST
    dist = _mock_dist(mean=100.0, median=100.0, p10=90.0, p25=95.0, p50=100.0, p75=115.0, p90=130.0)
    
    score_75 = score_strategy(dist, DecisionObjective.ROBUST_OUTCOME, RiskPreferences(downside_percentile=75.0))
    assert score_75 == 115.0
    
    score_90 = score_strategy(dist, DecisionObjective.ROBUST_OUTCOME, RiskPreferences(downside_percentile=90.0))
    assert score_90 == 130.0

def _run_eval(gap: float) -> DecisionResult:
    s_a = StrategyPlan([], [])
    s_b = StrategyPlan([1], ["HARD"])
    
    dist_a = _mock_dist(100.0, 100.0, 90.0, 95.0, 100.0, 105.0, 110.0)
    dist_a.strategy_index = 0
    dist_b = _mock_dist(100.0 + gap, 100.0 + gap, 90.0 + gap, 95.0 + gap, 100.0 + gap, 105.0 + gap, 110.0 + gap)
    dist_b.strategy_index = 1
    
    mc = MonteCarloResult(1, 1, 1, 1, 1, [dist_a, dist_b], [], None, [])
    return evaluate_decision([s_a, s_b], mc, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())

def test_confidence_semantics():
    # TASK 4 - CONFIDENCE SEMANTICS & TASK 5 - ABSTENTION LOGIC
    # Gap exactly 3.0 -> HIGH
    res_3 = _run_eval(3.0)
    assert res_3.confidence == "HIGH"
    
    # Gap exactly 1.0 -> MEDIUM
    res_1 = _run_eval(1.0)
    assert res_1.confidence == "MEDIUM"
    
    # Gap exactly 0.5 -> LOW
    res_05 = _run_eval(0.5)
    assert res_05.confidence == "LOW"
    assert not res_05.is_abstention
    
    # Gap < 0.5 -> Abstention
    res_04 = _run_eval(0.49)
    assert res_04.is_abstention
    assert res_04.confidence == "NONE"

def test_baseline_switch_rule():
    # TASK 6 - BASELINE SWITCH RULE
    s_base = StrategyPlan([], [])
    s_new = StrategyPlan([1], ["HARD"])
    
    # Baseline is slower (score 105) vs New (score 100)
    dist_base = _mock_dist(105.0, 105.0, 105.0, 105.0, 105.0, 105.0, 105.0)
    dist_base.strategy_index = 0
    dist_new = _mock_dist(100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0)
    dist_new.strategy_index = 1
    
    # Setup pairwise: new beats base 52% of the time
    comp = StrategyComparison(1, 0, -5.0, -5.0, 0.52, 0.48)
    
    mc = MonteCarloResult(1, 1, 1, 1, 1, [dist_base, dist_new], [comp], 0, [comp])
    
    # If threshold is 55%, we should NOT switch
    res_no = evaluate_decision(
        [s_base, s_new], mc, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(minimum_pairwise_win_probability=0.55), DecisionConstraints(), baseline_index=0
    )
    assert res_no.selected_strategy == s_base
    
    # If threshold is 50%, we SHOULD switch
    res_yes = evaluate_decision(
        [s_base, s_new], mc, DecisionObjective.MIN_EXPECTED_TIME, 
        RiskPreferences(minimum_pairwise_win_probability=0.50), DecisionConstraints(), baseline_index=0
    )
    assert res_yes.selected_strategy == s_new

def test_constraint_order():
    # TASK 7 - CONSTRAINT ORDER
    s_valid = StrategyPlan([10], ["HARD"])
    s_invalid = StrategyPlan([10, 20, 30], ["SOFT", "SOFT", "SOFT"])
    
    # The invalid strategy is MASSIVELY faster, but should be ignored
    dist_v = _mock_dist(100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0)
    dist_v.strategy_index = 0
    dist_inv = _mock_dist(10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0)
    dist_inv.strategy_index = 1
    
    mc = MonteCarloResult(1, 1, 1, 1, 1, [dist_v, dist_inv], [], None, [])
    
    res = evaluate_decision(
        [s_valid, s_invalid], mc, DecisionObjective.MIN_EXPECTED_TIME,
        RiskPreferences(), DecisionConstraints(maximum_pit_stops=2)
    )
    
    assert res.selected_strategy == s_valid
    assert res.decision_score == 100.0
    assert res.constraints_applied == 1
    # Ensure runner-up logic doesn't crash or use the invalid score
    assert res.confidence == "HIGH"
    
def test_explanation_consistency():
    # TASK 8 - EXPLANATION CONSISTENCY
    res = _run_eval(3.5)
    
    # Verify values trace directly
    assert f"Score: {res.decision_score:.2f}s" in res.explanation
    assert f"Mean Time: {res.expected_time:.2f}s" in res.explanation
    assert f"Downside: {res.risk_measure:.2f}s" in res.explanation

def test_objective_invariance():
    # TASK 9 - OBJECTIVE INVARIANCE
    # Strategy A is purely better than Strategy B in every way
    s_a = StrategyPlan([], [])
    s_b = StrategyPlan([1], ["HARD"])
    
    dist_a = _mock_dist(100.0, 100.0, 90.0, 95.0, 100.0, 105.0, 110.0)
    dist_a.strategy_index = 0
    dist_b = _mock_dist(200.0, 200.0, 190.0, 195.0, 200.0, 205.0, 210.0)
    dist_b.strategy_index = 1
    
    mc = MonteCarloResult(1, 1, 1, 1, 1, [dist_a, dist_b], [], None, [])
    
    # All objectives must choose A
    for obj in DecisionObjective:
        res = evaluate_decision([s_a, s_b], mc, obj, RiskPreferences(), DecisionConstraints())
        assert res.selected_strategy == s_a

def test_order_invariance():
    # TASK 10 - ORDER INVARIANCE
    s_a = StrategyPlan([], [])
    s_b = StrategyPlan([1], ["HARD"])
    
    dist_a = _mock_dist(100.0, 100.0, 90.0, 95.0, 100.0, 105.0, 110.0)
    dist_b = _mock_dist(200.0, 200.0, 190.0, 195.0, 200.0, 205.0, 210.0)
    
    mc_1 = MonteCarloResult(1, 1, 1, 1, 1, [dist_a, dist_b], [], None, [])
    res_1 = evaluate_decision([s_a, s_b], mc_1, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    # Reverse order
    mc_2 = MonteCarloResult(1, 1, 1, 1, 1, [dist_b, dist_a], [], None, [])
    res_2 = evaluate_decision([s_b, s_a], mc_2, DecisionObjective.MIN_EXPECTED_TIME, RiskPreferences(), DecisionConstraints())
    
    assert res_1.selected_strategy == res_2.selected_strategy
    assert res_1.decision_score == res_2.decision_score
    assert res_1.confidence == res_2.confidence
