import time
import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime, timezone
import json
import hashlib
import uuid
import os
import threading
import queue

from analytics.live.events import RaceEvent
from analytics.live.state import CanonicalRaceState
from analytics.live.bridge import FeatureUpdateBridge
from analytics.live.decision import StrategyDecisionEvent
from analytics.live.processor import process_event
from analytics.simulation.models import SimulationParameters, CalibrationProfile, RaceStateAtDecision
from analytics.simulation.montecarlo import compare_strategies, MonteCarloParameters
from analytics.simulation.decision import evaluate_decision, DecisionObjective, RiskPreferences, DecisionConstraints

logger = logging.getLogger(__name__)

class CandidateGenerator:
    """
    Deterministic candidate generation policy for live mode.
    Considers basic strategies to limit search space.
    """
    def __init__(self, allowed_compounds: List[str] = ["HARD", "MEDIUM", "SOFT"]):
        self.allowed_compounds = allowed_compounds
        
    def generate(self, current_lap: int, max_laps: int) -> List[List[Tuple[int, str]]]:
        # Minimal set: Stay out, Pit next lap, Pit in 2 laps, Pit in 3 laps
        # Returning lists of (pit_lap, compound) 
        # Since this is live, we only plan the next stop
        candidates = [[]] # Stay out
        if current_lap < max_laps - 1:
            for c in self.allowed_compounds:
                candidates.append([(current_lap + 1, c)])
                if current_lap < max_laps - 2:
                    candidates.append([(current_lap + 2, c)])
                if current_lap < max_laps - 3:
                    candidates.append([(current_lap + 3, c)])
        return candidates

class AsyncDecisionWriter:
    def __init__(self, db_connection, max_retries: int = 3, queue_size: int = 1000):
        self.db = db_connection
        self.q = queue.Queue(maxsize=queue_size)
        self.max_retries = max_retries
        self._stop_event = threading.Event()
        self.thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        self.thread.join(timeout=2.0)

    def enqueue(self, doc: dict):
        try:
            self.q.put_nowait(doc)
        except queue.Full:
            logger.error("AsyncDecisionWriter queue is full. Dropping persistence event to prevent memory growth.")

    def _writer_loop(self):
        while not self._stop_event.is_set() or not self.q.empty():
            try:
                # Wait for an item, but wake up periodically to check stop event
                doc = self.q.get(timeout=0.5)
            except queue.Empty:
                continue

            success = False
            for attempt in range(self.max_retries):
                try:
                    self.db.get_collection("live_decisions").insert_one(doc)
                    success = True
                    break
                except Exception as e:
                    logger.warning(f"Failed to persist decision (attempt {attempt + 1}/{self.max_retries}): {e}")
                    time.sleep(1.0) # wait before retry

            if not success:
                logger.error(f"Permanently dropped decision {doc.get('decision_id')} after {self.max_retries} failed persistence attempts.")
            
            self.q.task_done()

