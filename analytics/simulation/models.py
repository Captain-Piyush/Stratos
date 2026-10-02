from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class RaceStateAtDecision:
    """Represents the factual state of the race at the decision point (Lap N)."""
    session_key: int
    driver_number: int
    decision_lap: int
    
    # Current pace indicators (extracted from Phase 2 features)
    base_lap_time: float
    rolling_pace: float
    pace_trend: float
    
    # Current tyre state
    current_compound: str
    tyre_age: int
    
    # Race progression
    total_race_laps: int
    cumulative_race_time: float
    current_position: float
    gap_to_leader: float
    
    # Environmental/Track State at decision point
    air_temperature: float = 25.0
    track_temperature: float = 35.0
    safety_car_active: bool = False
    
    # Known competitors (simple representation)
    # A list of dictionaries: {'driver_number': 16, 'gap_to_leader': 10.5, 'rolling_pace': 98.5}
    competitors: List[Dict] = field(default_factory=list)

@dataclass
class CalibrationProfile:
    """Empirical calibration artifact."""
    version: str
    calibration_date: str
    calibration_races: List[int]
    
    # Empirical parameter values
    degradation_slopes: Dict[str, Dict[str, Any]]
    compound_deltas: Dict[str, Dict[str, Any]]
    fuel_burn_effect: Dict[str, Any]
    
    # Pit loss distribution
    pit_loss: Dict[str, Any]
    circuit_pit_loss: Dict[int, Dict[str, Any]] # e.g. {7953: {'value': 24.5, ...}}
    
    # Residual uncertainties
    residuals: Dict[str, Dict[str, Any]]
    
    # Uncertainty scales
    degradation_uncertainty: Dict[str, Any]
    
    # Fallback missing data values
    fallback_degradation: Dict[str, Any]
    fallback_compound_delta: Dict[str, Any]
    
    # Fallback hierarchies and sample sizes can be stored in metadata
    metadata: Dict = field(default_factory=dict)

@dataclass
class SimulationParameters:
    """Explicit parameters governing the simulation physics."""
    fuel_burn_effect: float = 0.06  # seconds gained per lap as fuel burns
    
    # Tyre degradation slope (seconds per lap of age)
    degradation_slopes: Dict[str, float] = field(default_factory=dict)
    
    # Base pace offset relative to SOFT (seconds)
    compound_deltas: Dict[str, float] = field(default_factory=dict)
    
    # Fallback properties
    fallback_degradation: float = 0.08
    fallback_compound_delta: float = 0.6
    
    # Pit stop loss
    base_pit_loss: float = 24.0
    
    # Uncertainty
    baseline_uncertainty: float = 0.3
    uncertainty_growth_per_lap: float = 0.1
    
    def apply_calibration(self, profile: CalibrationProfile, session_key: Optional[int] = None):
        """Replaces physical assumptions with calibrated empirical parameters."""
        self.fuel_burn_effect = profile.fuel_burn_effect['value']
        
        self.fallback_degradation = profile.fallback_degradation['value']
        self.fallback_compound_delta = profile.fallback_compound_delta['value']
        
        for comp, data in profile.degradation_slopes.items():
            self.degradation_slopes[comp] = data['value']
            
        for comp, data in profile.compound_deltas.items():
            self.compound_deltas[comp] = data['value']
        
        # Apply circuit-specific pit loss if available and accepted, otherwise global fallback
        if session_key and session_key in profile.circuit_pit_loss:
            c_data = profile.circuit_pit_loss[session_key]
            if c_data['quality_status'] == 'ACCEPTED':
                self.base_pit_loss = c_data['value']
            else:
                self.base_pit_loss = profile.pit_loss['value']
        else:
            self.base_pit_loss = profile.pit_loss['value']
            
        self.baseline_uncertainty = profile.residuals['std']['value']
        self.uncertainty_growth_per_lap = profile.degradation_uncertainty['value']

@dataclass
class StrategyPlan:
    """Represents a hypothetical strategy for a driver."""
    # List of planned pit laps. e.g. [36]
    pit_laps: List[int]
    
    # List of compounds to fit at each pit lap. e.g. ["HARD"]
    pit_compounds: List[str]
    
    def __post_init__(self):
        if len(self.pit_laps) != len(self.pit_compounds):
            raise ValueError("Number of pit laps must match number of pit compounds")
            
    @property
    def stable_id(self) -> int:
        import hashlib
        plan_str = "_".join(f"{l}{c}" for l, c in zip(self.pit_laps, self.pit_compounds))
        if not plan_str:
            plan_str = "stay_out"
        return int(hashlib.md5(plan_str.encode()).hexdigest()[:8], 16)

@dataclass
class SimulatedLap:
    """Represents a single simulated lap."""
    lap_number: int
    predicted_lap_time: float
    predicted_lap_time_lower: float
    predicted_lap_time_upper: float
    
    compound: str
    tyre_age: int
    
    pit_event: bool
    pit_time_loss: float
    
    cumulative_race_time: float
    
    # Estimates
    estimated_position: Optional[float] = None
    estimated_gap_to_leader: Optional[float] = None

@dataclass
class SimulationResult:
    """The final result of a forward simulation."""
    session_key: int
    driver_number: int
    strategy: StrategyPlan
    
    laps: List[SimulatedLap]
    
    predicted_total_race_time: float
    estimated_finish_position: Optional[float]
    total_pit_time_loss: float
    
    # Metadata for reporting
    strategy_assumptions: str
    simulation_horizon: int
