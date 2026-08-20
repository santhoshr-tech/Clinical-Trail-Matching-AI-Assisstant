from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class EvaluationCategoryEnum(str, Enum):
    CRITERION_CLASSIFICATION = "criterion_classification"
    ELIGIBILITY_EXTRACTION = "eligibility_extraction"
    MEDICAL_NORMALIZATION = "medical_normalization"
    NEGATION_DETECTION = "negation_detection"
    TEMPORAL_VALIDATION = "temporal_validation"
    MISSING_DATA_DETECTION = "missing_data_detection"
    CONFLICT_DETECTION = "conflict_detection"
    EVIDENCE_GROUNDING = "evidence_grounding"
    OVERALL_MATCHING = "overall_matching"
    DECISION_TRACEABILITY = "decision_traceability"

class CategoryMetricResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    category: EvaluationCategoryEnum
    target_threshold_f1: float = 0.85
    measured_accuracy: float
    measured_precision: float
    measured_recall: float
    measured_f1: float
    measured_specificity: float
    evidence_correctness: float = 1.0
    traceability_completeness: float = 1.0
    status: str  # "achieved", "not_achieved", "insufficient_data"
    sample_count: int

class EvaluationReport(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    run_id: str
    dataset_version: str = "v1.0-synthetic-gold-standard"
    evaluated_at: str
    total_test_cases: int
    overall_f1: float
    category_metrics: List[CategoryMetricResult]
    reproducible_command: str = "py -m pytest backend/tests/test_phase16.py"

class DashboardMetrics(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    active_trials: int
    total_patients_screened: int
    potentially_eligible_count: int
    not_eligible_count: int
    manual_review_count: int
    evidence_pending_count: int
    conflict_cases_count: int
    rescreening_jobs_count: int
    agreement_rate: float
    common_failed_criteria: List[Dict[str, Any]] = Field(default_factory=list)
    missing_data_distribution: Dict[str, int] = Field(default_factory=dict)
    data_freshness_status: str = "VALID"
