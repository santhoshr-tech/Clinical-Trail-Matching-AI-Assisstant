from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class DisagreementCategoryEnum(str, Enum):
    EXTRACTION_ERROR = "extraction_error"
    NORMALIZATION_ERROR = "normalization_error"
    NEGATION_ERROR = "negation_error"
    TEMPORAL_ERROR = "temporal_error"
    MISSING_DATA_ERROR = "missing_data_error"
    CONFLICT_ERROR = "conflict_error"
    EVIDENCE_ERROR = "evidence_error"
    RULE_ERROR = "rule_error"
    REVIEWER_ERROR = "reviewer_error"
    OTHER = "other"

class ReviewerFeedbackSubmission(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    patient_id: str
    trial_id: str
    criterion_id: str
    ai_decision: str
    human_decision: str
    disagreement_category: Optional[DisagreementCategoryEnum] = None
    override_reason: Optional[str] = None
    reviewer_id: str = "dr_investigator@clinicaltrial.ai"
    model_version: str = "gemini-1.5-pro-v1"
    prompt_version: str = "v2.1"

class FeedbackRecord(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    feedback_id: str
    patient_id: str
    trial_id: str
    criterion_id: str
    ai_decision: str
    human_decision: str
    agreement_status: str  # "AGREE", "DISAGREE"
    error_type: str        # "false_pass", "false_fail", "none"
    disagreement_category: Optional[str] = None
    override_reason: Optional[str] = None
    reviewer_id: str
    model_version: str
    prompt_version: str
    created_at: str

class DisagreementAnalytics(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    total_evaluations: int
    agree_count: int
    disagree_count: int
    agreement_rate: float
    disagreement_rate: float
    false_pass_count: int
    false_fail_count: int
    category_breakdown: Dict[str, int] = Field(default_factory=dict)
    model_version_comparison: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    most_disputed_criteria: List[Dict[str, Any]] = Field(default_factory=list)
