import logging
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, Optional
from app.schemas.feedback import ReviewerFeedbackSubmission, FeedbackRecord, DisagreementAnalytics
from app.modules.feedback.service import (
    submit_reviewer_feedback,
    get_disagreement_analytics,
    export_deidentified_evaluations,
    get_all_feedback_records
)

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger("clinical_trial_assistant")


from app.schemas.common import UserRole
from app.core.security import require_role, AuthenticatedUser

@router.post("/submit", response_model=Dict[str, Any])
def submit_feedback_endpoint(
    feedback: ReviewerFeedbackSubmission,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER
    ]))
):
    """Submit reviewer feedback or decision override."""
    try:
        record = submit_reviewer_feedback(feedback)
        return {
            "success": True,
            "data": record.model_dump(mode="json")
        }
    except ValueError as ve:
        logger.warning(f"Validation error in feedback submission: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics", response_model=Dict[str, Any])
def get_analytics_endpoint(
    trial_id: Optional[str] = Query(None),
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    """Retrieve AI-human disagreement analytics metrics."""
    try:
        analytics = get_disagreement_analytics(trial_id)
        return {
            "success": True,
            "data": analytics.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error retrieving disagreement analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/deidentified", response_model=Dict[str, Any])
def export_deidentified_endpoint(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Export de-identified evaluation records."""
    try:
        records = export_deidentified_evaluations()
        return {
            "success": True,
            "data": records
        }
    except Exception as e:
        logger.error(f"Error exporting de-identified evaluations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews", response_model=Dict[str, Any])
def get_reviews_endpoint(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER
    ]))
):
    """Retrieve all submitted feedback records."""
    try:
        records = get_all_feedback_records()
        return {
            "success": True,
            "data": [r.model_dump(mode="json") for r in records]
        }
    except Exception as e:
        logger.error(f"Error retrieving feedback records: {e}")
        raise HTTPException(status_code=500, detail=str(e))
