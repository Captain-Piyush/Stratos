import pytest
from unittest.mock import patch, MagicMock

from analytics.simulation.models import StrategyPlan, SimulationParameters, RaceStateAtDecision
from analytics.simulation.montecarlo import MonteCarloParameters
from analytics.simulation.decision import DecisionObjective, RiskPreferences, DecisionConstraints
from analytics.validation.models import ValidationCase, FailureTag, PerformanceCategory, RaceSummary, CoverageStatus, ValidationResult
from analytics.validation.evaluator import evaluate_validation_case
from analytics.validation.aggregator import aggregate_race_results, aggregate_overall_summary

class FakeCursor:
    def __init__(self, data):
        self.data = data
    def __iter__(self):
        return iter(self.data)
    def sort(self, *args, **kwargs):
        return self
    def limit(self, n):
        return self.data[-n:] if self.data else []

@pytest.fixture
def mock_db_validation():
    with patch('analytics.features.builder.db') as mock_db, \
         patch('analytics.replay.engine.db', new=mock_db):
        mock_db.db = True
        
        def _get_collection(name):
            mock_coll = MagicMock()
            data = []
            if name == "laps":
                data = [
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 91.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 3, "lap_duration": 92.0, "date_start": "2023-01-01T12:03:01+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 4, "lap_duration": 110.0, "date_start": "2023-01-01T12:04:33+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 5, "lap_duration": 90.0, "date_start": "2023-01-01T12:06:23+00:00", "is_pit_out_lap": False},
                    {"session_key": 1, "driver_number": 1, "lap_number": 10, "lap_duration": 90.0, "date_start": "2023-01-01T12:13:53+00:00", "is_pit_out_lap": False}
                ]
            elif name == "stints":
                data = [
                    {"session_key": 1, "driver_number": 1, "stint_number": 1, "lap_start": 1, "lap_end": 3, "compound": "SOFT", "tyre_age_at_start": 0},
                    {"session_key": 1, "driver_number": 1, "stint_number": 2, "lap_start": 4, "lap_end": 10, "compound": "HARD", "tyre_age_at_start": 0}
                ]
            elif name == "pit_stops":
                data = [] # Empty to force inferred pit logic test
            elif name == "race_control":
                data = []
            elif name == "positions":
                data = [
                    {"session_key": 1, "driver_number": 1, "position": 1, "date": "2023-01-01T12:01:29+00:00"}
                ]
            elif name == "intervals":
                data = []
            elif name == "weather":
                data = []
            elif name == "drivers":
                data = [{"session_key": 1, "driver_number": 1, "team_name": "RBR"}]
            
            mock_coll.find.return_value = FakeCursor(data)
            return mock_coll
            
        mock_db.get_collection.side_effect = _get_collection
        yield mock_db

def test_time_reference_normalization_and_inferred_pits(mock_db_validation):
    case = ValidationCase(
        case_id="test1",
        session_key=1,
        driver_number=1,
        decision_lap=2,
        candidate_strategies=[StrategyPlan([3], ["HARD"])],
        simulation_parameters=SimulationParameters(),
        monte_carlo_parameters=MonteCarloParameters(number_of_runs=10),
        decision_objective=DecisionObjective.MIN_EXPECTED_TIME,
        risk_preferences=RiskPreferences(),
        decision_constraints=DecisionConstraints(),
        baseline_index=0
    )
    
    result = evaluate_validation_case(case)
    m = result.evaluation_metrics
    
    assert result.historical_outcome.pit_source == "INFERRED"
    assert result.historical_outcome.strategy_source == "INFERRED"
    assert result.historical_outcome.actual_strategy == "PIT LAPS [3] -> ['HARD']"
    
    assert m.actual_race_outcome == 382.0
    
    assert m.actual_outcome_vs_model_prediction is not None
    assert m.absolute_prediction_error is not None
    assert m.p10_p90_coverage_status in [CoverageStatus.COVERED, CoverageStatus.NOT_COVERED]
    assert FailureTag.STRATEGY_DIFFERENCE not in result.failure_tags

