import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
from app.schemas.extraction import FactReviewRequest, ExtractionPipelineResult
from app.modules.extraction.service import (
    process_document_extraction,
    review_fact
)
from app.core.db import get_db_connection, init_db

router = APIRouter(prefix="/extraction", tags=["extraction"])
logger = logging.getLogger("clinical_trial_assistant")

class ExtractionRequest(BaseModel):
    patient_id: str
    document_id: str
    document_text: str


@router.post("/extract", response_model=Dict[str, Any])
def extract_facts(request: ExtractionRequest):
    """Trigger clinical fact extraction pipeline over document text."""
    try:
        res = process_document_extraction(request.patient_id, request.document_id, request.document_text)
        return {
            "success": True,
            "data": res.model_dump(mode="json")
        }
    except Exception as e:
        logger.error(f"Fact extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/facts/patient/{patient_id}", response_model=Dict[str, Any])
def get_patient_extracted_facts(patient_id: str):
    """Get all extracted clinical facts for a patient."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM extracted_clinical_facts WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
        rows = cursor.fetchall()
        facts = [dict(r) for r in rows]
        return {
            "success": True,
            "data": facts
        }


@router.post("/review", response_model=Dict[str, Any])
def review_extracted_fact_endpoint(request: FactReviewRequest):
    """Approve, edit, or reject an extracted clinical fact."""
    try:
        updated_fact = review_fact(request.fact_id, request.review_status.value, request.edited_canonical_label)
        return {
            "success": True,
            "data": updated_fact
        }
    except Exception as e:
        logger.error(f"Fact review error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/conflicts/patient/{patient_id}", response_model=Dict[str, Any])
def get_patient_fact_conflicts(patient_id: str):
    """List fact conflicts for a patient."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fact_conflicts WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
        rows = cursor.fetchall()
        conflicts = [dict(r) for r in rows]
        return {
            "success": True,
            "data": conflicts
        }
