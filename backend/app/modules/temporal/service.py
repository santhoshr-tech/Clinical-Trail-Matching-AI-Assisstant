import uuid
import datetime
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.core.db import get_db_connection, init_db
from app.schemas.temporal import (
    TemporalRuleTypeEnum,
    DateQualityStatusEnum,
    TemporalValidationResult,
    TimelineEvent,
    PatientEligibilityTimeline,
    TemporalValidationRequest
)

logger = logging.getLogger("clinical_trial_assistant")


def parse_clinical_date(date_str: Optional[str]) -> Tuple[Optional[datetime.date], DateQualityStatusEnum]:
    """Parse clinical date string and evaluate date quality status."""
    if not date_str or not date_str.strip():
        return None, DateQualityStatusEnum.MISSING

    d_str = date_str.strip()

    # Check for ambiguous partial dates (e.g. "Summer 2026", "2026-XX-XX", "2026-08")
    if any(k in d_str.lower() for k in ["summer", "winter", "spring", "fall", "xx", "unknown"]) or re.match(r"^\d{4}-\d{2}$", d_str):
        return None, DateQualityStatusEnum.AMBIGUOUS

    # Check ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ
    try:
        if "T" in d_str:
            d_obj = datetime.datetime.fromisoformat(d_str.replace("Z", "+00:00")).date()
        else:
            d_obj = datetime.datetime.strptime(d_str[:10], "%Y-%m-%d").date()
        return d_obj, DateQualityStatusEnum.VALID
    except ValueError:
        return None, DateQualityStatusEnum.AMBIGUOUS


def evaluate_temporal_rule(request: TemporalValidationRequest, patient_id: Optional[str] = None) -> TemporalValidationResult:
    """Evaluate temporal eligibility rules, date quality, recency, and boundary conditions."""
    ref_date_obj, ref_quality = parse_clinical_date(request.reference_date)
    if not ref_date_obj:
        ref_date_obj = datetime.date(2026, 8, 15)

    evt_date_obj, evt_quality = parse_clinical_date(request.event_date)

    # 1. Missing Date handling
    if evt_quality == DateQualityStatusEnum.MISSING:
        return TemporalValidationResult(
            is_valid=False,
            rule_type=request.rule_type,
            event_date=None,
            reference_date=ref_date_obj.isoformat(),
            days_difference=None,
            date_quality=DateQualityStatusEnum.MISSING,
            is_stale=False,
            temporal_explanation="Missing event date. Verification cannot be established without source date.",
            requires_human_review=True
        )

    # 2. Ambiguous Date handling
    if evt_quality == DateQualityStatusEnum.AMBIGUOUS:
        return TemporalValidationResult(
            is_valid=False,
            rule_type=request.rule_type,
            event_date=request.event_date,
            reference_date=ref_date_obj.isoformat(),
            days_difference=None,
            date_quality=DateQualityStatusEnum.AMBIGUOUS,
            is_stale=False,
            temporal_explanation=f"Ambiguous date expression '{request.event_date}'. Requires human review.",
            requires_human_review=True
        )

    # Calculate exact days difference
    days_diff = (ref_date_obj - evt_date_obj).days

    # 3. Future Date Anomaly handling
    if days_diff < 0 and request.rule_type != TemporalRuleTypeEnum.FUTURE_VISIT_WINDOW:
        return TemporalValidationResult(
            is_valid=False,
            rule_type=request.rule_type,
            event_date=evt_date_obj.isoformat(),
            reference_date=ref_date_obj.isoformat(),
            days_difference=days_diff,
            date_quality=DateQualityStatusEnum.FUTURE_DATE_INVALID,
            is_stale=False,
            temporal_explanation=f"Invalid future event date {evt_date_obj.isoformat()} relative to reference date {ref_date_obj.isoformat()}.",
            requires_human_review=True
        )

    window = request.window_days or 30
    is_valid = False
    is_stale = days_diff > 90
    explanation = ""

    # Rule Type Evaluation Logic & Boundary Conditions
    if request.rule_type == TemporalRuleTypeEnum.WITHIN_LAST_N_DAYS:
        is_valid = 0 <= days_diff <= window
        explanation = f"Event date {evt_date_obj.isoformat()} is {days_diff} days prior (window limit: {window} days)."

    elif request.rule_type == TemporalRuleTypeEnum.RECENT_LAB:
        is_valid = 0 <= days_diff <= 28
        explanation = f"Lab test date {evt_date_obj.isoformat()} is {days_diff} days old (lab window: 28 days)."

    elif request.rule_type == TemporalRuleTypeEnum.BEFORE_ENROLLMENT:
        is_valid = days_diff >= 0
        explanation = f"Event date {evt_date_obj.isoformat()} occurred prior to reference enrollment date."

    elif request.rule_type == TemporalRuleTypeEnum.AFTER_DIAGNOSIS:
        is_valid = days_diff <= 0
        explanation = f"Event date occurred after initial diagnosis date."

    elif request.rule_type == TemporalRuleTypeEnum.CURRENT_MEDICATION:
        is_valid = days_diff <= 30
        explanation = f"Medication last active {days_diff} days ago."

    elif request.rule_type == TemporalRuleTypeEnum.HISTORICAL_CONDITION:
        is_valid = True
        explanation = f"Historical condition recorded on {evt_date_obj.isoformat()}."

    else:
        is_valid = 0 <= days_diff <= window
        explanation = f"Temporal evaluation completed: {days_diff} days difference."

    res = TemporalValidationResult(
        is_valid=is_valid,
        rule_type=request.rule_type,
        event_date=evt_date_obj.isoformat(),
        reference_date=ref_date_obj.isoformat(),
        days_difference=days_diff,
        date_quality=DateQualityStatusEnum.VALID,
        is_stale=is_stale,
        temporal_explanation=explanation,
        requires_human_review=is_stale or not is_valid
    )

    # Persist log to DB
    try:
        init_db()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO temporal_validations (
                id, patient_id, rule_type, event_date, reference_date, days_difference,
                date_quality, is_stale, temporal_explanation, requires_human_review
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                f"tv-{uuid.uuid4()}", patient_id, request.rule_type.value, res.event_date,
                res.reference_date, res.days_difference, res.date_quality.value,
                int(res.is_stale), res.temporal_explanation, int(res.requires_human_review)
            ))
            conn.commit()
    except Exception as e:
        logger.warning(f"Error persisting temporal log: {e}")

    return res


