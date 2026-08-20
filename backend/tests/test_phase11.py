import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.conflicts.service import (
    create_clinical_conflict_case,
    resolve_clinical_conflict,
    get_conflict_analytics
)
from app.schemas.conflicts import (
    SourceFactDetail,
    ConflictResolutionRequest,
    ConflictResolutionChoiceEnum,
    ConflictCategoryEnum
)
from app.modules.matching.service import run_patient_trial_matching
from app.modules.criteria.service import parse_protocol_text_into_criteria, store_parsed_criteria, set_criterion_approval
from app.schemas.criteria import ApprovalStatusEnum

client = TestClient(app)

headers = {
    "X-User-Email": "investigator@clinicaltrial.ai",
    "X-User-Role": "principal_investigator"
}

TEST_PATIENT_ID = "88888888-8888-8888-8888-888888888888"
TEST_TRIAL_ID = "t-phase11-trial"


@pytest.fixture(autouse=True)
def setup_phase11_test_data():
    """Setup patient record and trial criteria for conflict resolution testing."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fact_conflicts WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM conflict_resolutions_audit WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM trial_criteria WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        cursor.execute("DELETE FROM patient_trial_matches WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-8888', 55, 'Female');", (TEST_PATIENT_ID,))
        conn.commit()

    protocol_text = """
    Inclusion Criteria:
    1. Age >= 18 years old.
    2. Confirmed EGFR Exon 19 Deletion Positive.
    """
    parsed = parse_protocol_text_into_criteria(TEST_TRIAL_ID, protocol_text)
    stored = store_parsed_criteria(TEST_TRIAL_ID, parsed)
    for item in stored:
        set_criterion_approval(item["id"], ApprovalStatusEnum.APPROVED, "principal_investigator")


def test_1_conflicting_biomarker_case():
    """Test creating and resolving conflicting biomarker case."""
    sa = SourceFactDetail(
        fact_id="f-bm-1", file_name="pathology_biopsy.pdf", document_date="2026-06-10",
        reliability_score=0.95, raw_value="Biopsy 1: EGFR Exon 19 Deletion Positive",
        normalized_value="EGFR Mutation: POSITIVE (MUTATED)", is_negated=False
    )
    sb = SourceFactDetail(
        fact_id="f-bm-2", file_name="liquid_ctdna.pdf", document_date="2026-07-15",
        reliability_score=0.88, raw_value="Liquid CtDNA: EGFR Wild-Type Negative",
        normalized_value="EGFR Mutation: NEGATIVE (WILD_TYPE)", is_negated=True
    )

    case = create_clinical_conflict_case(
        TEST_PATIENT_ID, ConflictCategoryEnum.BIOMARKER,
        "Contradictory tissue vs liquid biopsy EGFR mutation result", sa, sb
    )
    assert case.conflict_id is not None
    assert case.status == "unresolved"

    # Resolve by accepting Source A (Tissue Biopsy)
    req = ConflictResolutionRequest(
        conflict_id=case.conflict_id,
        resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_A,
        resolution_reason="Tissue biopsy from tissue specimen is gold standard over liquid ctDNA."
    )
    res = resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")
    
    assert res["status"] == "resolved_accept_a"
    assert "POSITIVE" in res["resolved_value"]
    assert res["rescreening_triggered"] is True


def test_2_conflicting_lab_case():
    """Test resolving conflicting lab threshold values."""
    sa = SourceFactDetail(
        fact_id="f-lab-1", file_name="cbc_lab_august.pdf", document_date="2026-08-01",
        reliability_score=0.96, raw_value="ANC 2.8 10*3/uL",
        normalized_value="Absolute Neutrophil Count: 2.8 10*3/uL", is_negated=False
    )
    sb = SourceFactDetail(
        fact_id="f-lab-2", file_name="cbc_lab_prior.pdf", document_date="2026-07-01",
        reliability_score=0.85, raw_value="ANC 0.8 10*3/uL",
        normalized_value="Absolute Neutrophil Count: 0.8 10*3/uL", is_negated=False
    )

    case = create_clinical_conflict_case(
        TEST_PATIENT_ID, ConflictCategoryEnum.LAB,
        "Contradictory lab report values for ANC", sa, sb
    )

    req = ConflictResolutionRequest(
        conflict_id=case.conflict_id,
        resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_A,
        resolution_reason="Most recent lab report from August confirms recovered ANC count."
    )
    res = resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")
    assert res["status"] == "resolved_accept_a"


def test_3_conflicting_diagnosis_stage_case():
    """Test resolving conflicting disease stage diagnoses."""
    sa = SourceFactDetail(
        fact_id="f-stage-1", file_name="pet_ct_scan.pdf", document_date="2026-06-20",
        reliability_score=0.94, raw_value="PET-CT confirms Stage IV NSCLC with bone metastases",
        normalized_value="Non-Small Cell Lung Cancer (Stage IV)", is_negated=False
    )
    sb = SourceFactDetail(
        fact_id="f-stage-2", file_name="initial_clinic_note.pdf", document_date="2026-05-10",
        reliability_score=0.80, raw_value="Initial staging Stage III NSCLC",
        normalized_value="Non-Small Cell Lung Cancer (Stage III)", is_negated=False
    )

    case = create_clinical_conflict_case(
        TEST_PATIENT_ID, ConflictCategoryEnum.DIAGNOSIS_STAGE,
        "Stage progression conflict between Stage III vs Stage IV", sa, sb
    )

    req = ConflictResolutionRequest(
        conflict_id=case.conflict_id,
        resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_A,
        resolution_reason="Recent PET-CT confirms metastatic stage IV progression."
    )
    res = resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")
    assert res["status"] == "resolved_accept_a"


def test_4_conflicting_medication_case():
    """Test resolving conflicting medication records."""
    sa = SourceFactDetail(
        fact_id="f-med-1", file_name="pharmacy_dispense.pdf", document_date="2026-08-01",
        reliability_score=0.92, raw_value="Prednisone 20mg daily active",
        normalized_value="Prednisone 20mg", is_negated=False
    )
    sb = SourceFactDetail(
        fact_id="f-med-2", file_name="patient_interview.pdf", document_date="2026-08-05",
        reliability_score=0.88, raw_value="Patient discontinued steroids 2 weeks ago",
        normalized_value="Prednisone: DISCONTINUED", is_negated=True
    )

    case = create_clinical_conflict_case(
        TEST_PATIENT_ID, ConflictCategoryEnum.MEDICATION,
        "Active steroid vs discontinued steroid conflict", sa, sb
    )

    req = ConflictResolutionRequest(
        conflict_id=case.conflict_id,
        resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_B,
        resolution_reason="Patient interview confirms completed steroid taper 2 weeks ago."
    )
    res = resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")
    assert res["status"] == "resolved_accept_b"


def test_5_resolution_reason_mandatory_enforcement():
    """Verify missing resolution reason raises explicit error."""
    sa = SourceFactDetail(fact_id="f1", file_name="a.pdf", document_date="2026-08-01", raw_value="val A", normalized_value="A")
    sb = SourceFactDetail(fact_id="f2", file_name="b.pdf", document_date="2026-08-01", raw_value="val B", normalized_value="B")
    case = create_clinical_conflict_case(TEST_PATIENT_ID, ConflictCategoryEnum.BIOMARKER, "Test conflict", sa, sb)

    # Empty reason should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        req = ConflictResolutionRequest.model_construct(
            conflict_id=case.conflict_id,
            resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_A,
            resolution_reason=""
        )
        resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")
    
    assert "A resolution reason is mandatory" in str(exc_info.value)


def test_6_historical_values_preserved():
    """Verify that resolution does not delete or overwrite historical conflict rows."""
    sa = SourceFactDetail(fact_id="f1", file_name="a.pdf", document_date="2026-08-01", raw_value="val A", normalized_value="A")
    sb = SourceFactDetail(fact_id="f2", file_name="b.pdf", document_date="2026-08-01", raw_value="val B", normalized_value="B")
    case = create_clinical_conflict_case(TEST_PATIENT_ID, ConflictCategoryEnum.BIOMARKER, "Test preservation", sa, sb)

    req = ConflictResolutionRequest(
        conflict_id=case.conflict_id,
        resolution_choice=ConflictResolutionChoiceEnum.ACCEPT_A,
        resolution_reason="Resolution preserving audit trail."
    )
    resolve_clinical_conflict(req, "investigator@clinicaltrial.ai")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fact_conflicts WHERE id = ?;", (case.conflict_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["source_a_json"] is not None
        assert row["source_b_json"] is not None
        
        cursor.execute("SELECT * FROM conflict_resolutions_audit WHERE conflict_id = ?;", (case.conflict_id,))
        audit_row = cursor.fetchone()
        assert audit_row is not None
        assert audit_row["resolution_choice"] == "accept_a"
