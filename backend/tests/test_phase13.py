import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import init_db, get_db_connection
from app.modules.what_if.service import (
    create_what_if_scenario,
    run_what_if_simulation,
    duplicate_scenario,
    archive_scenario
)
from app.schemas.what_if import (
    WhatIfScenario,
    WhatIfModification,
    WhatIfFieldCategoryEnum
)
from app.modules.criteria.service import parse_protocol_text_into_criteria, store_parsed_criteria, set_criterion_approval
from app.schemas.criteria import ApprovalStatusEnum

client = TestClient(app)

TEST_PATIENT_ID = "10101010-1010-1010-1010-101010101010"
TEST_TRIAL_ID = "t-phase13-trial"


@pytest.fixture(autouse=True)
def setup_phase13_test_data():
    """Setup baseline patient record and trial criteria for what-if testing."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM what_if_scenarios WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM what_if_audit_logs WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM trial_criteria WHERE trial_id = ?;", (TEST_TRIAL_ID,))
        cursor.execute("DELETE FROM patient_labs WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("DELETE FROM patient_biomarkers WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        cursor.execute("INSERT OR REPLACE INTO patients (id, mrn_synthetic, age, gender) VALUES (?, 'MRN-1010', 62, 'Female');", (TEST_PATIENT_ID,))
        conn.commit()

    protocol_text = """
    Inclusion Criteria:
    1. Absolute Neutrophil Count (ANC) >= 1.5 10*3/uL.
    2. Confirmed EGFR Exon 19 Deletion Positive.
    """
    parsed = parse_protocol_text_into_criteria(TEST_TRIAL_ID, protocol_text)
    stored = store_parsed_criteria(TEST_TRIAL_ID, parsed)
    for item in stored:
        set_criterion_approval(item["id"], ApprovalStatusEnum.APPROVED, "principal_investigator")


def test_1_missing_lab_scenario_simulation():
    """Verify hypothetically adding missing lab turns UNKNOWN/FAIL to PASS in simulation."""
    scen = WhatIfScenario(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        scenario_name="Hypothetical Normal ANC Lab",
        modifications=[
            WhatIfModification(
                field_category=WhatIfFieldCategoryEnum.LAB,
                field_name="Absolute Neutrophil Count",
                hypothetical_value="2.8",
                raw_unit="10*3/uL"
            )
        ]
    )
    scen = create_what_if_scenario(scen)
    
    sim_res = run_what_if_simulation(scen.scenario_id, "investigator@clinicaltrial.ai")
    assert sim_res.scenario_id == scen.scenario_id
    assert len(sim_res.criteria_deltas) >= 1
    
    lab_delta = [d for d in sim_res.criteria_deltas if "Neutrophil" in d.criterion_text or "ANC" in d.cause_field][0]
    assert lab_delta.new_state == "PASS"
    assert "meets clinical threshold" in lab_delta.delta_explanation


def test_2_biomarker_scenario_simulation():
    """Verify hypothetically adding positive biomarker turns state to PASS in simulation."""
    scen = WhatIfScenario(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        scenario_name="Hypothetical EGFR Mutation Positive",
        modifications=[
            WhatIfModification(
                field_category=WhatIfFieldCategoryEnum.BIOMARKER,
                field_name="EGFR Exon 19 Deletion",
                hypothetical_value="POSITIVE",
                is_negated=False
            )
        ]
    )
    scen = create_what_if_scenario(scen)

    sim_res = run_what_if_simulation(scen.scenario_id, "investigator@clinicaltrial.ai")
    bm_delta = [d for d in sim_res.criteria_deltas if "EGFR" in d.criterion_text or "EGFR" in d.cause_field][0]
    assert bm_delta.new_state == "PASS"


def test_3_prior_treatment_scenario_simulation():
    """Verify prior treatment modification simulation."""
    scen = WhatIfScenario(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        scenario_name="Hypothetical Chemotherapy Treatment Line",
        modifications=[
            WhatIfModification(
                field_category=WhatIfFieldCategoryEnum.PRIOR_TREATMENT,
                field_name="Cisplatin Chemotherapy",
                hypothetical_value="1 Line Prior Chemotherapy"
            )
        ]
    )
    scen = create_what_if_scenario(scen)
    sim_res = run_what_if_simulation(scen.scenario_id, "investigator@clinicaltrial.ai")
    assert sim_res.audit_event_id is not None


def test_4_canonical_data_non_mutation_guarantee():
    """Verify that hypothetical simulations do NOT mutate canonical patient database records."""
    # Count labs before simulation
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_labs WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        lab_count_before = cursor.fetchone()[0]

    scen = WhatIfScenario(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        scenario_name="Non Mutation Check",
        modifications=[
            WhatIfModification(field_category=WhatIfFieldCategoryEnum.LAB, field_name="ANC", hypothetical_value="5.0")
        ]
    )
    scen = create_what_if_scenario(scen)
    run_what_if_simulation(scen.scenario_id)

    # Count labs after simulation
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM patient_labs WHERE patient_id = ?;", (TEST_PATIENT_ID,))
        lab_count_after = cursor.fetchone()[0]

    assert lab_count_before == lab_count_after == 0


def test_5_scenario_duplication_and_archival():
    """Verify duplicating and archiving scenario records."""
    scen = WhatIfScenario(
        patient_id=TEST_PATIENT_ID,
        trial_id=TEST_TRIAL_ID,
        scenario_name="Original Scenario",
        modifications=[WhatIfModification(field_category=WhatIfFieldCategoryEnum.LAB, field_name="ANC", hypothetical_value="2.0")]
    )
    scen = create_what_if_scenario(scen)

    duplicated = duplicate_scenario(scen.scenario_id)
    assert duplicated.scenario_name == "Copy of Original Scenario"
    assert duplicated.scenario_id != scen.scenario_id

    archived = archive_scenario(scen.scenario_id)
    assert archived["status"] == "archived"