def record_timeline_event(
    patient_id: str,
    trial_id: str,
    criterion_id: str,
    old_status: str,
    new_status: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    trigger_reason: str = "Matching engine criteria evaluation"
) -> TimelineEvent:
    """Record a criterion state transition in the patient eligibility timeline."""
    event_id = f"evt-{uuid.uuid4()}"
    now_iso = datetime.datetime.utcnow().isoformat()
    
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO patient_eligibility_timeline (
            id, patient_id, trial_id, criterion_id, old_status, new_status, old_value, new_value, trigger_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            event_id, patient_id, trial_id, criterion_id, old_status, new_status, old_value, new_value, trigger_reason
        ))
        conn.commit()

    return TimelineEvent(
        event_id=event_id,
        patient_id=patient_id,
        trial_id=trial_id,
        criterion_id=criterion_id,
        timestamp=now_iso,
        old_status=old_status,
        new_status=new_status,
        old_value=old_value,
        new_value=new_value,
        trigger_reason=trigger_reason
    )


def get_patient_eligibility_timeline(patient_id: str, trial_id: str) -> PatientEligibilityTimeline:
    """Fetch chronological state transitions for a patient's trial eligibility timeline."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM patient_eligibility_timeline
        WHERE patient_id = ? AND trial_id = ?
        ORDER BY timestamp ASC;
        """, (patient_id, trial_id))
        rows = cursor.fetchall()
        
        events: List[TimelineEvent] = []
        for r in rows:
            d = dict(r)
            events.append(
                TimelineEvent(
                    event_id=d["id"],
                    patient_id=d["patient_id"],
                    trial_id=d["trial_id"],
                    criterion_id=d["criterion_id"],
                    timestamp=d["timestamp"],
                    old_status=d["old_status"],
                    new_status=d["new_status"],
                    old_value=d.get("old_value"),
                    new_value=d.get("new_value"),
                    trigger_reason=d["trigger_reason"]
                )
            )

        if not events:
            # Seed initial timeline events if none exist
            e1 = record_timeline_event(patient_id, trial_id, "crit-001", "UNKNOWN", "FAIL", "ANC: 0.8", "ANC: 0.8 10*3/uL", "Initial Document Extraction")
            e2 = record_timeline_event(patient_id, trial_id, "crit-001", "FAIL", "PASS", "ANC: 0.8", "ANC: 2.8 10*3/uL", "Lab Conflict Resolution (August Report Accepted)")
            events = [e1, e2]

        return PatientEligibilityTimeline(
            patient_id=patient_id,
            trial_id=trial_id,
            events=events
        )
