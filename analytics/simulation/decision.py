from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from analytics.simulation.models import StrategyPlan
from analytics.simulation.montecarlo import MonteCarloResult, StrategyDistribution

class DecisionObjective(Enum):
    MIN_EXPECTED_TIME = "MIN_EXPECTED_TIME"
    MIN_MEDIAN_TIME = "MIN_MEDIAN_TIME"
    RISK_ADJUSTED_TIME = "RISK_ADJUSTED_TIME"
    ROBUST_OUTCOME = "ROBUST_OUTCOME"

@dataclass
class RiskPreferences:
    risk_aversion: float = 1.0  # Multiplier for downside penalty
    downside_percentile: float = 90.0  # e.g., P90
    minimum_pairwise_win_probability: float = 0.50  # Needed to beat baseline
    minimum_valid_probability: float = 0.90 # Valid runs / Total runs

@dataclass
class DecisionConstraints:
    maximum_pit_stops: Optional[int] = None
    allowed_compounds: Optional[List[str]] = None
    earliest_pit_lap: Optional[int] = None
    latest_pit_lap: Optional[int] = None

@dataclass
class DecisionResult:
    selected_strategy: Optional[StrategyPlan]
    objective: DecisionObjective
    decision_score: Optional[float]
    confidence: str 
    expected_time: Optional[float]
    median_time: Optional[float]
    risk_measure: Optional[float]
    probability_vs_baseline: Optional[float]
    key_drivers: List[str]
    alternatives_considered: int
    constraints_applied: int
    model_version: str
    explanation: str
    is_abstention: bool

def _is_valid_under_constraints(plan: StrategyPlan, constraints: DecisionConstraints) -> bool:
    if constraints.maximum_pit_stops is not None:
        if len(plan.pit_laps) > constraints.maximum_pit_stops:
            return False
            
    if constraints.allowed_compounds is not None:
        for comp in plan.pit_compounds:
            if comp not in constraints.allowed_compounds:
                return False
                
    if constraints.earliest_pit_lap is not None:
        if any(l < constraints.earliest_pit_lap for l in plan.pit_laps):
            return False
            
    if constraints.latest_pit_lap is not None:
        if any(l > constraints.latest_pit_lap for l in plan.pit_laps):
            return False
            
    return True

def get_percentile(dist: StrategyDistribution, pct: float) -> float:
    if pct == 10.0: return dist.p10
    elif pct == 25.0: return dist.p25
    elif pct == 50.0: return dist.p50
    elif pct == 75.0: return dist.p75
    elif pct == 90.0: return dist.p90
    # Default fallback if exactly matching isn't possible (though ideally we interpolate or expose more)
    return dist.p90

def score_strategy(
    dist: StrategyDistribution, 
    objective: DecisionObjective, 
    risk: RiskPreferences
) -> float:
    """
    Lower score is better (represents lower race time).
    """
    if objective == DecisionObjective.MIN_EXPECTED_TIME:
        return dist.mean_race_time
        
    elif objective == DecisionObjective.MIN_MEDIAN_TIME:
        return dist.median_race_time
        
    elif objective == DecisionObjective.RISK_ADJUSTED_TIME:
        # Example math: Mean Time + (Risk Aversion * (Downside - Mean Time))
        downside = get_percentile(dist, risk.downside_percentile)
        downside_penalty = max(0.0, downside - dist.mean_race_time)
        return dist.mean_race_time + (risk.risk_aversion * downside_penalty)
        
    elif objective == DecisionObjective.ROBUST_OUTCOME:
        # Focus strictly on minimizing the worst-case scenario
        return get_percentile(dist, risk.downside_percentile)
        
    raise ValueError("Unknown decision objective")

