import os
import sys
import datetime
import logging

# Ensure app path is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.db import init_db, get_db_connection
from app.modules.enrollment import service as enrollment_service
from app.modules.matching.service import run_patient_trial_matching
from app.core.email_service import send_missed_week_alert_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_phase7")

def run_phase7_tests():
    logger.info("=== STARTING PHASE 7 VERIFICATION SUITE ===")
    init_db()

    # 1. Setup Test Patient and Disease-Agnostic Trials
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Ensure test patient exists
        patient_id = "test-patient-phase7"
        cursor.execute("SELECT * FROM patients WHERE id = ?;", (patient_id,))
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO patients (id, mrn_synthetic, age, gender, primary_diagnosis, created_at)
            VALUES (?, 'MRN-PHASE7-001', 54, 'FEMALE', 'Type 2 Diabetes Mellitus', CURRENT_TIMESTAMP);
            """, (patient_id,))

        # Trial 1: Diabetes Protocol (HbA1c decrease)
        trial_1_id = "t-phase7-diab"
        cursor.execute("DELETE FROM trials WHERE id = ?;", (trial_1_id,))
        cursor.execute("""
        INSERT INTO trials (
            id, nct_id, title, phase, recruitment_status, conditions,
            key_metric_name, improvement_direction, improvement_threshold_weeks,
            min_age, max_age, gender, created_at
        ) VALUES (
            ?, 'NCT09990001', 'Phase 3 Diabetes Oral Efficacy Trial', 'Phase 3', 'RECRUITING',
            'Type 2 Diabetes', 'HbA1c', 'decrease', 2, 18, 75, 'ALL', CURRENT_TIMESTAMP
        );
        """, (trial_1_id,))

        # Trial 2: Oncology Protocol (tumor_size decrease)
        trial_2_id = "t-phase7-onco"
        cursor.execute("DELETE FROM trials WHERE id = ?;", (trial_2_id,))
        cursor.execute("""
        INSERT INTO trials (
            id, nct_id, title, phase, recruitment_status, conditions,
            key_metric_name, improvement_direction, improvement_threshold_weeks,
            min_age, max_age, gender, created_at
        ) VALUES (
            ?, 'NCT09990002', 'Phase 3 Solid Tumor Targeted Therapy', 'Phase 3', 'RECRUITING',
            'Solid Tumor', 'tumor_size', 'decrease', 2, 18, 80, 'ALL', CURRENT_TIMESTAMP
        );
        """, (trial_2_id,))

        # Clean up existing test enrollments
        cursor.execute("DELETE FROM trial_enrollments WHERE patient_id = ?;", (patient_id,))
        cursor.execute("DELETE FROM trial_progress_reports WHERE enrollment_id LIKE 'NCT0999%';")
        conn.commit()

    logger.info("[TEST 1 PASSED] Test Patient and Multi-Disease Trial Protocols created.")

    # 2. Test Eligibility Screening
    screen_res = enrollment_service.screen_patient_for_trial(patient_id, trial_1_id)
    assert "is_eligible" in screen_res
    logger.info(f"[TEST 2 PASSED] Screening Result: Eligible={screen_res['is_eligible']} ({screen_res['message']})")

    # 3. Test Confirm Enrollment & Unique ID Generation
    enr_res = enrollment_service.confirm_trial_enrollment(
        patient_id=patient_id,
        trial_id=trial_1_id,
        baseline_metric_value=8.2
    )
    enrollment_id = enr_res["enrollment_id"]
    assert "NCT09990001-2026-" in enrollment_id
    assert enr_res["status"] == "active"
    logger.info(f"[TEST 3 PASSED] Confirmed Enrollment. Generated Unique ID: '{enrollment_id}'")

    # 4. Test Weekly Progress Reports & Responder Logic
    # Week 1: 7.8 (Decreased from 8.2 -> Improving!)
    prog1 = enrollment_service.upload_weekly_progress_report(
        enrollment_id=enrollment_id,
        key_metric_value=7.8,
        notes="Week 1 - HbA1c reduced"
    )
    assert prog1["is_improving"] == True
    assert prog1["feedback_message"] == "YES, it's working"
    logger.info(f"[TEST 4a PASSED] Week 1 progress upload: {prog1['feedback_message']}")

    # Week 2: 8.0 (Increased -> Non-improving #1)
    prog2 = enrollment_service.upload_weekly_progress_report(
        enrollment_id=enrollment_id,
        key_metric_value=8.0,
        notes="Week 2 - Slight increase"
    )
    assert prog2["is_improving"] == False

    # Week 3: 8.3 (Increased -> Non-improving #2 => Reaches threshold 2!)
    prog3 = enrollment_service.upload_weekly_progress_report(
        enrollment_id=enrollment_id,
        key_metric_value=8.3,
        notes="Week 3 - No improvement"
    )
    assert prog3["threshold_reached"] == True
    assert "No improvement" in prog3["feedback_message"]
    logger.info(f"[TEST 4b PASSED] Week 3 Non-Responder Flagged: {prog3['feedback_message']}")

    # 5. Test Non-Responder Discontinuation (Archiving without deletion)
    disc_res = enrollment_service.discontinue_enrollment(enrollment_id, reason="no_improvement_after_N_weeks")
    assert disc_res["status"] == "discontinued"
    assert disc_res["discontinued_reason"] == "no_improvement_after_N_weeks"

    # Verify history retained in DB
    cohort = enrollment_service.get_trial_cohort(trial_1_id)
    assert len(cohort) >= 1
    assert len(cohort[0]["history"]) >= 3
    logger.info("[TEST 5 PASSED] Discontinued non-responder patient. All 3 weekly progress reports retained in DB.")

    # 6. Test Missed-Week Detection & Email Alerts
    # Create second active enrollment past due date
    enr_res2 = enrollment_service.confirm_trial_enrollment(
        patient_id=patient_id,
        trial_id=trial_2_id,
        baseline_metric_value=4.5
    )
    enrollment_id2 = enr_res2["enrollment_id"]

    yesterday_str = (datetime.date.today() - datetime.timedelta(days=2)).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE trial_enrollments
        SET next_expected_report_date = ?
        WHERE enrollment_id = ?;
        """, (yesterday_str, enrollment_id2))
        conn.commit()

    # Trigger scheduled missed-week check
    check_res = enrollment_service.check_and_alert_missed_weeks()
    assert check_res["overdue_count"] >= 1
    assert check_res["alerts_triggered_count"] >= 1
    logger.info(f"[TEST 6a PASSED] Scheduled Missed-Week Check detected overdue enrollment {enrollment_id2} and dispatched email alert.")

    # Test Duplicate Prevention (Re-running immediately should not re-send email)
    check_res2 = enrollment_service.check_and_alert_missed_weeks()
    assert check_res2["alerts_triggered_count"] == 0
    logger.info("[TEST 6b PASSED] Duplicate alert prevention verified (0 alerts triggered on immediate re-run).")

    logger.info("=== ALL PHASE 7 TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    run_phase7_tests()
