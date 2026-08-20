from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TemporalRuleTypeEnum(str, Enum):
    WITHIN_LAST_N_DAYS = "within_last_n_days"
    BEFORE_ENROLLMENT = "before_enrollment"
    AFTER_DIAGNOSIS = "after_diagnosis"
    CURRENT_MEDICATION = "current_medication"
    HISTORICAL_CONDITION = "historical_condition"
    PRIOR_TREATMENT_LINE_COUNT = "prior_treatment_line_count"
    RECENT_LAB = "recent_lab"
    FUTURE_VISIT_WINDOW = "future_visit_window"

class DateQualityStatusEnum(str, Enum):
    VALID = "valid"
    AMBIGUOUS = "ambiguous"
    MISSING = "missing"
    FUTURE_DATE_INVALID = "future_date_invalid"
    CONFLICTING = "conflicting"

class TemporalValidationResult(BaseModel):
    is_valid: bool
    rule_type: TemporalRuleTypeEnum
    event_date: Optional[str] = None
    reference_date: Optional[str] = None
    days_difference: Optional[int] = None
    date_quality: DateQualityStatusEnum
    is_stale: bool = False
    temporal_explanation: str
    requires_human_review: bool = False

class TimelineEvent(BaseModel):
    event_id: str
    patient_id: str
    trial_id: str
    criterion_id: str
    timestamp: str
    old_status: str
    new_status: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    trigger_reason: str

class PatientEligibilityTimeline(BaseModel):
    patient_id: str
    trial_id: str
    events: List[TimelineEvent] = Field(default_factory=list)

class TemporalValidationRequest(BaseModel):
    rule_type: TemporalRuleTypeEnum
    event_date: Optional[str] = None
    reference_date: Optional[str] = "2026-08-15"
    window_days: Optional[int] = 30
    timezone_offset_hours: Optional[float] = 0.0
