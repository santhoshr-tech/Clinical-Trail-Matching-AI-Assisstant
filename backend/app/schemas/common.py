from enum import Enum
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class UserRole(str, Enum):
    ADMIN = "admin"
    RESEARCH_COORDINATOR = "research_coordinator"
    INVESTIGATOR = "investigator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    PATIENT = "patient"

class CriterionDecisionState(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"

class ScreeningState(str, Enum):
    ELIGIBLE_FOR_REVIEW = "eligible_for_review"
    POTENTIALLY_ELIGIBLE = "potentially_eligible"
    NOT_ELIGIBLE = "not_eligible"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    EXPIRED_MATCH = "expired_match"

class ProviderStatusState(str, Enum):
    CONFIGURED = "configured"
    MISSING = "missing"
    INVALID = "invalid"

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ProviderHealthStatus(BaseModel):
    aiProvider: str
    status: ProviderStatusState
    geminiStatus: ProviderStatusState
    ollamaStatus: ProviderStatusState
    clinicalTrialsApiStatus: ProviderStatusState
