from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ClinicalCategoryEnum(str, Enum):
    DIAGNOSIS = "diagnosis"
    DISEASE_STAGE = "disease_stage"
    MEDICATION = "medication"
    LAB = "lab"
    BIOMARKER = "biomarker"
    PREVIOUS_TREATMENT = "previous_treatment"
    COMORBIDITY = "comorbidity"
    ALLERGY = "allergy"

class FactReviewStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"

class ExtractedFact(BaseModel):
    id: Optional[str] = None
    patient_id: str
    document_id: Optional[str] = None
    category: ClinicalCategoryEnum
    raw_text: str
    canonical_label: str
    mapping_method: str = "snomed_loinc_rxnorm_hybrid"
    mapping_confidence: float = Field(default=0.92, ge=0.0, le=1.0)
    is_negated: bool = False
    temporal_expression: Optional[str] = None
    data_date: Optional[str] = None
    is_stale: bool = False
    numeric_value: Optional[float] = None
    raw_unit: Optional[str] = None
    normalized_unit: Optional[str] = None
    source_page: int = 1
    start_char: int = 0
    end_char: int = 0
    ai_provider: str = "mock"
    ai_model: str = "mock-v1"
    prompt_version: str = "v1.0"
    review_status: FactReviewStatusEnum = FactReviewStatusEnum.PENDING
    has_conflict: bool = False
    conflict_details: Optional[str] = None

class ExtractionPipelineResult(BaseModel):
    document_id: str
    patient_id: str
    extracted_facts: List[ExtractedFact]
    conflict_count: int = 0
    processed_at: str

class FactReviewRequest(BaseModel):
    fact_id: str
    review_status: FactReviewStatusEnum
    edited_canonical_label: Optional[str] = None
    edited_is_negated: Optional[bool] = None
    reviewer_notes: Optional[str] = None