def test_selected_differs_coverage_suppression(mock_db_validation):
    case = ValidationCase(
        case_id="test2",
        session_key=1,
        driver_number=1,
        decision_lap=2,
        candidate_strategies=[StrategyPlan([5], ["MEDIUM"])],
        simulation_parameters=SimulationParameters(),
        monte_carlo_parameters=MonteCarloParameters(number_of_runs=10),
        decision_objective=DecisionObjective.MIN_EXPECTED_TIME,
        risk_preferences=RiskPreferences(),
        decision_constraints=DecisionConstraints(),
        baseline_index=0
    )
    
    result = evaluate_validation_case(case)
    m = result.evaluation_metrics
    
    assert m.performance_category == PerformanceCategory.SELECTED_DIFFERS_FROM_ACTUAL
    assert m.actual_outcome_vs_model_prediction is None
    assert m.absolute_prediction_error is None
    assert m.p10_p90_coverage_status == CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL
    assert FailureTag.STRATEGY_DIFFERENCE in result.failure_tags

def test_missing_data_unknown_strategy():
    with patch('analytics.features.builder.db') as mock_db, \
         patch('analytics.replay.engine.db', new=mock_db):
        mock_db.db = True
        def _get_coll(n):
            c = MagicMock()
            if n == "laps":
                class CustomFakeCursor(FakeCursor):
                    def sort(self, *args, **kwargs):
                        # return a cursor with lap 57 for the max_lap query
                        if len(args) > 1 and args[1] == -1:
                            return FakeCursor([{"session_key": 1, "driver_number": 1, "lap_number": 57}])
                        return self
                c.find.return_value = CustomFakeCursor([
                    {"session_key": 1, "driver_number": 1, "lap_number": 1, "lap_duration": 90.0, "date_start": "2023-01-01T12:00:00+00:00", "is_pit_out_lap": False}, 
                    {"session_key": 1, "driver_number": 1, "lap_number": 2, "lap_duration": 91.0, "date_start": "2023-01-01T12:01:30+00:00", "is_pit_out_lap": False}
                ])
            else:
                c.find.return_value = FakeCursor([])
            return c
        mock_db.get_collection.side_effect = _get_coll

        case = ValidationCase(
            case_id="test3",
            session_key=1,
            driver_number=1,
            decision_lap=2,
            candidate_strategies=[StrategyPlan([], [])],
            simulation_parameters=SimulationParameters(),
            monte_carlo_parameters=MonteCarloParameters(number_of_runs=10),
            decision_objective=DecisionObjective.MIN_EXPECTED_TIME,
            risk_preferences=RiskPreferences(),
            decision_constraints=DecisionConstraints(),
            baseline_index=0
        )

        result = evaluate_validation_case(case)
        assert result.evaluation_metrics.actual_strategy == "UNKNOWN"
        assert result.evaluation_metrics.actual_pit_source == "UNKNOWN"

def test_strategy_id_traceability(mock_db_validation):
    case = ValidationCase(
        case_id="test4",
        session_key=1,
        driver_number=1,
        decision_lap=2,
        candidate_strategies=[StrategyPlan([], [])],
        simulation_parameters=SimulationParameters(),
        monte_carlo_parameters=MonteCarloParameters(number_of_runs=10),
        decision_objective=DecisionObjective.MIN_EXPECTED_TIME,
        risk_preferences=RiskPreferences(),
        decision_constraints=DecisionConstraints(),
        baseline_index=0
    )
    
    with patch('analytics.validation.evaluator.evaluate_historical_decision') as mock_eval:
        from analytics.replay.models import DecisionSnapshot
        mock_eval.return_value = DecisionSnapshot(
            decision_time=None,
            selected_strategy=StrategyPlan([99], ["SOFT"]),
            candidate_strategies=case.candidate_strategies,
            decision_objective=DecisionObjective.MIN_EXPECTED_TIME,
            decision_score=0,
            confidence="HIGH",
            explanation="",
            monte_carlo_summary=[],
            model_version="",
            probability_vs_baseline=0.0
        )
        with pytest.raises(RuntimeError, match="not found in candidate strategies"):
            evaluate_validation_case(case)

