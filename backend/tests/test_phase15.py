import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.feedback.service import (
    submit_reviewer_feedback,
    get_disagreement_analytics,
    export_deidentified_evaluations
)
from app.schemas.feedback import (
    ReviewerFeedbackSubmission,
    DisagreementCategoryEnum
)

client = TestClient(app)

TEST_PATIENT_ID = "13131313-1313-1313-1313-131313131313"
TEST_TRIAL_ID = "t-phase15-trial"


@pytest.fixture(autouse=True)
def setup_phase15_test_data():
    """Setup test patient record."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-1313', 60, 'Female');", (TEST_PATIENT_ID,))
        conn.commit()


def test_1_agreement_feedback_submission():
    """Verify submitting agreement feedback stores AGREE status."""
    sub = ReviewerFeedbackSubmission(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        criterion_id="crit-age",
        ai_decision="PASS",
        human_decision="PASS",
        reviewer_id="dr_test_phase15"
    )
    rec = submit_reviewer_feedback(sub)
    assert rec.agreement_status == "AGREE"
    assert rec.error_type == "none"


def test_2_disagreement_override_false_pass_classification():
    """Verify disagreement override classifies false-pass (AI=PASS, Human=FAIL)."""
    sub = ReviewerFeedbackSubmission(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        criterion_id="crit-anc",
        ai_decision="PASS",
        human_decision="FAIL",
        disagreement_category=DisagreementCategoryEnum.EXTRACTION_ERROR,
        override_reason="AI extracted wrong lab column value 2.8 instead of true ANC 0.8.",
        reviewer_id="dr_test_phase15"
    )
    rec = submit_reviewer_feedback(sub)
    assert rec.agreement_status == "DISAGREE"
    assert rec.error_type == "false_pass"
    assert rec.disagreement_category == "extraction_error"


def test_3_disagreement_override_false_fail_classification():
    """Verify disagreement override classifies false-fail (AI=FAIL, Human=PASS)."""
    sub = ReviewerFeedbackSubmission(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        criterion_id="crit-egfr",
        ai_decision="FAIL",
        human_decision="PASS",
        disagreement_category=DisagreementCategoryEnum.NEGATION_ERROR,
        override_reason="AI misread negative negation tag for EGFR Exon 19 Deletion.",
        reviewer_id="dr_test_phase15"
    )
    rec = submit_reviewer_feedback(sub)
    assert rec.agreement_status == "DISAGREE"
    assert rec.error_type == "false_fail"


def test_4_mandatory_override_rationale_enforcement():
    """Verify missing override rationale raises explicit ValueError."""
    sub = ReviewerFeedbackSubmission(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        criterion_id="crit-anc",
        ai_decision="PASS",
        human_decision="FAIL",
        override_reason="",
        reviewer_id="dr_test_phase15"
    )
    with pytest.raises(ValueError, match="Mandatory override rationale"):
        submit_reviewer_feedback(sub)


def test_5_analytics_metrics_computation():
    """Verify disagreement analytics calculates rates and category breakdown."""
    analytics = get_disagreement_analytics(TEST_TRIAL_ID)
    assert analytics.total_evaluations >= 3
    assert analytics.agree_count >= 1
    assert analytics.disagree_count >= 2
    assert analytics.false_pass_count >= 1
    assert analytics.false_fail_count >= 1
    assert "extraction_error" in analytics.category_breakdown


def test_6_deidentified_export():
    """Verify export de-identifies patient IDs using hashes."""
    exported = export_deidentified_evaluations()
    assert len(exported) > 0
    rec = exported[0]
    assert "anon_patient_id" in rec
    assert rec["anon_patient_id"].startswith("anon-")
    assert TEST_PATIENT_ID not in rec["anon_patient_id"]
