from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime

from analytics.simulation.models import RaceStateAtDecision, StrategyPlan
from analytics.simulation.decision import DecisionObjective, DecisionResult
from analytics.simulation.montecarlo import StrategyDistribution

@dataclass
class ReplaySnapshot:
    """The factual boundary representing the past."""
    session_key: int
    driver_number: int
    decision_lap: int
    race_distance: int
    race_state_at_decision: RaceStateAtDecision
    available_features: dict
    snapshot_timestamp: datetime

@dataclass
class DecisionSnapshot:
    """The frozen decision generated at the replay boundary."""
    decision_time: datetime
    selected_strategy: Optional[StrategyPlan]
    candidate_strategies: List[StrategyPlan]
    decision_objective: DecisionObjective
    decision_score: Optional[float]
    confidence: str
    explanation: str
    monte_carlo_summary: List[StrategyDistribution]
    model_version: str
    probability_vs_baseline: Optional[float] = None

from enum import Enum

class OutcomeStatus(Enum):
    FINISHED = "FINISHED"
    RETIRED = "RETIRED"
    UNKNOWN = "UNKNOWN"

@dataclass
class HistoricalOutcome:
    """The actual future race data loaded after the decision is frozen."""
    actual_strategy: str # e.g. "PIT LAP 32 -> HARD" or "UNKNOWN"
    pit_source: str # "DIRECT", "INFERRED", "UNKNOWN"
    strategy_source: str # "DIRECT", "INFERRED", "UNKNOWN"
    actual_pit_laps: List[int]
    actual_compounds: List[str]
    actual_finish_position: Optional[float]
    actual_race_time: Optional[float]
    actual_outcome_from_decision_point: Optional[float]
    outcome_status: OutcomeStatus = OutcomeStatus.UNKNOWN
    retirement_lap: Optional[int] = None
    retirement_reason: Optional[str] = None