class LiveDecisionEngine:
    def __init__(self, db_connection, model_v2_path: str):
        self.db = db_connection
        self.params = SimulationParameters()
        
        with open(model_v2_path, 'r') as f:
            profile_data = json.load(f)
            self.calibration_version = "model_v2" # Simplified for demo
            self.params.apply_calibration(CalibrationProfile(**profile_data))
            
        self.candidate_generator = CandidateGenerator()
        self.last_decision_time = 0
        self.throttle_seconds = float(os.environ.get("LIVE_DECISION_THROTTLE_SECONDS", 30))
        self.writer = AsyncDecisionWriter(db_connection)

    def __del__(self):
        if hasattr(self, 'writer'):
            self.writer.stop()

    def evaluate(self, state: CanonicalRaceState, material_change: bool, current_time: Optional[datetime] = None) -> Optional[StrategyDecisionEvent]:
        if not material_change:
            return None
            
        now = time.time()
        if now - self.last_decision_time < self.throttle_seconds:
            return None
            
        # Check staleness
        state.check_staleness(current_time=current_time)
        if state.weather.status_stale:
            # We don't generate confident decisions if weather is stale
            return StrategyDecisionEvent(
                session_key=state.session_key,
                timestamp=current_time or datetime.now(timezone.utc),
                driver_number=-1, # N/A for global hold
                decision_lap=state.current_leader_lap,
                selected_strategy="DECISION_WITHHELD",
                objective="NONE",
                decision_score=0.0,
                decision_confidence="LOW",
                explanation="STALE_WEATHER",
                calibration_version=self.calibration_version
            )
            
        self.last_decision_time = now
        
        trigger = "LAP_COMPLETION"
        if state.current_leader_lap == 0:
            trigger = "SESSION_INITIALIZATION"
        
        # Extract Phase 3 RaceStateAtDecision
        # Use top driver or a specific driver (default to leader or driver 1 for now if no leader specified)
        # Assuming we just generate a decision for the leader
        driver_number = state.driver_states.keys()
        if not driver_number:
             return None
        target_driver = list(driver_number)[0] # In a full system, you would iterate over all drivers
        for drv_num, drv_state in state.driver_states.items():
            if drv_state.position == 1:
                target_driver = drv_num
                break
                
        snapshot = FeatureUpdateBridge.extract_race_snapshot(state, target_driver, state.current_leader_lap)
        if not snapshot:
            return None
            
        rs = RaceStateAtDecision(
            session_key=state.session_key,
            driver_number=target_driver,
            decision_lap=state.current_leader_lap,
            base_lap_time=snapshot.get("lap_duration", 90.0) or 90.0,
            rolling_pace=snapshot.get("rolling_pace", 90.0) or 90.0,
            pace_trend=0.0,
            current_compound=snapshot.get("compound", "MEDIUM"),
            tyre_age=snapshot.get("tyre_age", 1),
            total_race_laps=state.race_distance or 57,
            cumulative_race_time=(snapshot.get("lap_duration") or 90.0) * state.current_leader_lap,
            current_position=snapshot.get("position") or 1,
            gap_to_leader=snapshot.get("gap_to_leader") or 0.0,
            air_temperature=snapshot.get("air_temperature") or 25.0,
            track_temperature=snapshot.get("track_temperature") or 35.0,
            safety_car_active=snapshot.get("safety_car") or False
        )
        
        # Generate Candidates
        candidates_raw = self.candidate_generator.generate(rs.decision_lap, rs.total_race_laps)
        from analytics.simulation.models import StrategyPlan
        candidate_plans = []
        for raw in candidates_raw:
            laps = [x[0] for x in raw]
            comps = [x[1] for x in raw]
            candidate_plans.append(StrategyPlan(pit_laps=laps, pit_compounds=comps))
            
        # Run Monte Carlo
        if rs.total_race_laps - rs.decision_lap <= 0:
            return StrategyDecisionEvent(
                session_key=state.session_key,
                timestamp=current_time or datetime.now(timezone.utc),
                driver_number=target_driver,
                decision_lap=state.current_leader_lap,
                selected_strategy="DECISION_WITHHELD",
                objective="NONE",
                decision_score=0.0,
                decision_confidence="LOW",
                explanation="No laps remaining to simulate.",
                calibration_version=self.calibration_version
            )
            
        mc_result = compare_strategies(
            race_state=rs,
            strategies=candidate_plans,
            simulation_parameters=self.Params if hasattr(self, 'Params') else self.params,
            monte_carlo_parameters=MonteCarloParameters(number_of_runs=100)
        )
        
        # Evaluate Decision
        result = evaluate_decision(
            candidate_strategies=candidate_plans,
            mc_result=mc_result,
            objective=DecisionObjective.MIN_EXPECTED_TIME,
            risk_preferences=RiskPreferences(),
            constraints=DecisionConstraints()
        )
        
        if result.is_abstention or result.selected_strategy is None:
            return StrategyDecisionEvent(
                session_key=state.session_key,
                timestamp=current_time or datetime.now(timezone.utc),
                driver_number=target_driver,
                decision_lap=state.current_leader_lap,
                selected_strategy="DECISION_WITHHELD",
                objective="NONE",
                decision_score=0.0,
                decision_confidence="LOW",
                explanation=result.explanation,
                calibration_version=self.calibration_version
            )
            
        selected_plan_str = "STAY_OUT"
        if result.selected_strategy.pit_laps:
            selected_plan_str = f"PIT_LAP_{result.selected_strategy.pit_laps[0]}_{result.selected_strategy.pit_compounds[0]}"
            
        summary = []
        for idx, dist in enumerate(mc_result.distributions):
            plan_str = "STAY_OUT"
            if candidate_plans[idx].pit_laps:
                plan_str = f"PIT_LAP_{candidate_plans[idx].pit_laps[0]}_{candidate_plans[idx].pit_compounds[0]}"
                
            summary.append({
                "strategy_id": f"{plan_str}_{idx}",
                "description": plan_str,
                "expected_time": dist.mean_race_time,
                "median_time": dist.median_race_time,
                "p10_time": dist.p10,
                "p90_time": dist.p90,
                "decision_score": dist.mean_race_time,
                "probability_vs_baseline": result.probability_vs_baseline if plan_str == selected_plan_str else 0.5,
                "is_valid": True,
                "constraint_status": "VALID",
                "is_selected": plan_str == selected_plan_str
            })
            
        # Determine Pit Loss Source String
        pit_loss_source = "GLOBAL"
        if state.session_key in [9110, 9126, 9133, 9157]: # Quick hack for the model parsing
             pit_loss_source = "CIRCUIT_SPECIFIC"

        return StrategyDecisionEvent(
            session_key=state.session_key,
            timestamp=current_time or datetime.now(timezone.utc),
            driver_number=target_driver,
            decision_lap=state.current_leader_lap,
            trigger=trigger,
            selected_strategy=selected_plan_str,
            objective=result.objective.value,
            decision_score=result.decision_score,
            decision_confidence=result.confidence,
            probability_selected_beats_baseline=result.probability_vs_baseline or 0.5,
            candidate_summary=summary,
            explanation=f"Model parameters are calibrated from 2023 historical data; 2026 event-specific validation is unavailable.\n{result.explanation}",
            calibration_version=self.calibration_version,
            monte_carlo_seed=42,
            state_snapshot_hash="livehash",
            decision_id=str(uuid.uuid4())
        )

    def persist_decision(self, decision: StrategyDecisionEvent, state_summary: dict):
        doc = decision.model_dump()
        doc['state_summary'] = state_summary
        if 'decision_id' not in doc or not doc['decision_id']:
            doc['decision_id'] = str(uuid.uuid4())
            
        # Non-blocking, failure-tolerant background write
        self.writer.enqueue(doc)

