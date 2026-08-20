import uuid
import datetime
import logging
from typing import Dict, Any, List, Optional
from app.core.db import get_db_connection, init_db
from app.modules.matching.service import run_patient_trial_matching
from app.core.email_service import send_missed_week_alert_email
from app.schemas.matching import TrialMatchResult

logger = logging.getLogger("clinical_trial_assistant")


def screen_patient_for_trial(patient_id: str, trial_id: str) -> Dict[str, Any]:
    """
    Screen patient medical report/facts against a selected trial using Phase 6 deterministic matching engine.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, key_metric_name FROM trials WHERE id = ?;", (trial_id,))
        trial_row = cursor.fetchone()
        trial_title = trial_row["title"] if trial_row else f"Trial {trial_id}"

    # Run deterministic matching engine
    match_result: TrialMatchResult = run_patient_trial_matching(patient_id, trial_id)
    overall_status = str(match_result.overall_status.value if hasattr(match_result.overall_status, "value") else match_result.overall_status)
    overall_status_upper = overall_status.upper()

    is_eligible = overall_status_upper in ["ELIGIBLE_FOR_REVIEW", "POTENTIALLY_ELIGIBLE"] or match_result.match_score >= 0.70

    if is_eligible:
        message = f"Eligible - Patient can be enrolled in {trial_title}"
    else:
        message = f"Not Eligible for {trial_title} - Please add/select next patient"

    return {
        "patient_id": patient_id,
        "trial_id": trial_id,
        "trial_title": trial_title,
        "overall_status": overall_status,
        "match_score": match_result.match_score,
        "is_eligible": is_eligible,
        "message": message
    }


def confirm_trial_enrollment(
    patient_id: str,
    trial_id: str,
    baseline_report_id: Optional[str] = None,
    baseline_metric_value: Optional[float] = None
) -> Dict[str, Any]:
    """
    Confirm enrollment for eligible patient, generate unique trial-specific enrollment ID, and store in DB.
    Format: {TRIAL_CODE}-{YEAR}-{SEQUENCE} e.g. DIAB2026-001 or NCT04500000-2026-001.
    """
    init_db()
    today_str = datetime.date.today().isoformat()
    next_due_str = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    year_str = datetime.date.today().strftime("%Y")

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Fetch trial code prefix
        cursor.execute("SELECT nct_id, title, key_metric_name FROM trials WHERE id = ?;", (trial_id,))
        trial_row = cursor.fetchone()
        if not trial_row:
            raise ValueError(f"Trial '{trial_id}' not found.")

        nct_id = trial_row["nct_id"] or "TR"
        # Generate slug code e.g. NCT04500000 -> NCT04500000
        trial_code = nct_id.replace("-", "").upper()

        # 2. Check for existing enrollment
        cursor.execute("SELECT * FROM trial_enrollments WHERE patient_id = ? AND trial_id = ?;", (patient_id, trial_id))
        existing = cursor.fetchone()
        if existing:
            return dict(existing)

        # 3. Compute sequence number
        cursor.execute("SELECT COUNT(*) FROM trial_enrollments WHERE trial_id = ?;", (trial_id,))
        seq_count = cursor.fetchone()[0] + 1
        seq_str = f"{seq_count:03d}"

        enrollment_id = f"{trial_code}-{year_str}-{seq_str}"
        key_metric = trial_row["key_metric_name"] or "HbA1c"

        # 4. Insert enrollment
        cursor.execute("""
        INSERT INTO trial_enrollments (
            enrollment_id, patient_id, trial_id, status, enrolled_date,
            baseline_report_id, baseline_metric_value, current_metric_value,
            next_expected_report_date, missed_week, created_at
        ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP);
        """, (
            enrollment_id, patient_id, trial_id, today_str,
            baseline_report_id, baseline_metric_value, baseline_metric_value,
            next_due_str
        ))

        # 5. Insert initial Week 1 baseline progress report if baseline metric present
        if baseline_metric_value is not None:
            prog_id = f"prog-{uuid.uuid4()}"
            cursor.execute("""
            INSERT INTO trial_progress_reports (
                id, enrollment_id, report_id, week_number, upload_date,
                key_metric_name, key_metric_value, comparison_to_previous, comparison_to_baseline, is_improving, notes
            ) VALUES (?, ?, ?, 1, ?, ?, ?, 0.0, 0.0, 1, 'Baseline Report');
            """, (
                prog_id, enrollment_id, baseline_report_id, today_str, key_metric, baseline_metric_value
            ))

        conn.commit()

        cursor.execute("SELECT * FROM trial_enrollments WHERE enrollment_id = ?;", (enrollment_id,))
        return dict(cursor.fetchone())


def upload_weekly_progress_report(
    enrollment_id: str,
    key_metric_value: float,
    report_id: Optional[str] = None,
    key_metric_name: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a new weekly progress report for an active enrollment and perform disease-agnostic metric evaluation.
    """
    init_db()
    today_str = datetime.date.today().isoformat()
    next_due_str = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Fetch enrollment and trial config
        cursor.execute("""
        SELECT e.*, t.key_metric_name as trial_metric, t.improvement_direction, t.improvement_threshold_weeks
        FROM trial_enrollments e
        JOIN trials t ON e.trial_id = t.id
        WHERE e.enrollment_id = ?;
        """, (enrollment_id,))
        enr = cursor.fetchone()
        if not enr:
            raise ValueError(f"Enrollment '{enrollment_id}' not found.")

        enr_dict = dict(enr)
        if enr_dict["status"] != "active":
            raise ValueError(f"Enrollment '{enrollment_id}' is currently {enr_dict['status']}.")

        metric_name = key_metric_name or enr_dict.get("trial_metric") or "key_metric"
        direction = (enr_dict.get("improvement_direction") or "decrease").lower()
        threshold_weeks = enr_dict.get("improvement_threshold_weeks") or 2

        # 2. Determine week number & previous report value
        cursor.execute("""
        SELECT * FROM trial_progress_reports
        WHERE enrollment_id = ?
        ORDER BY week_number DESC;
        """, (enrollment_id,))
        reports = [dict(r) for r in cursor.fetchall()]

        week_number = len(reports) + 1

        if reports:
            prev_value = reports[0]["key_metric_value"]
            baseline_val = reports[-1]["key_metric_value"]
        else:
            prev_value = enr_dict.get("baseline_metric_value") if enr_dict.get("baseline_metric_value") is not None else key_metric_value
            baseline_val = prev_value

        comp_previous = key_metric_value - prev_value
        comp_baseline = key_metric_value - baseline_val

        # 3. Determine if metric is improving
        if direction == "decrease":
            is_improving = key_metric_value < prev_value
        else:  # "increase"
            is_improving = key_metric_value > prev_value

        # 4. Save progress report
        prog_id = f"prog-{uuid.uuid4()}"
        cursor.execute("""
        INSERT INTO trial_progress_reports (
            id, enrollment_id, report_id, week_number, upload_date,
            key_metric_name, key_metric_value, comparison_to_previous, comparison_to_baseline,
            is_improving, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            prog_id, enrollment_id, report_id, week_number, today_str,
            metric_name, key_metric_value, comp_previous, comp_baseline,
            1 if is_improving else 0, notes or f"Week {week_number} Progress Upload"
        ))

        # 5. Update enrollment current value & reset missed_week flag
        cursor.execute("""
        UPDATE trial_enrollments
        SET current_metric_value = ?,
            next_expected_report_date = ?,
            missed_week = 0,
            missed_since_date = NULL
        WHERE enrollment_id = ?;
        """, (key_metric_value, next_due_str, enrollment_id))

        conn.commit()

        # 6. Check for N consecutive non-improving weeks
        all_updated_reports = reports
        all_updated_reports.insert(0, {"is_improving": 1 if is_improving else 0, "week_number": week_number})

        consecutive_non_improving = 0
        for r in all_updated_reports:
            if not r["is_improving"]:
                consecutive_non_improving += 1
            else:
                break

        threshold_reached = consecutive_non_improving >= threshold_weeks

        if threshold_reached:
            feedback_message = f"No improvement - dosage may not be suitable for this patient ({consecutive_non_improving} consecutive weeks without progress)."
        elif is_improving:
            feedback_message = "YES, it's working"
        else:
            feedback_message = "Stable - continuation monitored."

        return {
            "success": True,
            "enrollment_id": enrollment_id,
            "week_number": week_number,
            "key_metric_name": metric_name,
            "key_metric_value": key_metric_value,
            "is_improving": is_improving,
            "consecutive_non_improving_weeks": consecutive_non_improving,
            "threshold_reached": threshold_reached,
            "feedback_message": feedback_message,
            "next_expected_report_date": next_due_str
        }


def discontinue_enrollment(enrollment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """
    Discontinue an enrollment without deleting any historical data.
    """
    init_db()
    discontinue_reason = reason or "no_improvement_after_N_weeks"
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE trial_enrollments
        SET status = 'discontinued', discontinued_reason = ?
        WHERE enrollment_id = ?;
        """, (discontinue_reason, enrollment_id))
        conn.commit()

        cursor.execute("SELECT * FROM trial_enrollments WHERE enrollment_id = ?;", (enrollment_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Enrollment '{enrollment_id}' not found.")
        return dict(row)


def get_trial_cohort(trial_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all enrolled patients for a trial, their current status, week number, trend, and history.
    """
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT key_metric_name FROM trials WHERE id = ?;", (trial_id,))
        t_row = cursor.fetchone()
        trial_metric = t_row["key_metric_name"] if t_row and t_row["key_metric_name"] else "key_metric"

        cursor.execute("""
        SELECT e.*, p.mrn_synthetic, p.age, p.gender, p.primary_diagnosis
        FROM trial_enrollments e
        JOIN patients p ON e.patient_id = p.id
        WHERE e.trial_id = ?
        ORDER BY e.created_at DESC;
        """, (trial_id,))
        enrollments = cursor.fetchall()

        cohort: List[Dict[str, Any]] = []
        for enr in enrollments:
            e_dict = dict(enr)
            eid = e_dict["enrollment_id"]

            cursor.execute("""
            SELECT week_number, upload_date, key_metric_value, is_improving, notes
            FROM trial_progress_reports
            WHERE enrollment_id = ?
            ORDER BY week_number ASC;
            """, (eid,))
            rep_rows = cursor.fetchall()
            history = [dict(r) for r in rep_rows]

            current_week = history[-1]["week_number"] if history else 1
            latest_improving = bool(history[-1]["is_improving"]) if history else True

            # Calculate consecutive non-improving weeks
            consecutive_non_improving = 0
            for r in reversed(history):
                if not r["is_improving"]:
                    consecutive_non_improving += 1
                else:
                    break

            cohort.append({
                "enrollment_id": eid,
                "patient_id": e_dict["patient_id"],
                "mrn_synthetic": e_dict["mrn_synthetic"],
                "age": e_dict["age"],
                "gender": e_dict["gender"],
                "primary_diagnosis": e_dict["primary_diagnosis"],
                "status": e_dict["status"],
                "enrolled_date": e_dict["enrolled_date"],
                "week_number": current_week,
                "key_metric_name": trial_metric,
                "baseline_metric_value": e_dict.get("baseline_metric_value"),
                "current_metric_value": e_dict.get("current_metric_value"),
                "is_improving": latest_improving,
                "consecutive_non_improving_weeks": consecutive_non_improving,
                "missed_week": bool(e_dict.get("missed_week")),
                "next_expected_report_date": e_dict["next_expected_report_date"],
                "discontinued_reason": e_dict.get("discontinued_reason"),
                "history": history
            })

        return cohort


def check_and_alert_missed_weeks() -> Dict[str, Any]:
    """
    Scheduled check for active enrollments past due date.
    Flags missed_week=1, sends email alert once per detection period, and creates notification.
    """
    init_db()
    today_str = datetime.date.today().isoformat()
    now_iso = datetime.datetime.utcnow().isoformat()

    alerts_triggered = []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Query active enrollments past due date
        cursor.execute("""
        SELECT e.*, t.title as trial_title
        FROM trial_enrollments e
        JOIN trials t ON e.trial_id = t.id
        WHERE e.status = 'active' AND e.next_expected_report_date < ?;
        """, (today_str,))
        overdue_list = cursor.fetchall()

        for row in overdue_list:
            enr = dict(row)
            eid = enr["enrollment_id"]
            last_alert = enr.get("last_alert_sent_at")

            # Duplicate prevention check (allow initial alert, or follow-up after 3 days)
            should_send = False
            if not last_alert:
                should_send = True
            else:
                try:
                    last_dt = datetime.datetime.fromisoformat(last_alert.replace("Z", ""))
                    days_since = (datetime.datetime.utcnow() - last_dt).days
                    if days_since >= 3:
                        should_send = True
                except Exception:
                    should_send = True

            # Mark missed_week = 1
            cursor.execute("""
            UPDATE trial_enrollments
            SET missed_week = 1,
                missed_since_date = COALESCE(missed_since_date, ?)
            WHERE enrollment_id = ?;
            """, (enr["next_expected_report_date"], eid))

            if should_send:
                # Fetch total weeks to report current week number
                cursor.execute("SELECT COUNT(*) FROM trial_progress_reports WHERE enrollment_id = ?;", (eid,))
                week_num = cursor.fetchone()[0] + 1

                # Send email
                email_res = send_missed_week_alert_email(
                    enrollment_id=eid,
                    patient_id=enr["patient_id"],
                    trial_title=enr["trial_title"],
                    missed_week=week_num,
                    missed_since_date=enr["next_expected_report_date"]
                )

                # Store in coordinator_notifications table
                notif_id = f"notif-{uuid.uuid4()}"
                notif_msg = f"Missed Week {week_num} report for enrollment {eid} in trial '{enr['trial_title']}'. Next report was due on {enr['next_expected_report_date']}."
                cursor.execute("""
                INSERT INTO coordinator_notifications (
                    id, job_id, patient_id, trial_id, title, message, is_read, created_at
                ) VALUES (?, 'scheduled-missed-check', ?, ?, ?, ?, 0, ?);
                """, (
                    notif_id, enr["patient_id"], enr["trial_id"],
                    f"Missed Weekly Report: {eid}", notif_msg, now_iso
                ))

                # Update last_alert_sent_at
                cursor.execute("""
                UPDATE trial_enrollments
                SET last_alert_sent_at = ?
                WHERE enrollment_id = ?;
                """, (now_iso, eid))

                alerts_triggered.append({
                    "enrollment_id": eid,
                    "patient_id": enr["patient_id"],
                    "trial_title": enr["trial_title"],
                    "email_result": email_res
                })

        conn.commit()

    return {
        "checked_at": now_iso,
        "overdue_count": len(overdue_list),
        "alerts_triggered_count": len(alerts_triggered),
        "alerts": alerts_triggered
    }
