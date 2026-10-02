import math
from typing import List

from analytics.replay.engine import (
    create_replay_snapshot,
    evaluate_historical_decision,
    extract_historical_outcome
)
from analytics.validation.models import (
    ValidationCase,
    ValidationResult,
    ValidationMetrics,
    FailureTag,
    PerformanceCategory,
    CoverageStatus
)
from analytics.simulation.decision import get_percentile

def evaluate_validation_case(case: ValidationCase) -> ValidationResult:
    try:
        snapshot = create_replay_snapshot(case.session_key, case.driver_number, case.decision_lap)
    except Exception as e:
        print(f"Exception creating snapshot: {e}")
        return ValidationResult(
            case_id=case.case_id,
            session_key=case.session_key,
            driver_number=case.driver_number,
            decision_lap=case.decision_lap,
            is_valid=False,
            is_abstention=False,
            decision_snapshot=None,
            historical_outcome=None,
            evaluation_metrics=None,
            failure_tags=[FailureTag.INSUFFICIENT_DATA]
        )

    decision = evaluate_historical_decision(
        snapshot=snapshot,
        candidate_strategies=case.candidate_strategies,
        sim_params=case.simulation_parameters,
        mc_params=case.monte_carlo_parameters,
        objective=case.decision_objective,
        risk=case.risk_preferences,
        constraints=case.decision_constraints,
        baseline_index=case.baseline_index
    )

    is_abstention = (decision.selected_strategy is None)

    selected_idx = None
    if not is_abstention:
        for idx, plan in enumerate(case.candidate_strategies):
            if plan.pit_laps == decision.selected_strategy.pit_laps and plan.pit_compounds == decision.selected_strategy.pit_compounds:
                selected_idx = idx
                break
        if selected_idx is None:
            raise RuntimeError(f"Invariant broken: Selected strategy {decision.selected_strategy} not found in candidate strategies.")

    outcome = extract_historical_outcome(case.session_key, case.driver_number, case.decision_lap)
    
    metrics = None
    tags = []
    
    actual_strategy_str = outcome.actual_strategy
    actual_matches_selected = False
    
    if not is_abstention and decision.selected_strategy:
        if outcome.actual_pit_laps == decision.selected_strategy.pit_laps and outcome.actual_compounds == decision.selected_strategy.pit_compounds:
            actual_matches_selected = True

    if is_abstention:
        perf_cat = PerformanceCategory.ABSTAINED
    elif actual_matches_selected:
        perf_cat = PerformanceCategory.SELECTED_EQUALS_ACTUAL
    else:
        perf_cat = PerformanceCategory.SELECTED_DIFFERS_FROM_ACTUAL

    if outcome.actual_outcome_from_decision_point is not None:
        expected_time_selected = None
        expected_time_baseline = None
        counterfactual_improvement = None
        prob_vs_base = None
        risk_selected = None
        risk_baseline = None
        
        cum_time = snapshot.race_state_at_decision.cumulative_race_time
        
        if not is_abstention:
            selected_dist = decision.monte_carlo_summary[selected_idx]
            expected_time_selected = selected_dist.mean_race_time - cum_time
            risk_selected = get_percentile(selected_dist, case.risk_preferences.downside_percentile) - cum_time
            
            if case.baseline_index is not None and case.baseline_index < len(decision.monte_carlo_summary):
                baseline_dist = decision.monte_carlo_summary[case.baseline_index]
                expected_time_baseline = baseline_dist.mean_race_time - cum_time
                risk_baseline = get_percentile(baseline_dist, case.risk_preferences.downside_percentile) - cum_time
                counterfactual_improvement = expected_time_baseline - expected_time_selected
                
                prob_vs_base = decision.probability_vs_baseline
                
        actual_vs_expected_time_diff = None
        abs_error = None
        p10_p90_cov = CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL
        p25_p75_cov = CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL
        
        if outcome.outcome_status.value != "FINISHED":
            perf_cat = PerformanceCategory.OUTCOME_NOT_COMPARABLE
            p10_p90_cov = CoverageStatus.NOT_OBSERVABLE
            p25_p75_cov = CoverageStatus.NOT_OBSERVABLE
        elif perf_cat == PerformanceCategory.SELECTED_EQUALS_ACTUAL:
            actual_vs_expected_time_diff = outcome.actual_outcome_from_decision_point - expected_time_selected
            abs_error = abs(actual_vs_expected_time_diff)
            
            # Predict bounds as remaining time
            p10_rem = selected_dist.p10 - cum_time
            p90_rem = selected_dist.p90 - cum_time
            p25_rem = selected_dist.p25 - cum_time
            p75_rem = selected_dist.p75 - cum_time
            
            if p10_rem <= outcome.actual_outcome_from_decision_point <= p90_rem:
                p10_p90_cov = CoverageStatus.COVERED
            else:
                p10_p90_cov = CoverageStatus.NOT_COVERED
                
            if p25_rem <= outcome.actual_outcome_from_decision_point <= p75_rem:
                p25_p75_cov = CoverageStatus.COVERED
            else:
                p25_p75_cov = CoverageStatus.NOT_COVERED
                
            if abs_error > 10.0:
                tags.append(FailureTag.MODEL_UNCERTAINTY)
        else:
            if not is_abstention:
                tags.append(FailureTag.STRATEGY_DIFFERENCE)
                tags.append(FailureTag.COUNTERFACTUAL_UNOBSERVED)

        metrics = ValidationMetrics(
            performance_category=perf_cat,
            selected_strategy_index=selected_idx,
            baseline_strategy_index=case.baseline_index,
            expected_time_selected=expected_time_selected,
            expected_time_baseline=expected_time_baseline,
            counterfactual_expected_improvement=counterfactual_improvement,
            probability_selected_beats_baseline=prob_vs_base,
            risk_selected=risk_selected,
            risk_baseline=risk_baseline,
            actual_strategy=actual_strategy_str,
            actual_strategy_source=outcome.strategy_source,
            actual_pit_source=outcome.pit_source,
            actual_race_outcome=outcome.actual_outcome_from_decision_point,
            outcome_status=outcome.outcome_status.value,
            retirement_lap=outcome.retirement_lap,
            retirement_reason=outcome.retirement_reason,
            actual_outcome_vs_model_prediction=actual_vs_expected_time_diff,
            absolute_prediction_error=abs_error,
            p10_p90_coverage_status=p10_p90_cov,
            p25_p75_coverage_status=p25_p75_cov
        )
    else:
        metrics = ValidationMetrics(
            performance_category=perf_cat,
            selected_strategy_index=selected_idx,
            baseline_strategy_index=case.baseline_index,
            expected_time_selected=None,
            expected_time_baseline=None,
            counterfactual_expected_improvement=None,
            probability_selected_beats_baseline=None,
            risk_selected=None,
            risk_baseline=None,
            actual_strategy=actual_strategy_str,
            actual_strategy_source=outcome.strategy_source,
            actual_pit_source=outcome.pit_source,
            actual_race_outcome=None,
            outcome_status=outcome.outcome_status.value,
            retirement_lap=outcome.retirement_lap,
            retirement_reason=outcome.retirement_reason,
            actual_outcome_vs_model_prediction=None,
            absolute_prediction_error=None,
            p10_p90_coverage_status=CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL,
            p25_p75_coverage_status=CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL
        )

    return ValidationResult(
        case_id=case.case_id,
        session_key=case.session_key,
        driver_number=case.driver_number,
        decision_lap=case.decision_lap,
        is_valid=True,
        is_abstention=is_abstention,
        decision_snapshot=decision,
        historical_outcome=outcome,
        evaluation_metrics=metrics,
        failure_tags=tags if tags else []
    )
