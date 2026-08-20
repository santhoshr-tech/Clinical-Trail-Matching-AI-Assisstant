from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class CriterionMatchStatusEnum(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"

class EvidenceReliabilityEnum(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    STALE = "stale"
    CONFLICTING = "conflicting"

class OverallEligibilityStatusEnum(str, Enum):
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    POTENTIALLY_ELIGIBLE = "POTENTIALLY_ELIGIBLE"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    ELIGIBLE_FOR_REVIEW = "ELIGIBLE_FOR_REVIEW"
    INVESTIGATOR_REVIEW_REQUIRED = "INVESTIGATOR_REVIEW_REQUIRED"

class CriterionMatchResult(BaseModel):
    criterion_id: str
    criterion_type: str  # inclusion / exclusion
    category: str
    operator: str
    raw_text: str
    status: CriterionMatchStatusEnum
    patient_value: Optional[str] = None
    expected_value: Optional[str] = None
    rule_used: str
    source_evidence: Optional[str] = None
    evidence_reliability: EvidenceReliabilityEnum
    data_date: Optional[str] = None
    decision_timestamp: str
    criterion_version: int = 1
    engine_version: str = "v1.0.0-deterministic"

class TrialMatchResult(BaseModel):
    patient_id: str
    trial_id: str
    overall_status: OverallEligibilityStatusEnum
    match_score: float  # Transparent percentage of criteria passed (0.0 to 100.0)
    total_criteria: int
    passed_count: int
    failed_count: int
    unknown_count: int
    conflict_count: int
    evaluated_at: str
    engine_version: str = "v1.0.0-deterministic"
    criterion_results: List[CriterionMatchResult]

class MatchEvaluationRequest(BaseModel):
    patient_id: str
    trial_id: str
