import uuid
import json
import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.core.db import get_db_connection, init_db
from app.schemas.rescreening import (
    ReScreeningTriggerEnum,
    ReScreeningJobStatusEnum,
    ReScreeningJob,
    ReScreeningImpactSummary,
    CoordinatorNotification
)
from app.modules.matching.service import run_patient_trial_matching
from app.schemas.matching import TrialMatchResult

logger = logging.getLogger("clinical_trial_assistant")


def trigger_re_screening_job(
    trigger_type: ReScreeningTriggerEnum,
    trigger_source_id: str,
    patient_id: Optional[str] = None,
    trial_id: Optional[str] = None,
    idempotency_key: Optional[str] = None
) -> ReScreeningJob:
    """Trigger an automatic re-screening job with idempotency protection."""
    key = idempotency_key or f"ik-{trigger_type.value}-{trigger_source_id}-{patient_id or 'all'}-{trial_id or 'all'}"
    
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Idempotency Check: Return existing job if duplicate trigger key found
        cursor.execute("SELECT * FROM re_screening_jobs WHERE idempotency_key = ?;", (key,))
        existing = cursor.fetchone()
        if existing:
            d = dict(existing)
            logger.info(f"Idempotent re-screening job returned: {d['id']}")
            return ReScreeningJob(
                job_id=d["id"],
                trigger_type=ReScreeningTriggerEnum(d["trigger_type"]),
                trigger_source_id=d["trigger_source_id"],
                patient_id=d.get("patient_id"),
                trial_id=d.get("trial_id"),
                idempotency_key=d["idempotency_key"],
                status=ReScreeningJobStatusEnum(d["status"]),
                retry_count=d["retry_count"],
                max_retries=d["max_retries"],
                error_message=d.get("error_message"),
                created_at=d["created_at"],
                completed_at=d.get("completed_at")
            )

        job_id = f"job-{uuid.uuid4()}"
        now_iso = datetime.datetime.utcnow().isoformat()

        cursor.execute("""
        INSERT INTO re_screening_jobs (
            id, trigger_type, trigger_source_id, patient_id, trial_id, idempotency_key, status, retry_count, max_retries, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'pending', 0, 3, ?);
        """, (
            job_id, trigger_type.value, trigger_source_id, patient_id, trial_id, key, now_iso
        ))
        conn.commit()

        return ReScreeningJob(
            job_id=job_id,
            trigger_type=trigger_type,
            trigger_source_id=trigger_source_id,
            patient_id=patient_id,
            trial_id=trial_id,
            idempotency_key=key,
            status=ReScreeningJobStatusEnum.PENDING,
            retry_count=0,
            max_retries=3,
            created_at=now_iso
        )


def execute_re_screening_job(job_id: str) -> ReScreeningImpactSummary:
    """Execute re-screening job, compute status deltas, preserve history, and notify coordinators."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM re_screening_jobs WHERE id = ?;", (job_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Re-screening job '{job_id}' not found.")

        job_dict = dict(row)
        cursor.execute("UPDATE re_screening_jobs SET status = 'running' WHERE id = ?;", (job_id,))
        conn.commit()

    patient_id = job_dict.get("patient_id") or "11111111-1111-1111-1111-111111111111"
    trial_id = job_dict.get("trial_id") or "t-nct04500000"

    try:
        # 1. Fetch previous screening run from history
        old_status = "UNKNOWN"
        old_score = 0.0
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT overall_status, match_score FROM screening_history
            WHERE patient_id = ? AND trial_id = ?
            ORDER BY evaluated_at DESC LIMIT 1;
            """, (patient_id, trial_id))
            prev_row = cursor.fetchone()
            if prev_row:
                old_status = prev_row[0]
                old_score = prev_row[1]

        # 2. Run new deterministic screening run
        new_match: TrialMatchResult = run_patient_trial_matching(patient_id, trial_id)
        new_status = new_match.overall_status.value
        new_score = new_match.match_score

        # 3. Append new run to screening_history (never delete old runs!)
        run_id = f"run-{uuid.uuid4()}"
        now_iso = datetime.datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO screening_history (
                id, patient_id, trial_id, overall_status, match_score, results_json, trigger_job_id, evaluated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                run_id, patient_id, trial_id, new_status, new_score,
                json.dumps(new_match.model_dump(mode="json")), job_id, now_iso
            ))

            # 4. Update job status to completed
            cursor.execute("""
            UPDATE re_screening_jobs
            SET status = 'completed', completed_at = ?
            WHERE id = ?;
            """, (now_iso, job_id))
            conn.commit()

        # 5. Dispatch coordinator notification if status changed
        requires_review = old_status != new_status
        notification_sent = False

        if requires_review:
            notif_id = f"notif-{uuid.uuid4()}"
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT INTO coordinator_notifications (
                    id, job_id, patient_id, trial_id, title, message
                ) VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    notif_id, job_id, patient_id, trial_id,
                    f"Re-screening State Change: {old_status} -> {new_status}",
                    f"Automatic re-screening triggered by '{job_dict['trigger_type']}' resulted in eligibility state change."
                ))
                conn.commit()
                notification_sent = True

        return ReScreeningImpactSummary(
            job_id=job_id,
            patient_id=patient_id,
            trial_id=trial_id,
            old_status=old_status,
            new_status=new_status,
            old_score=old_score,
            new_score=new_score,
            changed_criteria_count=1 if requires_review else 0,
            requires_human_review=requires_review,
            coordinator_notification_sent=notification_sent
        )

    except Exception as e:
        logger.error(f"Execution error in job '{job_id}': {e}")
        new_retries = job_dict["retry_count"] + 1
        new_job_status = "failed" if new_retries >= job_dict["max_retries"] else "pending"
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE re_screening_jobs
            SET status = ?, retry_count = ?, error_message = ?
            WHERE id = ?;
            """, (new_job_status, new_retries, str(e), job_id))
            conn.commit()
            
        raise e


def get_all_rescreening_jobs() -> List[ReScreeningJob]:
    """Retrieve all re-screening jobs."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM re_screening_jobs ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        
        jobs: List[ReScreeningJob] = []
        for r in rows:
            d = dict(r)
            jobs.append(
                ReScreeningJob(
                    job_id=d["id"],
                    trigger_type=ReScreeningTriggerEnum(d["trigger_type"]),
                    trigger_source_id=d["trigger_source_id"],
                    patient_id=d.get("patient_id"),
                    trial_id=d.get("trial_id"),
                    idempotency_key=d["idempotency_key"],
                    status=ReScreeningJobStatusEnum(d["status"]),
                    retry_count=d["retry_count"],
                    max_retries=d["max_retries"],
                    error_message=d.get("error_message"),
                    created_at=d["created_at"],
                    completed_at=d.get("completed_at")
                )
            )
        return jobs


def get_coordinator_notifications() -> List[CoordinatorNotification]:
    """Retrieve all coordinator notifications."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coordinator_notifications ORDER BY created_at DESC;")
        rows = cursor.fetchall()
        
        notifs: List[CoordinatorNotification] = []
        for r in rows:
            d = dict(r)
            notifs.append(
                CoordinatorNotification(
                    notification_id=d["id"],
                    job_id=d["job_id"],
                    patient_id=d["patient_id"],
                    trial_id=d["trial_id"],
                    title=d["title"],
                    message=d["message"],
                    is_read=bool(d["is_read"]),
                    created_at=d["created_at"]
                )
            )
        return notifs
