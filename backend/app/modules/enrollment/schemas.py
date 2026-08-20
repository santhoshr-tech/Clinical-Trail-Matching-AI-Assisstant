from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class TrialScreeningRequest(BaseModel):
    patient_id: str
    trial_id: str

class TrialScreeningResponse(BaseModel):
    patient_id: str
    trial_id: str
    trial_title: str
    overall_status: str
    match_score: float
    is_eligible: bool
    message: str

class ConfirmEnrollmentRequest(BaseModel):
    patient_id: str
    trial_id: str
    baseline_report_id: Optional[str] = None
    baseline_metric_value: Optional[float] = None

class TrialEnrollment(BaseModel):
    enrollment_id: str
    patient_id: str
    trial_id: str
    status: str
    enrolled_date: str
    baseline_report_id: Optional[str] = None
    baseline_metric_value: Optional[float] = None
    current_metric_value: Optional[float] = None
    next_expected_report_date: str
    missed_week: bool = False
    missed_since_date: Optional[str] = None
    discontinued_reason: Optional[str] = None
    created_at: str

class ProgressReportUploadRequest(BaseModel):
    enrollment_id: str
    report_id: Optional[str] = None
    key_metric_name: Optional[str] = None
    key_metric_value: float
    notes: Optional[str] = None

class DiscontinueEnrollmentRequest(BaseModel):
    enrollment_id: str
    reason: Optional[str] = "no_improvement_after_N_weeks"

class CohortPatientSummary(BaseModel):
    enrollment_id: str
    patient_id: str
    mrn_synthetic: str
    age: int
    gender: str
    primary_diagnosis: str
    status: str
    enrolled_date: str
    week_number: int
    key_metric_name: str
    baseline_metric_value: Optional[float] = None
    current_metric_value: Optional[float] = None
    is_improving: bool
    consecutive_non_improving_weeks: int
    missed_week: bool
    next_expected_report_date: str
    history: List[Dict[str, Any]]
