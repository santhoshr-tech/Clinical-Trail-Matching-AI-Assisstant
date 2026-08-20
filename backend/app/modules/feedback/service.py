import uuid
import hashlib
import datetime
import logging
from typing import List, Dict, Any, Optional
from app.core.db import get_db_connection, init_db
from app.schemas.feedback import (
    ReviewerFeedbackSubmission,
    FeedbackRecord,
    DisagreementAnalytics,
    DisagreementCategoryEnum
)

logger = logging.getLogger("clinical_trial_assistant")


def submit_reviewer_feedback(feedback: ReviewerFeedbackSubmission) -> FeedbackRecord:
    """Submit explicit human reviewer feedback or decision override."""
    is_agreement = feedback.ai_decision.upper() == feedback.human_decision.upper()
    agreement_status = "AGREE" if is_agreement else "DISAGREE"

    # Enforce mandatory rationale for decision overrides
    if not is_agreement:
        if not feedback.override_reason or len(feedback.override_reason.strip()) < 5:
            raise ValueError("Mandatory override rationale (minimum 5 characters) required for decision override.")

    # Classify error type
    error_type = "none"
    if not is_agreement:
        if feedback.ai_decision.upper() == "PASS" and feedback.human_decision.upper() in ["FAIL", "UNKNOWN"]:
            error_type = "false_pass"
        elif feedback.ai_decision.upper() == "FAIL" and feedback.human_decision.upper() in ["PASS", "UNKNOWN"]:
            error_type = "false_fail"

    feedback_id = f"fb-{uuid.uuid4()}"
    now_iso = datetime.datetime.utcnow().isoformat()
    category_val = feedback.disagreement_category.value if feedback.disagreement_category else (None if is_agreement else "other")

    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO researcher_feedback (
            id, patient_id, trial_id, criterion_id, ai_decision, human_decision,
            agreement_status, error_type, disagreement_category, override_reason,
            reviewer_id, model_version, prompt_version, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            feedback_id, feedback.patient_id, feedback.trial_id, feedback.criterion_id,
            feedback.ai_decision.upper(), feedback.human_decision.upper(), agreement_status,
            error_type, category_val, feedback.override_reason, feedback.reviewer_id,
            feedback.model_version, feedback.prompt_version, now_iso
        ))

        # Insert audit log entry
        audit_id = f"audit-fb-{uuid.uuid4()}"
        cursor.execute("""
        INSERT INTO feedback_audit_logs (
            id, feedback_id, reviewer_id, action, rationale, created_at
        ) VALUES (?, ?, ?, ?, ?, ?);
        """, (
            audit_id, feedback_id, feedback.reviewer_id,
            "AGREEMENT_SUBMITTED" if is_agreement else "OVERRIDE_SUBMITTED",
            feedback.override_reason or "Reviewer agreed with AI criterion decision", now_iso
        ))
        conn.commit()

    return FeedbackRecord(
        feedback_id=feedback_id,
        patient_id=feedback.patient_id,
        trial_id=feedback.trial_id,
        criterion_id=feedback.criterion_id,
        ai_decision=feedback.ai_decision.upper(),
        human_decision=feedback.human_decision.upper(),
        agreement_status=agreement_status,
        error_type=error_type,
        disagreement_category=category_val,
        override_reason=feedback.override_reason,
        reviewer_id=feedback.reviewer_id,
        model_version=feedback.model_version,
        prompt_version=feedback.prompt_version,
        created_at=now_iso
    )


