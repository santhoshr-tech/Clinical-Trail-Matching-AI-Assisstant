from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class EvidenceVerificationStatusEnum(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    UNCLEAR = "unclear"

class EvidenceItem(BaseModel):
    document_id: Optional[str] = None
    file_name: Optional[str] = None
    document_category: Optional[str] = "clinical_document"
    page_number: Optional[int] = 1
    start_char: Optional[int] = 0
    end_char: Optional[int] = 0
    data_date: Optional[str] = None
    raw_value: str
    normalized_value: str
    extraction_method: str = "pymupdf_text_extraction"
    extraction_confidence: float = 1.0
    verification_status: EvidenceVerificationStatusEnum = EvidenceVerificationStatusEnum.VERIFIED

class EvidenceReliabilityBreakdown(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    source_type_factor: float
    recency_factor: float
    verification_factor: float
    confidence_factor: float
    conflict_factor: float
    completeness_factor: float

class DecisionTraceObject(BaseModel):
    trace_id: str
    match_id: str
    criterion_id: str
    criterion_version: int = 1
    trial_id: str
    trial_version: int = 1
    patient_id: str
    patient_snapshot_id: str
    status: str  # PASS, FAIL, UNKNOWN, CONFLICT
    patient_value: Optional[str] = None
    expected_value: Optional[str] = None
    rule_used: str
    facts_used: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    reliability_score: float = Field(..., ge=0.0, le=1.0)
    reliability_breakdown: EvidenceReliabilityBreakdown
    ai_provider: str = "mock"
    ai_model: str = "mock-v1"
    prompt_version: str = "v1.0"
    matching_engine_version: str = "v1.0.0-deterministic"
    human_review: Optional[Dict[str, Any]] = None
    override_reason: Optional[str] = None
    decision_timestamp: str
    completeness_score: float = 1.0  # Target 1.0 (100%)

class EvidenceVerificationRequest(BaseModel):
    evidence_id: str
    verification_status: EvidenceVerificationStatusEnum
    reviewer_notes: Optional[str] = None
