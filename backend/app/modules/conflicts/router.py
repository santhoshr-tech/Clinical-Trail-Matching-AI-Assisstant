import logging
from fastapi import APIRouter, HTTPException, Header
from typing import Dict, Any, List, Optional
from app.schemas.conflicts import ConflictResolutionRequest, ClinicalConflictCase
from app.modules.conflicts.service import (
    resolve_clinical_conflict,
    get_patient_conflict_cases,
    get_conflict_analytics
)

router = APIRouter(prefix="/conflicts", tags=["conflicts"])
logger = logging.getLogger("clinical_trial_assistant")


@router.get("/cases/patient/{patient_id}", response_model=Dict[str, Any])
def list_patient_conflict_cases(patient_id: str):
    """Retrieve all side-by-side conflict cases for a patient."""
    try:
        cases = get_patient_conflict_cases(patient_id)
        return {
            "success": True,
            "data": [c.model_dump(mode="json") for c in cases]
        }
    except Exception as e:
        logger.error(f"Error fetching conflict cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resolve", response_model=Dict[str, Any])
def resolve_conflict_endpoint(
    request: ConflictResolutionRequest,
    x_user_email: Optional[str] = Header("investigator@clinicaltrial.ai")
):
    """Resolve a clinical evidence conflict through controlled human workflow requiring mandatory reason."""
    try:
        res = resolve_clinical_conflict(request, user_email=x_user_email or "investigator@clinicaltrial.ai")
        return {
            "success": True,
            "data": res
        }
    except ValueError as ve:
        logger.warning(f"Validation error in conflict resolution: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error resolving conflict: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=Dict[str, Any])
def get_analytics_endpoint(patient_id: Optional[str] = None):
    """Retrieve conflict analytics metrics and category breakdown."""
    try:
        analytics = get_conflict_analytics(patient_id)
        return {
            "success": True,
            "data": analytics.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error getting conflict analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