def test_validation_aggregator():
    from analytics.validation.models import ValidationMetrics
    from analytics.replay.models import DecisionSnapshot, HistoricalOutcome
    
    m1 = ValidationResult(
        case_id="1", session_key=1, driver_number=1, decision_lap=1, is_valid=True, is_abstention=False,
        failure_tags=[], decision_snapshot=None, historical_outcome=None,
        evaluation_metrics=ValidationMetrics(
            performance_category=PerformanceCategory.SELECTED_EQUALS_ACTUAL,
            selected_strategy_index=0, baseline_strategy_index=0,
            expected_time_selected=0.0, expected_time_baseline=0.0, counterfactual_expected_improvement=2.0,
            probability_selected_beats_baseline=0.0, risk_selected=0.0, risk_baseline=0.0,
            actual_strategy="STAY OUT", actual_strategy_source="DIRECT", actual_pit_source="DIRECT",
            actual_race_outcome=0.0, actual_outcome_vs_model_prediction=-5.0, absolute_prediction_error=5.0,
            p10_p90_coverage_status=CoverageStatus.COVERED, p25_p75_coverage_status=CoverageStatus.NOT_COVERED
        )
    )
    m2 = ValidationResult(
        case_id="2", session_key=1, driver_number=1, decision_lap=2, is_valid=True, is_abstention=False,
        failure_tags=[], decision_snapshot=None, historical_outcome=None,
        evaluation_metrics=ValidationMetrics(
            performance_category=PerformanceCategory.SELECTED_DIFFERS_FROM_ACTUAL,
            selected_strategy_index=0, baseline_strategy_index=0,
            expected_time_selected=0.0, expected_time_baseline=0.0, counterfactual_expected_improvement=4.0,
            probability_selected_beats_baseline=0.0, risk_selected=0.0, risk_baseline=0.0,
            actual_strategy="UNKNOWN", actual_strategy_source="UNKNOWN", actual_pit_source="UNKNOWN",
            actual_race_outcome=None, actual_outcome_vs_model_prediction=None, absolute_prediction_error=None,
            p10_p90_coverage_status=CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL, p25_p75_coverage_status=CoverageStatus.NOT_OBSERVABLE_COUNTERFACTUAL
        )
    )
    
    summary = aggregate_race_results(1, 1, [m1, m2])
    assert summary.selected_equals_actual_count == 1
    assert summary.selected_differs_from_actual_count == 1
    assert summary.unknown_actual_strategy_count == 1
    
    assert summary.mean_signed_prediction_error == -5.0
    assert summary.mean_absolute_prediction_error == 5.0
    
    assert summary.p10_p90_eligible_cases == 1
    assert summary.p10_p90_covered_cases == 1
    assert summary.empirical_p10_p90_coverage == 1.0
    
    assert summary.p25_p75_covered_cases == 0
    assert summary.empirical_p25_p75_coverage == 0.0

def test_multi_race_aggregation():
    s1 = RaceSummary(
        session_key=1, driver_number=1, total_cases=2, valid_cases=2, invalid_cases=0, abstentions=0,
        selected_equals_actual_count=1, selected_differs_from_actual_count=1, unknown_actual_strategy_count=0,
        mean_expected_improvement=1.0, median_expected_improvement=1.0,
        p10_expected_improvement=1.0, p25_expected_improvement=1.0, p50_expected_improvement=1.0,
        p75_expected_improvement=1.0, p90_expected_improvement=1.0, worst_expected_improvement=1.0, best_expected_improvement=1.0,
        mean_signed_prediction_error=1.0, mean_absolute_prediction_error=1.0, median_absolute_prediction_error=1.0,
        p10_prediction_error=1.0, p90_prediction_error=1.0,
        p10_p90_eligible_cases=1, p10_p90_covered_cases=1, empirical_p10_p90_coverage=1.0,
        p25_p75_eligible_cases=1, p25_p75_covered_cases=1, empirical_p25_p75_coverage=1.0,
        failure_taxonomy_counts={}, abstention_reasons={}
    )
    s2 = RaceSummary(
        session_key=2, driver_number=1, total_cases=2, valid_cases=2, invalid_cases=0, abstentions=0,
        selected_equals_actual_count=1, selected_differs_from_actual_count=1, unknown_actual_strategy_count=0,
        mean_expected_improvement=3.0, median_expected_improvement=3.0,
        p10_expected_improvement=3.0, p25_expected_improvement=3.0, p50_expected_improvement=3.0,
        p75_expected_improvement=3.0, p90_expected_improvement=3.0, worst_expected_improvement=3.0, best_expected_improvement=3.0,
        mean_signed_prediction_error=3.0, mean_absolute_prediction_error=3.0, median_absolute_prediction_error=3.0,
        p10_prediction_error=3.0, p90_prediction_error=3.0,
        p10_p90_eligible_cases=3, p10_p90_covered_cases=0, empirical_p10_p90_coverage=0.0,
        p25_p75_eligible_cases=1, p25_p75_covered_cases=0, empirical_p25_p75_coverage=0.0,
        failure_taxonomy_counts={}, abstention_reasons={}
    )
    overall = aggregate_overall_summary([s1, s2])
    
    assert overall.mean_expected_improvement == 2.0
    assert overall.empirical_p10_p90_coverage == 0.25
    assert overall.empirical_p25_p75_coverage == 0.5
