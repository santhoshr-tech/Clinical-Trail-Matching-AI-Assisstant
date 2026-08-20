from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SecurityCheckResult(BaseModel):
    check_id: int
    title: str
    status: str  # PASS, FAIL, REMEDIATED
    details: str

class SecurityReviewReport(BaseModel):
    phase: str = "Phase 17: Security & Privacy Review"
    total_checks: int = 17
    passed_checks: int
    failed_checks: int
    remediated_checks: int
    secrets_found: List[str] = Field(default_factory=list)
    insecure_routes: List[str] = Field(default_factory=list)
    missing_policies: List[str] = Field(default_factory=list)
    failed_checks_list: List[str] = Field(default_factory=list)
    remediation_applied: List[str] = Field(default_factory=list)
    security_checklist: List[SecurityCheckResult] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)
    regulatory_disclaimer: str
    deployment_status: str
