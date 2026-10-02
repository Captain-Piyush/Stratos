from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

from analytics.replay.models import DecisionSnapshot, HistoricalOutcome
from analytics.simulation.models import StrategyPlan, SimulationParameters
from analytics.simulation.montecarlo import MonteCarloParameters
from analytics.simulation.decision import DecisionObjective, RiskPreferences, DecisionConstraints

class FailureTag(str, Enum):
    TRAFFIC_UNMODELED = "TRAFFIC_UNMODELED"
    PIT_LOSS_ERROR = "PIT_LOSS_ERROR"
    TYRE_DEGRADATION_ERROR = "TYRE_DEGRADATION_ERROR"
    SAFETY_CAR_EFFECT = "SAFETY_CAR_EFFECT"
    WEATHER_EFFECT = "WEATHER_EFFECT"
    POSITION_MODEL_LIMITATION = "POSITION_MODEL_LIMITATION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    MODEL_UNCERTAINTY = "MODEL_UNCERTAINTY"
    STRATEGY_DIFFERENCE = "STRATEGY_DIFFERENCE"
    COUNTERFACTUAL_UNOBSERVED = "COUNTERFACTUAL_UNOBSERVED"
    UNKNOWN = "UNKNOWN"

class PerformanceCategory(str, Enum):
    SELECTED_EQUALS_ACTUAL = "SELECTED_EQUALS_ACTUAL"
    SELECTED_DIFFERS_FROM_ACTUAL = "SELECTED_DIFFERS_FROM_ACTUAL"
    ABSTAINED = "ABSTAINED"
    OUTCOME_NOT_COMPARABLE = "OUTCOME_NOT_COMPARABLE"
    
class CoverageStatus(str, Enum):
    COVERED = "COVERED"
    NOT_COVERED = "NOT_COVERED"
    NOT_OBSERVABLE_COUNTERFACTUAL = "NOT_OBSERVABLE_COUNTERFACTUAL"
    NOT_OBSERVABLE = "NOT_OBSERVABLE"

class ValidationCase(BaseModel):
    case_id: str
    session_key: int
    driver_number: int
    decision_lap: int
    candidate_strategies: List[StrategyPlan]
    simulation_parameters: SimulationParameters
    monte_carlo_parameters: MonteCarloParameters
    decision_objective: DecisionObjective
    risk_preferences: RiskPreferences
    decision_constraints: DecisionConstraints
    baseline_index: Optional[int]

class ValidationMetrics(BaseModel):
    performance_category: PerformanceCategory
    
    selected_strategy_index: Optional[int]
    baseline_strategy_index: Optional[int]
    
    # Counterfactual simulated expectations
    expected_time_selected: Optional[float]
    expected_time_baseline: Optional[float]
    counterfactual_expected_improvement: Optional[float]
    probability_selected_beats_baseline: Optional[float]
    risk_selected: Optional[float]
    risk_baseline: Optional[float]
    
    # Actual outcome reality
    actual_strategy: str
    actual_strategy_source: str
    actual_pit_source: str
    actual_race_outcome: Optional[float]
    outcome_status: str = "UNKNOWN"
    retirement_lap: Optional[int] = None
    retirement_reason: Optional[str] = None
    
    # Reality compared to selected prediction (only valid if selected == actual and FINISHED)
    actual_outcome_vs_model_prediction: Optional[float]
    absolute_prediction_error: Optional[float]
    
    p10_p90_coverage_status: CoverageStatus
    p25_p75_coverage_status: CoverageStatus

class ValidationResult(BaseModel):
    case_id: str
    session_key: int
    driver_number: int
    decision_lap: int
    is_valid: bool
    is_abstention: bool
    decision_snapshot: Optional[DecisionSnapshot]
    historical_outcome: Optional[HistoricalOutcome]
    evaluation_metrics: Optional[ValidationMetrics]
    failure_tags: List[FailureTag]

class RaceSummary(BaseModel):
    session_key: int
    driver_number: int
    total_cases: int
    valid_cases: int
    invalid_cases: int
    abstentions: int
    selected_equals_actual_count: int
    selected_differs_from_actual_count: int
    unknown_actual_strategy_count: int
    
    # Counterfactual expectation aggregates (model output only)
    mean_expected_improvement: float
    median_expected_improvement: float
    p10_expected_improvement: float
    p25_expected_improvement: float
    p50_expected_improvement: float
    p75_expected_improvement: float
    p90_expected_improvement: float
    worst_expected_improvement: float
    best_expected_improvement: float
    
    # Errors (only for selected == actual)
    mean_signed_prediction_error: Optional[float]
    mean_absolute_prediction_error: Optional[float]
    median_absolute_prediction_error: Optional[float]
    p10_prediction_error: Optional[float]
    p90_prediction_error: Optional[float]
    
    # Coverage (only for selected == actual)
    p10_p90_eligible_cases: int
    p10_p90_covered_cases: int
    empirical_p10_p90_coverage: float
    
    p25_p75_eligible_cases: int
    p25_p75_covered_cases: int
    empirical_p25_p75_coverage: float
    
    failure_taxonomy_counts: Dict[str, int]
    abstention_reasons: Dict[str, int]

class OverallSummary(BaseModel):
    total_cases: int
    valid_cases: int
    invalid_cases: int
    abstentions: int
    selected_equals_actual_count: int
    selected_differs_from_actual_count: int
    unknown_actual_strategy_count: int
    
    mean_expected_improvement: float
    median_expected_improvement: float
    empirical_p10_p90_coverage: float
    empirical_p25_p75_coverage: float
    
    race_summaries: List[RaceSummary]
