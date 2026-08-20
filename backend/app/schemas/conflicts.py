from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class ConflictResolutionChoiceEnum(str, Enum):
    ACCEPT_A = "accept_a"
    ACCEPT_B = "accept_b"
    MARK_UNRESOLVED = "mark_unresolved"
    CUSTOM_CORRECTION = "custom_correction"

class ConflictCategoryEnum(str, Enum):
    BIOMARKER = "biomarker"
    LAB = "lab"
    DIAGNOSIS_STAGE = "diagnosis_stage"
    MEDICATION = "medication"

class SourceFactDetail(BaseModel):
    fact_id: str
    document_id: Optional[str] = None
    file_name: str
    document_date: str
    reliability_score: float = Field(default=0.9, ge=0.0, le=1.0)
    raw_value: str
    normalized_value: str
    is_negated: bool = False

class ClinicalConflictCase(BaseModel):
    conflict_id: str
    patient_id: str
    category: ConflictCategoryEnum
    description: str
    source_a: SourceFactDetail
    source_b: SourceFactDetail
    status: str = "unresolved"
    resolution_reason: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None

class ConflictResolutionRequest(BaseModel):
    conflict_id: str
    resolution_choice: ConflictResolutionChoiceEnum
    custom_corrected_value: Optional[str] = None
    resolution_reason: str = Field(..., min_length=5, description="Mandatory rationale for clinical evidence resolution.")

class ConflictAnalytics(BaseModel):
    total_conflicts: int
    unresolved_count: int
    resolved_count: int
    category_breakdown: Dict[str, int]
    average_resolution_time_hours: float = 0.0
