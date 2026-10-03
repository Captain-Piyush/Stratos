from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime

class CandidateSummary(BaseModel):
    strategy_id: str
    description: str
    expected_time: Optional[float] = None
    median_time: Optional[float] = None
    p10_time: Optional[float] = None
    p90_time: Optional[float] = None
    decision_score: Optional[float] = None
    probability_vs_baseline: Optional[float] = None
    is_valid: bool = True
    constraint_status: str = "VALID"
    is_selected: bool = False

class StrategyDecisionEvent(BaseModel):
    session_key: int
    timestamp: datetime
    driver_number: int
    decision_lap: int
    trigger: str = "UNKNOWN"
    selected_strategy: str
    objective: str
    decision_score: float
    decision_confidence: str  # HIGH, MEDIUM, LOW
    probability_selected_beats_baseline: Optional[float] = None
    candidate_summary: List[CandidateSummary] = Field(default_factory=list)
    explanation: str
    pit_window_open: Optional[int] = None
    pit_window_close: Optional[int] = None

    
    # Versioning
    software_version: str = "6.0.0"
    simulation_version: str = "3.0.0"
    decision_version: str = "3.1.0"
    calibration_version: str
    
    # Reproducibility
    monte_carlo_seed: int = 42
    state_snapshot_hash: str = ""
    decision_id: str = ""
