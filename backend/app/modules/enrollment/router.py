import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.schemas.common import ApiResponse
from app.modules.enrollment.schemas import (
    TrialScreeningRequest,
    ConfirmEnrollmentRequest,
    ProgressReportUploadRequest,
    DiscontinueEnrollmentRequest
)
from app.modules.enrollment import service

router = APIRouter(prefix="/enrollment", tags=["enrollment"])
logger = logging.getLogger("clinical_trial_assistant")


@router.post("/screen", response_model=ApiResponse[Dict[str, Any]])
def screen_patient_for_trial_endpoint(req: TrialScreeningRequest):
    """Screen patient report against a specific trial using Phase 6 matching engine."""
    try:
        res = service.screen_patient_for_trial(req.patient_id, req.trial_id)
        return ApiResponse(data=res)
    except Exception as e:
        logger.error(f"Screening error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm", response_model=ApiResponse[Dict[str, Any]])
def confirm_enrollment_endpoint(req: ConfirmEnrollmentRequest):
    """Confirm enrollment for eligible patient and generate unique trial enrollment ID."""
    try:
        res = service.confirm_trial_enrollment(
            patient_id=req.patient_id,
            trial_id=req.trial_id,
            baseline_report_id=req.baseline_report_id,
            baseline_metric_value=req.baseline_metric_value
        )
        return ApiResponse(data=res)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Confirm enrollment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cohort/{trial_id}", response_model=ApiResponse[List[Dict[str, Any]]])
def get_trial_cohort_endpoint(trial_id: str):
    """Get enrolled cohort for a trial with progress trends and status."""
    try:
        cohort = service.get_trial_cohort(trial_id)
        return ApiResponse(data=cohort)
    except Exception as e:
        logger.error(f"Cohort fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/progress", response_model=ApiResponse[Dict[str, Any]])
def upload_weekly_progress_endpoint(req: ProgressReportUploadRequest):
    """Upload weekly treatment progress report and calculate responder trend."""
    try:
        res = service.upload_weekly_progress_report(
            enrollment_id=req.enrollment_id,
            key_metric_value=req.key_metric_value,
            report_id=req.report_id,
            key_metric_name=req.key_metric_name,
            notes=req.notes
        )
        return ApiResponse(data=res)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Progress upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discontinue", response_model=ApiResponse[Dict[str, Any]])
def discontinue_enrollment_endpoint(req: DiscontinueEnrollmentRequest):
    """Discontinue non-responder enrollment without deleting historical data."""
    try:
        res = service.discontinue_enrollment(req.enrollment_id, req.reason)
        return ApiResponse(data=res)
    except Exception as e:
        logger.error(f"Discontinue enrollment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-missed-weeks", response_model=ApiResponse[Dict[str, Any]])
def check_missed_weeks_endpoint():
    """Trigger scheduled missed-week detection check and dispatch email & in-app alerts."""
    try:
        res = service.check_and_alert_missed_weeks()
        return ApiResponse(data=res)
    except Exception as e:
        logger.error(f"Missed week check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