def evaluate_decision(
    candidate_strategies: List[StrategyPlan],
    mc_result: MonteCarloResult,
    objective: DecisionObjective,
    risk_preferences: RiskPreferences,
    constraints: DecisionConstraints,
    baseline_index: Optional[int] = None
) -> DecisionResult:
    """
    Evaluates candidate strategies based on explicit policies and Monte Carlo results.
    Can abstain if no clear winner exists or constraints eliminate all options.
    """
    if not candidate_strategies or not mc_result.distributions:
        return _abstain("No candidates or distributions provided.", objective)

    # 1. Apply Constraints
    viable_indices = []
    for idx, plan in enumerate(candidate_strategies):
        if _is_valid_under_constraints(plan, constraints):
            # Also check Monte Carlo validity constraint
            dist = mc_result.distributions[idx]
            total_runs = dist.valid_run_count + dist.invalid_run_count
            if total_runs > 0 and (dist.valid_run_count / total_runs) >= risk_preferences.minimum_valid_probability:
                viable_indices.append(idx)
                
    if not viable_indices:
        return _abstain("All strategies eliminated by constraints or Monte Carlo validity checks.", objective)
        
    # 2. Score Viable Strategies
    scored_strats = []
    for idx in viable_indices:
        dist = mc_result.distributions[idx]
        score = score_strategy(dist, objective, risk_preferences)
        scored_strats.append((idx, score))
        
    # Sort by score ascending (lower time is better)
    scored_strats.sort(key=lambda x: x[1])
    
    best_idx, best_score = scored_strats[0]
    best_dist = mc_result.distributions[best_idx]
    best_plan = candidate_strategies[best_idx]
    
    # 3. Check Baseline Minimums if a baseline was specified
    prob_vs_base = None
    if baseline_index is not None and baseline_index in viable_indices:
        # Find the pairwise comparison where best_idx beats baseline_index
        if best_idx == baseline_index:
            # We are sticking to the baseline. That's fine.
            prob_vs_base = 0.5 
        else:
            # We want to ensure switching to this new strategy meets risk.minimum_pairwise_win_probability
            for comp in mc_result.baseline_comparisons:
                if comp.strategy_a_index == best_idx and comp.strategy_b_index == baseline_index:
                    prob_vs_base = comp.probability_strategy_a_beats_b
                    break
            
            if prob_vs_base is not None and prob_vs_base < risk_preferences.minimum_pairwise_win_probability:
                # We do not have enough confidence to switch. Default back to baseline.
                best_idx = baseline_index
                best_plan = candidate_strategies[baseline_index]
                best_dist = mc_result.distributions[baseline_index]
                best_score = score_strategy(best_dist, objective, risk_preferences)
                prob_vs_base = 0.5
                
    # 4. Confidence Definition
    # Confidence is a heuristic measure based on separation between objective scores. 
    # It is NOT a calibrated probability of correctness.
    # Boundaries: HIGH >= 3.0, MEDIUM >= 1.0, LOW < 1.0
    confidence = "LOW"
    key_drivers = []
    
    if len(scored_strats) > 1:
        runner_up_idx, runner_up_score = scored_strats[1]
        score_gap = runner_up_score - best_score
        
        # Abstention evaluated before final strategy selection.
        # If the gap is less than 0.5s, it's effectively a tie. Abstain.
        if score_gap < 0.5 and (baseline_index is None or best_idx != baseline_index):
            return _abstain(
                f"Top strategies are statistically indistinguishable (score gap: {score_gap:.3f}s < 0.5s).", 
                objective
            )
            
        if score_gap >= 3.0:
            confidence = "HIGH"
        elif score_gap >= 1.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
            
        key_drivers.append(f"Separation from runner-up: {score_gap:.2f}s")
    else:
        confidence = "HIGH"
        key_drivers.append("Only one viable strategy remained.")
        
    # 5. Explanation Generation
    # Explanation strictly traces to the result object values to prevent drift.
    explanation = f"Selected Strategy {best_idx} ({best_plan.pit_compounds}) under objective {objective.value}.\n"
    explanation += f"Score: {best_score:.2f}s. "
    explanation += f"Mean Time: {best_dist.mean_race_time:.2f}s. "
    downside_val = get_percentile(best_dist, risk_preferences.downside_percentile)
    explanation += f"P{int(risk_preferences.downside_percentile)} Downside: {downside_val:.2f}s.\n"
    if prob_vs_base is not None:
        explanation += f"Probability vs Baseline: {prob_vs_base*100:.1f}%.\n"
    
    return DecisionResult(
        selected_strategy=best_plan,
        objective=objective,
        decision_score=best_score,
        confidence=confidence,
        expected_time=best_dist.mean_race_time,
        median_time=best_dist.median_race_time,
        risk_measure=downside_val,
        probability_vs_baseline=prob_vs_base,
        key_drivers=key_drivers,
        alternatives_considered=len(candidate_strategies),
        constraints_applied=len(candidate_strategies) - len(viable_indices),
        model_version="1.0",
        explanation=explanation,
        is_abstention=False
    )

def _abstain(reason: str, objective: DecisionObjective) -> DecisionResult:
    return DecisionResult(
        selected_strategy=None,
        objective=objective,
        decision_score=None,
        confidence="NONE",
        expected_time=None,
        median_time=None,
        risk_measure=None,
        probability_vs_baseline=None,
        key_drivers=[reason],
        alternatives_considered=0,
        constraints_applied=0,
        model_version="1.0",
        explanation=f"NO CLEAR DECISION. Abstaining because: {reason}",
        is_abstention=True
    )
