import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.temporal import TemporalValidationRequest, TemporalValidationResult, PatientEligibilityTimeline
from app.modules.temporal.service import (
    evaluate_temporal_rule,
    get_patient_eligibility_timeline,
    record_timeline_event
)

router = APIRouter(prefix="/temporal", tags=["temporal"])
logger = logging.getLogger("clinical_trial_assistant")

class AmbiguousDateReviewRequest(BaseModel):
    validation_id: Optional[str] = None
    patient_id: str
    corrected_date: str
    reviewer_notes: str


@router.post("/validate", response_model=Dict[str, Any])
def validate_temporal_rule_endpoint(request: TemporalValidationRequest):
    """Validate temporal eligibility rule against event and reference dates."""
    try:
        res = evaluate_temporal_rule(request)
        return {
            "success": True,
            "data": res.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error evaluating temporal rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline/patient/{patient_id}/{trial_id}", response_model=Dict[str, Any])
def get_eligibility_timeline_endpoint(patient_id: str, trial_id: str):
    """Retrieve chronological state transitions for a patient's trial eligibility timeline."""
    try:
        timeline = get_patient_eligibility_timeline(patient_id, trial_id)
        return {
            "success": True,
            "data": timeline.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error retrieving eligibility timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review-ambiguous-date", response_model=Dict[str, Any])
def review_ambiguous_date_endpoint(request: AmbiguousDateReviewRequest):
    """Submit human review resolution for an ambiguous clinical date expression."""
    try:
        # Record resolved event in timeline
        evt = record_timeline_event(
            patient_id=request.patient_id,
            trial_id="t-nct04500000",
            criterion_id="crit-ambiguous-date",
            old_status="UNKNOWN",
            new_status="PASS",
            old_value="Ambiguous Date Expression",
            new_value=request.corrected_date,
            trigger_reason=f"Ambiguous Date Human Review: {request.reviewer_notes}"
        )
        return {
            "success": True,
            "data": {
                "corrected_date": request.corrected_date,
                "timeline_event": evt.model_dump(mode="json")
            }
        }
    except Exception as e:
        logger.error(f"Error resolving ambiguous date: {e}")
        raise HTTPException(status_code=500, detail=str(e))
