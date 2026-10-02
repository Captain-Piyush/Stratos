import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from analytics.simulation.models import RaceStateAtDecision, StrategyPlan, SimulationParameters, SimulationResult
from analytics.simulation.engine import simulate_strategy

@dataclass
class MonteCarloParameters:
    number_of_runs: int = 1000
    random_seed: int = 42
    minimum_valid_runs: int = 10
    
    # Noise scales (Standard deviations / Multipliers)
    shared_noise_scale: float = 1.0       # Multiplier for the environmental/shared uncertainty per lap
    degradation_noise_scale: float = 0.05 # Std dev of seconds per lap of degradation uncertainty
    pit_loss_noise_scale: float = 0.5     # Std dev of seconds for pit stop execution uncertainty

@dataclass
class StrategyDistribution:
    strategy_index: int
    mean_race_time: float
    median_race_time: float
    standard_deviation: float
    min_race_time: float
    max_race_time: float
    p10: float
    p25: float
    p50: float
    p75: float
    p90: float
    valid_run_count: int
    invalid_run_count: int

@dataclass
class StrategyComparison:
    strategy_a_index: int
    strategy_b_index: int
    mean_time_delta: float  # A - B. Negative means A is faster.
    median_time_delta: float
    probability_strategy_a_beats_b: float
    probability_strategy_b_beats_a: float

@dataclass
class MonteCarloResult:
    session_key: int
    driver_number: int
    decision_lap: int
    random_seed: int
    requested_runs: int
    
    distributions: List[StrategyDistribution]
    pairwise_comparisons: List[StrategyComparison]
    
    baseline_index: Optional[int] = None
    baseline_comparisons: List[StrategyComparison] = field(default_factory=list)

