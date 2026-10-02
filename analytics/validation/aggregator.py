import math
from typing import List, Dict

from analytics.validation.models import (
    ValidationResult,
    RaceSummary,
    OverallSummary,
    PerformanceCategory,
    CoverageStatus
)

def aggregate_race_results(session_key: int, driver_number: int, results: List[ValidationResult]) -> RaceSummary:
    valid_cases = [r for r in results if r.is_valid]
    invalid_cases = [r for r in results if not r.is_valid]
    
    abstentions = [r for r in valid_cases if r.is_abstention]
    non_abstained = [r for r in valid_cases if not r.is_abstention]
    
    abstention_reasons = {}
    for a in abstentions:
        reason = "UNKNOWN"
        if a.decision_snapshot and a.decision_snapshot.explanation:
            reason = a.decision_snapshot.explanation.split(":")[0]
        abstention_reasons[reason] = abstention_reasons.get(reason, 0) + 1
        
    expected_improvements = []
    p10_p90_cov_count = 0
    p10_p90_elig = 0
    p25_p75_cov_count = 0
    p25_p75_elig = 0
    
    signed_errors = []
    abs_errors = []
    
    selected_equals_actual_count = 0
    selected_differs_from_actual_count = 0
    unknown_strategy_count = 0
    
    for r in non_abstained:
        if r.evaluation_metrics:
            m = r.evaluation_metrics
            
            if m.actual_strategy == "UNKNOWN":
                unknown_strategy_count += 1
                
            if m.performance_category == PerformanceCategory.SELECTED_EQUALS_ACTUAL:
                selected_equals_actual_count += 1
                
                if m.p10_p90_coverage_status != CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL:
                    p10_p90_elig += 1
                    if m.p10_p90_coverage_status == CoverageStatus.COVERED:
                        p10_p90_cov_count += 1
                        
                if m.p25_p75_coverage_status != CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL:
                    p25_p75_elig += 1
                    if m.p25_p75_coverage_status == CoverageStatus.COVERED:
                        p25_p75_cov_count += 1
                        
                if m.actual_outcome_vs_model_prediction is not None:
                    signed_errors.append(m.actual_outcome_vs_model_prediction)
                if m.absolute_prediction_error is not None:
                    abs_errors.append(m.absolute_prediction_error)
                    
            elif m.performance_category == PerformanceCategory.SELECTED_DIFFERS_FROM_ACTUAL:
                selected_differs_from_actual_count += 1
                
            if m.counterfactual_expected_improvement is not None:
                expected_improvements.append(m.counterfactual_expected_improvement)

    expected_improvements.sort()
    signed_errors.sort()
    abs_errors.sort()
    
    def get_pct(lst, p):
        if not lst: return 0.0
        idx = int(len(lst) * p)
        if idx >= len(lst): idx = len(lst) - 1
        return lst[idx]
        
    mean_imp = sum(expected_improvements)/len(expected_improvements) if expected_improvements else 0.0
    median_imp = get_pct(expected_improvements, 0.5)
    
    mean_signed_err = sum(signed_errors)/len(signed_errors) if signed_errors else None
    mean_abs_err = sum(abs_errors)/len(abs_errors) if abs_errors else None
    median_abs_err = get_pct(abs_errors, 0.5) if abs_errors else None
    p10_err = get_pct(signed_errors, 0.1) if signed_errors else None
    p90_err = get_pct(signed_errors, 0.9) if signed_errors else None
    
    failure_counts = {}
    for r in valid_cases:
        for t in r.failure_tags:
            failure_counts[t.value] = failure_counts.get(t.value, 0) + 1
            
    return RaceSummary(
        session_key=session_key,
        driver_number=driver_number,
        total_cases=len(results),
        valid_cases=len(valid_cases),
        invalid_cases=len(invalid_cases),
        abstentions=len(abstentions),
        selected_equals_actual_count=selected_equals_actual_count,
        selected_differs_from_actual_count=selected_differs_from_actual_count,
        unknown_actual_strategy_count=unknown_strategy_count,
        
        mean_expected_improvement=mean_imp,
        median_expected_improvement=median_imp,
        p10_expected_improvement=get_pct(expected_improvements, 0.1),
        p25_expected_improvement=get_pct(expected_improvements, 0.25),
        p50_expected_improvement=get_pct(expected_improvements, 0.5),
        p75_expected_improvement=get_pct(expected_improvements, 0.75),
        p90_expected_improvement=get_pct(expected_improvements, 0.9),
        worst_expected_improvement=expected_improvements[0] if expected_improvements else 0.0,
        best_expected_improvement=expected_improvements[-1] if expected_improvements else 0.0,
        
        mean_signed_prediction_error=mean_signed_err,
        mean_absolute_prediction_error=mean_abs_err,
        median_absolute_prediction_error=median_abs_err,
        p10_prediction_error=p10_err,
        p90_prediction_error=p90_err,
        
        p10_p90_eligible_cases=p10_p90_elig,
        p10_p90_covered_cases=p10_p90_cov_count,
        empirical_p10_p90_coverage=(p10_p90_cov_count / p10_p90_elig) if p10_p90_elig else 0.0,
        
        p25_p75_eligible_cases=p25_p75_elig,
        p25_p75_covered_cases=p25_p75_cov_count,
        empirical_p25_p75_coverage=(p25_p75_cov_count / p25_p75_elig) if p25_p75_elig else 0.0,
        
        failure_taxonomy_counts=failure_counts,
        abstention_reasons=abstention_reasons
    )

def aggregate_overall_summary(race_summaries: List[RaceSummary]) -> OverallSummary:
    total_cases = sum(r.total_cases for r in race_summaries)
    valid_cases = sum(r.valid_cases for r in race_summaries)
    invalid_cases = sum(r.invalid_cases for r in race_summaries)
    abstentions = sum(r.abstentions for r in race_summaries)
    
    selected_equals = sum(r.selected_equals_actual_count for r in race_summaries)
    selected_differs = sum(r.selected_differs_from_actual_count for r in race_summaries)
    unknowns = sum(r.unknown_actual_strategy_count for r in race_summaries)
    
    total_non_abstained = selected_equals + selected_differs
    mean_exp_imp = sum(r.mean_expected_improvement * (r.selected_equals_actual_count + r.selected_differs_from_actual_count) for r in race_summaries) / total_non_abstained if total_non_abstained else 0.0
    
    total_p10_p90_elig = sum(r.p10_p90_eligible_cases for r in race_summaries)
    total_p10_p90_cov = sum(r.p10_p90_covered_cases for r in race_summaries)
    p10_p90_cov = total_p10_p90_cov / total_p10_p90_elig if total_p10_p90_elig else 0.0
    
    total_p25_p75_elig = sum(r.p25_p75_eligible_cases for r in race_summaries)
    total_p25_p75_cov = sum(r.p25_p75_covered_cases for r in race_summaries)
    p25_p75_cov = total_p25_p75_cov / total_p25_p75_elig if total_p25_p75_elig else 0.0
    
    return OverallSummary(
        total_cases=total_cases,
        valid_cases=valid_cases,
        invalid_cases=invalid_cases,
        abstentions=abstentions,
        selected_equals_actual_count=selected_equals,
        selected_differs_from_actual_count=selected_differs,
        unknown_actual_strategy_count=unknowns,
        mean_expected_improvement=mean_exp_imp,
        median_expected_improvement=0.0, 
        empirical_p10_p90_coverage=p10_p90_cov,
        empirical_p25_p75_coverage=p25_p75_cov,
        race_summaries=race_summaries
    )
