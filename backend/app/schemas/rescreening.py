from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ReScreeningTriggerEnum(str, Enum):
    NEW_DOCUMENT = "new_document"
    FACT_CHANGE = "fact_change"
    NEW_LAB = "new_lab"
    NEW_BIOMARKER = "new_biomarker"
    MEDICATION_CHANGE = "medication_change"
    RECRUITMENT_STATUS_CHANGE = "recruitment_status_change"
    PROTOCOL_VERSION_CHANGE = "protocol_version_change"
    CRITERION_CHANGE = "criterion_change"
    EVIDENCE_VERIFICATION = "evidence_verification"

class ReScreeningJobStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class ReScreeningJob(BaseModel):
    job_id: Optional[str] = None
    trigger_type: ReScreeningTriggerEnum
    trigger_source_id: str
    patient_id: Optional[str] = None
    trial_id: Optional[str] = None
    idempotency_key: str
    status: ReScreeningJobStatusEnum = ReScreeningJobStatusEnum.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

class ReScreeningImpactSummary(BaseModel):
    job_id: str
    patient_id: str
    trial_id: str
    old_status: str
    new_status: str
    old_score: float
    new_score: float
    changed_criteria_count: int
    requires_human_review: bool
    coordinator_notification_sent: bool

class CoordinatorNotification(BaseModel):
    notification_id: str
    job_id: str
    patient_id: str
    trial_id: str
    title: str
    message: str
    is_read: bool = False
    created_at: str
