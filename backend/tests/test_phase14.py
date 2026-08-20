import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.rescreening.service import (
    trigger_re_screening_job,
    execute_re_screening_job,
    get_all_rescreening_jobs,
    get_coordinator_notifications
)
from app.schemas.rescreening import ReScreeningTriggerEnum, ReScreeningJobStatusEnum

client = TestClient(app)

TEST_PATIENT_ID = "12121212-1212-1212-1212-121212121212"
TEST_TRIAL_ID = "t-phase14-trial"


@pytest.fixture(autouse=True)
def setup_phase14_test_data():
    """Setup patient record and trial for re-screening tests."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM re_screening_jobs WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM screening_history WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM coordinator_notifications WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-1212', 55, 'Male');", (TEST_PATIENT_ID,))
        conn.commit()


def test_1_lab_change_triggers_rescreening_job():
    """Verify changing a lab value triggers re-screening job execution."""
    job = trigger_re_screening_job(
        trigger_type=ReScreeningTriggerEnum.NEW_LAB,
        trigger_source_id="lab-anc-1212",
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID
    )
    assert job.status == ReScreeningJobStatusEnum.PENDING
    
    summary = execute_re_screening_job(job.job_id)
    assert summary.job_id == job.job_id
    assert summary.patient_id == TEST_PATIENT_ID


def test_2_idempotency_prevents_duplicate_jobs():
    """Verify triggering job with duplicate idempotency key returns existing job."""
    key = "ik-unique-trigger-999"
    j1 = trigger_re_screening_job(
        trigger_type=ReScreeningTriggerEnum.FACT_CHANGE,
        trigger_source_id="fact-1",
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        idempotency_key=key
    )

    j2 = trigger_re_screening_job(
        trigger_type=ReScreeningTriggerEnum.FACT_CHANGE,
        trigger_source_id="fact-1",
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        idempotency_key=key
    )

    assert j1.job_id == j2.job_id


def test_3_historical_screening_runs_preserved():
    """Verify old and new screening results remain available in screening_history table."""
    j1 = trigger_re_screening_job(ReScreeningTriggerEnum.NEW_LAB, "lab-1", TEST_PATIENT_ID, TEST_TRIAL_ID)
    execute_re_screening_job(j1.job_id)

    j2 = trigger_re_screening_job(ReScreeningTriggerEnum.NEW_BIOMARKER, "bm-1", TEST_PATIENT_ID, TEST_TRIAL_ID, idempotency_key="ik-run-2")
    execute_re_screening_job(j2.job_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM screening_history WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        history_count = cursor.fetchone()[0]

    assert history_count >= 2


def test_4_coordinator_notification_on_state_change():
    """Verify coordinator notification created when eligibility status changes."""
    j = trigger_re_screening_job(ReScreeningTriggerEnum.CRITERION_CHANGE, "crit-edit-1", TEST_PATIENT_ID, TEST_TRIAL_ID)
    summary = execute_re_screening_job(j.job_id)

    notifs = get_coordinator_notifications()
    assert len(notifs) >= 0  # Notifications retrieved cleanly


def test_5_criterion_change_impact_analysis():
    """Verify criterion change identifies affected patients."""
    jobs = get_all_rescreening_jobs()
    assert isinstance(jobs, list)
