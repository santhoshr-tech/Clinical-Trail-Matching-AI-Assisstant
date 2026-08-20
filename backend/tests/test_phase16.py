import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db
from app.modules.evaluation.service import (
    seed_gold_standard_benchmark_dataset,
    run_measured_evaluation_suite,
    get_researcher_dashboard_metrics
)
from app.schemas.evaluation import EvaluationCategoryEnum

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_phase16_test_data():
    """Setup test database and seed benchmark cases."""
    init_db()
    seed_gold_standard_benchmark_dataset()


def test_1_seed_gold_standard_dataset():
    """Verify gold standard dataset is seeded into database."""
    report = run_measured_evaluation_suite()
    assert report.total_test_cases >= 30
    assert report.dataset_version == "v1.0-synthetic-gold-standard"


def test_2_evaluation_across_10_target_categories():
    """Verify evaluation suite measures performance across all 10 target categories."""
    report = run_measured_evaluation_suite()
    categories = [m.category.value for m in report.category_metrics]
    
    expected_categories = [
        "criterion_classification",
        "eligibility_extraction",
        "medical_normalization",
        "negation_detection",
        "temporal_validation",
        "missing_data_detection",
        "conflict_detection",
        "evidence_grounding",
        "overall_matching",
        "decision_traceability"
    ]

    for expected in expected_categories:
        assert expected in categories


def test_3_measured_metrics_calculation():
    """Verify Accuracy, Precision, Recall, F1, Specificity score calculations."""
    report = run_measured_evaluation_suite()
    for metric in report.category_metrics:
        assert 0.0 <= metric.measured_accuracy <= 1.0
        assert 0.0 <= metric.measured_precision <= 1.0
        assert 0.0 <= metric.measured_recall <= 1.0
        assert 0.0 <= metric.measured_f1 <= 1.0
        assert 0.0 <= metric.measured_specificity <= 1.0
        assert metric.status in ["achieved", "not_achieved", "insufficient_data"]


def test_4_strict_target_achieved_classification_rule():
    """Verify status is NEVER marked 'achieved' unless measured F1 >= target_threshold_f1."""
    report = run_measured_evaluation_suite()
    for metric in report.category_metrics:
        if metric.status == "achieved":
            assert metric.measured_f1 >= metric.target_threshold_f1
        elif metric.status == "not_achieved":
            assert metric.measured_f1 < metric.target_threshold_f1


def test_5_researcher_dashboard_metrics_aggregation():
    """Verify researcher dashboard operational metrics retrieval."""
    metrics = get_researcher_dashboard_metrics()
    assert metrics.active_trials >= 1
    assert metrics.total_patients_screened >= 1
    assert metrics.agreement_rate >= 0.0
    assert isinstance(metrics.common_failed_criteria, list)
    assert isinstance(metrics.missing_data_distribution, dict)


def test_6_reproducible_command_presence():
    """Verify evaluation report contains reproducible evaluation CLI command."""
    report = run_measured_evaluation_suite()
    assert "py -m pytest" in report.reproducible_command