def compare_strategies(
    race_state: RaceStateAtDecision,
    strategies: List[StrategyPlan],
    simulation_parameters: SimulationParameters,
    monte_carlo_parameters: MonteCarloParameters,
    baseline_index: Optional[int] = None
) -> MonteCarloResult:
    """
    Runs a Monte Carlo simulation across multiple strategies using Common Random Numbers (CRN).
    No optimization is performed. This strictly quantifies uncertainty.
    """
    num_runs = monte_carlo_parameters.number_of_runs
    seed = monte_carlo_parameters.random_seed
    num_strats = len(strategies)
    
    if num_strats == 0:
        raise ValueError("No strategies provided for comparison.")
    if num_runs <= 0:
        raise ValueError("Number of Monte Carlo runs must be > 0.")
    if baseline_index is not None and (baseline_index < 0 or baseline_index >= num_strats):
        raise ValueError("Baseline index is out of bounds.")
        
    # We will compute the deterministic baseline for each strategy first
    deterministic_results = []
    for plan in strategies:
        # Check invalid strategies (pit lap > total laps)
        if any(p > race_state.total_race_laps for p in plan.pit_laps):
            raise ValueError("Strategy contains pit lap beyond race distance.")
            
        res = simulate_strategy(race_state, plan, simulation_parameters)
        deterministic_results.append(res)
        
    # Pre-calculate uncertainties for each lap of the horizon.
    laps_remaining = race_state.total_race_laps - race_state.decision_lap
    if laps_remaining <= 0:
        raise ValueError("No laps remaining to simulate.")
        
    uncertainties = np.array([
        simulation_parameters.baseline_uncertainty + (i * simulation_parameters.uncertainty_growth_per_lap)
        for i in range(1, laps_remaining + 1)
    ]) * monte_carlo_parameters.shared_noise_scale
    
    # Initialize the CRN PRNG for shared environmental noise
    rng = np.random.default_rng(seed)
    z_scores_shared = rng.standard_normal((num_runs, laps_remaining))
    shared_noise_matrix = z_scores_shared * uncertainties
    
    # We will collect final times. Shape: (num_strats, num_runs)
    final_times = np.zeros((num_strats, num_runs))
    valid_mask = np.ones((num_strats, num_runs), dtype=bool)
    
    for s_idx, det_res in enumerate(deterministic_results):
        det_lap_times = np.array([lap.predicted_lap_time for lap in det_res.laps])
        
        # Build Strategy-Specific Noise
        # This rng is seeded distinctly but deterministically per strategy to isolate it from the shared noise
        # We use a stable hash of the strategy plan so that ordering doesn't change distributions
        strat_rng = np.random.default_rng((seed + det_res.strategy.stable_id) % (2**32))
        
        # 1. Degradation noise: uncertainty scales with tyre age
        tyre_ages = np.array([lap.tyre_age for lap in det_res.laps])
        deg_std = tyre_ages * monte_carlo_parameters.degradation_noise_scale
        deg_noise = strat_rng.standard_normal((num_runs, laps_remaining)) * deg_std
        
        # 2. Pit stop noise
        pit_events = np.array([lap.pit_event for lap in det_res.laps])
        pit_noise = np.zeros((num_runs, laps_remaining))
        if np.any(pit_events):
            # Only generate pit noise where pit_event is true
            pit_z = strat_rng.standard_normal((num_runs, laps_remaining))
            pit_noise[:, pit_events] = pit_z[:, pit_events] * monte_carlo_parameters.pit_loss_noise_scale
            
        specific_noise = deg_noise + pit_noise
        
        # Total Stochastic Lap Time
        stochastic_lap_times = det_lap_times + shared_noise_matrix + specific_noise
        
        # Add the starting cumulative time to get final race times
        final_times[s_idx] = race_state.cumulative_race_time + np.sum(stochastic_lap_times, axis=1)
        
        # Sanity check: if any lap time < 0, invalidate that run
        invalid_runs = np.any(stochastic_lap_times <= 0, axis=1)
        valid_mask[s_idx, invalid_runs] = False
        
    # Build Distributions
    distributions = []
    for s_idx in range(num_strats):
        v_mask = valid_mask[s_idx]
        valid_times = final_times[s_idx, v_mask]
        
        v_count = len(valid_times)
        inv_count = num_runs - v_count
        
        if v_count < monte_carlo_parameters.minimum_valid_runs:
            dist = StrategyDistribution(
                strategy_index=s_idx, mean_race_time=float('nan'), median_race_time=float('nan'),
                standard_deviation=float('nan'), min_race_time=float('nan'), max_race_time=float('nan'),
                p10=float('nan'), p25=float('nan'), p50=float('nan'), p75=float('nan'), p90=float('nan'),
                valid_run_count=v_count, invalid_run_count=inv_count
            )
        else:
            dist = StrategyDistribution(
                strategy_index=s_idx,
                mean_race_time=float(np.mean(valid_times)),
                median_race_time=float(np.median(valid_times)),
                standard_deviation=float(np.std(valid_times)),
                min_race_time=float(np.min(valid_times)),
                max_race_time=float(np.max(valid_times)),
                p10=float(np.percentile(valid_times, 10)),
                p25=float(np.percentile(valid_times, 25)),
                p50=float(np.percentile(valid_times, 50)),
                p75=float(np.percentile(valid_times, 75)),
                p90=float(np.percentile(valid_times, 90)),
                valid_run_count=v_count,
                invalid_run_count=inv_count
            )
        distributions.append(dist)
        
    # Build Pairwise Comparisons
    pairwise_comparisons = []
    for i in range(num_strats):
        for j in range(i + 1, num_strats):
            # Only compare runs where BOTH were valid
            joint_valid = valid_mask[i] & valid_mask[j]
            if np.sum(joint_valid) < monte_carlo_parameters.minimum_valid_runs:
                continue
                
            times_i = final_times[i, joint_valid]
            times_j = final_times[j, joint_valid]
            
            deltas = times_i - times_j
            
            # If a trial is an exact tie, award 0.5 wins to each
            a_beats_b = (np.sum(deltas < 0) + 0.5 * np.sum(deltas == 0)) / len(deltas)
            b_beats_a = (np.sum(deltas > 0) + 0.5 * np.sum(deltas == 0)) / len(deltas)
            
            comp = StrategyComparison(
                strategy_a_index=i,
                strategy_b_index=j,
                mean_time_delta=float(np.mean(deltas)),
                median_time_delta=float(np.median(deltas)),
                probability_strategy_a_beats_b=float(a_beats_b),
                probability_strategy_b_beats_a=float(b_beats_a)
            )
            pairwise_comparisons.append(comp)
            
    # Baseline comparisons
    baseline_comparisons = []
    if baseline_index is not None:
        for i in range(num_strats):
            if i == baseline_index:
                continue
                
            joint_valid = valid_mask[i] & valid_mask[baseline_index]
            if np.sum(joint_valid) < monte_carlo_parameters.minimum_valid_runs:
                continue
                
            times_i = final_times[i, joint_valid]
            times_base = final_times[baseline_index, joint_valid]
            
            deltas = times_i - times_base
            
            i_beats_base = (np.sum(deltas < 0) + 0.5 * np.sum(deltas == 0)) / len(deltas)
            base_beats_i = (np.sum(deltas > 0) + 0.5 * np.sum(deltas == 0)) / len(deltas)
            
            comp = StrategyComparison(
                strategy_a_index=i,
                strategy_b_index=baseline_index,
                mean_time_delta=float(np.mean(deltas)),
                median_time_delta=float(np.median(deltas)),
                probability_strategy_a_beats_b=float(i_beats_base),
                probability_strategy_b_beats_a=float(base_beats_i)
            )
            baseline_comparisons.append(comp)
            
    return MonteCarloResult(
        session_key=race_state.session_key,
        driver_number=race_state.driver_number,
        decision_lap=race_state.decision_lap,
        random_seed=seed,
        requested_runs=num_runs,
        distributions=distributions,
        pairwise_comparisons=pairwise_comparisons,
        baseline_index=baseline_index,
        baseline_comparisons=baseline_comparisons
    )
