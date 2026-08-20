from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.common import ApiResponse, UserRole
from app.core.security import require_role, AuthenticatedUser
from app.core.db import get_db_connection
from app.schemas.criteria import (
    StructuredCriterion,
    CriterionCreateRequest,
    CriterionUpdateRequest,
    CriterionApprovalRequest,
    ApprovalStatusEnum
)
from app.modules.criteria.service import (
    parse_protocol_text_into_criteria,
    store_parsed_criteria,
    get_trial_criteria,
    update_criterion,
    set_criterion_approval
)
from app.modules.audit.service import log_audit_event

router = APIRouter(prefix="/criteria", tags=["criteria"])

@router.post("/parse/{trial_id}", response_model=ApiResponse[List[dict]])
async def parse_trial_criteria(
    trial_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Parse unstructured protocol eligibility criteria text into structured rule nodes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT eligibility_criteria_text FROM trials WHERE id = ? OR nct_id = ?;", (trial_id, trial_id))
    row = cursor.fetchone()
    conn.close()

    if not row or not row["eligibility_criteria_text"]:
        raise HTTPException(status_code=404, detail=f"Protocol text for trial {trial_id} not found.")

    protocol_text = row["eligibility_criteria_text"]
    structured_nodes = parse_protocol_text_into_criteria(trial_id, protocol_text)
    saved_records = store_parsed_criteria(trial_id, structured_nodes)

    log_audit_event(
        action="PARSE_TRIAL_CRITERIA",
        entity_type="trial_criteria",
        entity_id=trial_id,
        user_id=current_user.user_id,
        payload={"trialId": trial_id, "criteriaCount": len(saved_records)}
    )

    return ApiResponse(data=saved_records)


@router.get("/trial/{trial_id}", response_model=ApiResponse[List[dict]])
async def list_trial_criteria(
    trial_id: str,
    approved_only: bool = Query(default=False)
):
    """List structured criteria for a trial."""
    records = get_trial_criteria(trial_id, approved_only=approved_only)
    return ApiResponse(data=records)


@router.post("/create", response_model=ApiResponse[dict])
async def create_manual_criterion(
    request: CriterionCreateRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Manually add a structured criterion to a trial."""
    criterion = StructuredCriterion(
        trial_id=request.trial_id,
        criterion_type=request.criterion_type,
        category=request.category,
        operator=request.operator,
        value_primary=request.value_primary,
        value_secondary=request.value_secondary,
        unit=request.unit,
        temporal_window=request.temporal_window,
        is_negated=request.is_negated,
        logic_group=request.logic_group,
        raw_text=request.raw_text,
        approval_status=ApprovalStatusEnum.PENDING
    )
    records = store_parsed_criteria(request.trial_id, [criterion])
    
    log_audit_event(
        action="CREATE_MANUAL_CRITERION",
        entity_type="trial_criteria",
        entity_id=criterion.id,
        user_id=current_user.user_id,
        payload={"trialId": request.trial_id, "category": request.category}
    )

    return ApiResponse(data=records[0] if records else {})


@router.put("/{criterion_id}", response_model=ApiResponse[dict])
async def edit_criterion_endpoint(
    criterion_id: str,
    request: CriterionUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Edit criterion and create a version snapshot."""
    try:
        updated = update_criterion(criterion_id, request, user_id=current_user.user_id)
        log_audit_event(
            action="UPDATE_CRITERION",
            entity_type="trial_criteria",
            entity_id=criterion_id,
            user_id=current_user.user_id,
            payload={"version": updated["version"], "change_summary": request.change_summary}
        )
        return ApiResponse(data=updated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{criterion_id}/approve", response_model=ApiResponse[dict])
async def approve_criterion_endpoint(
    criterion_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Approve criterion for screening usage."""
    try:
        updated = set_criterion_approval(criterion_id, ApprovalStatusEnum.APPROVED, user_id=current_user.user_id)
        log_audit_event(
            action="APPROVE_CRITERION",
            entity_type="trial_criteria",
            entity_id=criterion_id,
            user_id=current_user.user_id,
            payload={"status": "approved"}
        )
        return ApiResponse(data=updated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{criterion_id}/reject", response_model=ApiResponse[dict])
async def reject_criterion_endpoint(
    criterion_id: str,
    current_user: AuthenticatedUser = Depends(require_role([
        UserRole.ADMIN, UserRole.RESEARCH_COORDINATOR, UserRole.INVESTIGATOR
    ]))
):
    """Reject criterion."""
    try:
        updated = set_criterion_approval(criterion_id, ApprovalStatusEnum.REJECTED, user_id=current_user.user_id)
        log_audit_event(
            action="REJECT_CRITERION",
            entity_type="trial_criteria",
            entity_id=criterion_id,
            user_id=current_user.user_id,
            payload={"status": "rejected"}
        )
        return ApiResponse(data=updated)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
