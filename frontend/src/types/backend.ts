export interface CandidateSummary {
    strategy_id: string;
    description: string;
    expected_time: number | null;
    median_time: number | null;
    p10_time: number | null;
    p90_time: number | null;
    decision_score: number | null;
    probability_vs_baseline: number | null;
    is_valid: boolean;
    constraint_status: string;
    is_selected: boolean;
}

export interface StrategyDecisionEvent {
    session_key: number;
    timestamp: string;
    driver_number: number;
    decision_lap: number;
    trigger: string;
    selected_strategy: string;
    objective: string;
    decision_score: number;
    decision_confidence: "HIGH" | "MEDIUM" | "LOW";
    probability_selected_beats_baseline: number | null;
    candidate_summary: CandidateSummary[];
    explanation: string;
    software_version: string;
    simulation_version: string;
    decision_version: string;
    calibration_version: string;
    monte_carlo_seed: number;
    state_snapshot_hash: string;
    decision_id: string;
}

export interface DriverState {
    driver_number: number;
    current_lap: number;
    position: number | null;
    gap_to_leader: number | null;
    interval_to_ahead: number | null;
    current_compound: string;
    tyre_age: number;
    stints: number;
    last_lap_time: number | null;
    is_in_pit: boolean;
    is_retired: boolean;
    last_update: string;
    lap_history: number[];
    status_stale: boolean;
}

export interface WeatherState {
    air_temperature: number | null;
    track_temperature: number | null;
    rainfall: boolean | null;
    last_update: string | null;
    status_stale: boolean;
}

export interface CanonicalRaceState {
    session_key: number;
    race_distance: number | null;
    global_status: string;
    current_leader_lap: number;
    driver_states: Record<number, DriverState>;
    weather: WeatherState;
    last_event_timestamp: string | null;
    stale_threshold_seconds: number;
}

export interface CalibrationProfile {
    degradation_slopes: Record<string, number>;
    base_lap_times: Record<string, number>;
    fuel_effect: number;
    pit_loss: number;
    // other fields as needed
}

export interface HistoricalOutcome {
    actual_strategy: string;
    pit_source: string;
    strategy_source: string;
    actual_pit_laps: number[];
    actual_compounds: string[];
    actual_finish_position: number | null;
    actual_race_time: number | null;
    actual_outcome_from_decision_point: number | null;
    outcome_status: string;
    retirement_lap: number | null;
    retirement_reason: string | null;
}
