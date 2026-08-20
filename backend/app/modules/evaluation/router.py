import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from app.schemas.evaluation import EvaluationReport, DashboardMetrics
from app.schemas.common import UserRole
from app.core.security import require_role, AuthenticatedUser
from app.modules.evaluation.service import (
    run_measured_evaluation_suite,
    get_researcher_dashboard_metrics
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
logger = logging.getLogger("clinical_trial_assistant")


@router.get("/dashboard", response_model=Dict[str, Any])
def get_dashboard_metrics_endpoint(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR, UserRole.REVIEWER, UserRole.VIEWER
    ]))
):
    """Retrieve aggregated researcher dashboard operational metrics."""
    try:
        metrics = get_researcher_dashboard_metrics()
        return {
            "success": True,
            "data": metrics.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error retrieving researcher dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run", response_model=Dict[str, Any])
@router.post("/run", response_model=Dict[str, Any])
def run_evaluation_suite_endpoint(
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Run automated measured evaluation suite across 10 target benchmark categories."""
    try:
        report = run_measured_evaluation_suite()
        return {
            "success": True,
            "data": report.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Error executing evaluation suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))
