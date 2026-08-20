from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class CriterionTypeEnum(str, Enum):
    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"

class CriterionCategoryEnum(str, Enum):
    DEMOGRAPHIC = "demographic"
    DIAGNOSIS = "diagnosis"
    STAGE = "stage"
    LABORATORY = "laboratory"
    BIOMARKER = "biomarker"
    MEDICATION = "medication"
    PRIOR_TREATMENT = "prior_treatment"
    COMORBIDITY = "comorbidity"
    TEMPORAL = "temporal"
    PROCEDURAL = "procedural"
    ADMINISTRATIVE = "administrative"

class CriterionOperatorEnum(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    BETWEEN = "between"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    EXISTS = "exists"
    ABSENT = "absent"

class ApprovalStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class StructuredCriterion(BaseModel):
    id: Optional[str] = None
    trial_id: str
    criterion_type: CriterionTypeEnum
    category: CriterionCategoryEnum
    operator: CriterionOperatorEnum
    value_primary: Optional[str] = None
    value_secondary: Optional[str] = None
    unit: Optional[str] = None
    temporal_window: Optional[str] = None
    is_negated: bool = False
    logic_group: str = "AND"
    raw_text: str
    page_number: int = 1
    start_char: int = 0
    end_char: int = 0
    classification_confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    approval_status: ApprovalStatusEnum = ApprovalStatusEnum.PENDING
    version: int = 1

class CriterionCreateRequest(BaseModel):
    trial_id: str
    criterion_type: CriterionTypeEnum
    category: CriterionCategoryEnum
    operator: CriterionOperatorEnum
    value_primary: Optional[str] = None
    value_secondary: Optional[str] = None
    unit: Optional[str] = None
    temporal_window: Optional[str] = None
    is_negated: bool = False
    logic_group: str = "AND"
    raw_text: str

class CriterionUpdateRequest(BaseModel):
    category: Optional[CriterionCategoryEnum] = None
    operator: Optional[CriterionOperatorEnum] = None
    value_primary: Optional[str] = None
    value_secondary: Optional[str] = None
    unit: Optional[str] = None
    temporal_window: Optional[str] = None
    is_negated: Optional[bool] = None
    logic_group: Optional[str] = None
    raw_text: Optional[str] = None
    change_summary: Optional[str] = "Manual update by clinical research coordinator"

class CriterionApprovalRequest(BaseModel):
    status: ApprovalStatusEnum
    reason: Optional[str] = None
