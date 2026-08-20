import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from app.schemas.matching import MatchEvaluationRequest, TrialMatchResult
from app.modules.matching.service import run_patient_trial_matching
from app.core.db import get_db_connection, init_db

router = APIRouter(prefix="/matching", tags=["matching"])
logger = logging.getLogger("clinical_trial_assistant")


@router.post("/evaluate", response_model=Dict[str, Any])
def evaluate_patient_trial_matching(request: MatchEvaluationRequest):
    """Run deterministic eligibility matching for a patient against approved trial criteria."""
    try:
        match_result = run_patient_trial_matching(request.patient_id, request.trial_id)
        return {
            "success": True,
            "data": match_result.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Matching evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient/{patient_id}", response_model=Dict[str, Any])
def get_patient_match_history(patient_id: str):
    """Get screening match history for a patient."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_trial_matches WHERE patient_id = ? ORDER BY evaluated_at DESC;", (patient_id,))
        rows = cursor.fetchall()
        matches = [dict(r) for r in rows]
        return {
            "success": True,
            "data": matches
        }


@router.get("/trial/{trial_id}", response_model=Dict[str, Any])
def get_trial_candidates(trial_id: str):
    """Get screening candidates for a clinical trial."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patient_trial_matches WHERE trial_id = ? ORDER BY match_score DESC, evaluated_at DESC;", (trial_id,))
        rows = cursor.fetchall()
        matches = [dict(r) for r in rows]
        return {
            "success": True,
            "data": matches
        }