def get_disagreement_analytics(trial_id: Optional[str] = None) -> DisagreementAnalytics:
    """Compute agreement rates, disagreement categories, false-pass/false-fail metrics, and model comparisons."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT * FROM researcher_feedback"
        params = []
        if trial_id:
            query += " WHERE trial_id = ?"
            params.append(trial_id)
            
        cursor.execute(query, params)
        rows = cursor.fetchall()

        total = len(rows)
        if total == 0:
            return DisagreementAnalytics(
                total_evaluations=0,
                agree_count=0,
                disagree_count=0,
                agreement_rate=100.0,
                disagreement_rate=0.0,
                false_pass_count=0,
                false_fail_count=0,
                category_breakdown={},
                model_version_comparison={},
                most_disputed_criteria=[]
            )

        agree_count = sum(1 for r in rows if dict(r)["agreement_status"] == "AGREE")
        disagree_count = total - agree_count
        agree_rate = round((agree_count / total) * 100.0, 1)
        disagree_rate = round((disagree_count / total) * 100.0, 1)

        false_pass = sum(1 for r in rows if dict(r)["error_type"] == "false_pass")
        false_fail = sum(1 for r in rows if dict(r)["error_type"] == "false_fail")

        category_counts: Dict[str, int] = {}
        model_comp: Dict[str, Dict[str, Any]] = {}
        criteria_counts: Dict[str, int] = {}

        for r in rows:
            d = dict(r)
            cat = d.get("disagreement_category")
            if cat and d["agreement_status"] == "DISAGREE":
                category_counts[cat] = category_counts.get(cat, 0) + 1

            mv = d["model_version"]
            if mv not in model_comp:
                model_comp[mv] = {"total": 0, "agree": 0, "disagree": 0}
            model_comp[mv]["total"] += 1
            if d["agreement_status"] == "AGREE":
                model_comp[mv]["agree"] += 1
            else:
                model_comp[mv]["disagree"] += 1

            if d["agreement_status"] == "DISAGREE":
                cid = d["criterion_id"]
                criteria_counts[cid] = criteria_counts.get(cid, 0) + 1

        most_disputed = [
            {"criterion_id": cid, "disagreement_count": cnt}
            for cid, cnt in sorted(criteria_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return DisagreementAnalytics(
            total_evaluations=total,
            agree_count=agree_count,
            disagree_count=disagree_count,
            agreement_rate=agree_rate,
            disagreement_rate=disagree_rate,
            false_pass_count=false_pass,
            false_fail_count=false_fail,
            category_breakdown=category_counts,
            model_version_comparison=model_comp,
            most_disputed_criteria=most_disputed
        )


def export_deidentified_evaluations() -> List[Dict[str, Any]]:
    """Export evaluation records with de-identified patient hashes."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM researcher_feedback ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        
        exported: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            # De-identify patient ID using SHA-256 hash
            anon_id = f"anon-{hashlib.sha256(d['patient_id'].encode()).hexdigest()[:12]}"
            exported.append({
                "record_id": d["id"],
                "anon_patient_id": anon_id,
                "trial_id": d["trial_id"],
                "criterion_id": d["criterion_id"],
                "ai_decision": d["ai_decision"],
                "human_decision": d["human_decision"],
                "agreement_status": d["agreement_status"],
                "error_type": d["error_type"],
                "disagreement_category": d.get("disagreement_category"),
                "override_reason": d.get("override_reason"),
                "model_version": d["model_version"],
                "prompt_version": d["prompt_version"],
                "evaluated_at": d["created_at"]
            })
        return exported


def get_all_feedback_records() -> List[FeedbackRecord]:
    """Get all feedback records."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM researcher_feedback ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        
        recs: List[FeedbackRecord] = []
        for r in rows:
            d = dict(r)
            recs.append(
                FeedbackRecord(
                    feedback_id=d["id"],
                    patient_id=d["patient_id"],
                    trial_id=d["trial_id"],
                    criterion_id=d["criterion_id"],
                    ai_decision=d["ai_decision"],
                    human_decision=d["human_decision"],
                    agreement_status=d["agreement_status"],
                    error_type=d["error_type"],
                    disagreement_category=d.get("disagreement_category"),
                    override_reason=d.get("override_reason"),
                    reviewer_id=d["reviewer_id"],
                    model_version=d["model_version"],
                    prompt_version=d["prompt_version"],
                    created_at=d["created_at"]
                )
            )
        return recs
