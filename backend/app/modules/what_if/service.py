import uuid
import json
import datetime
import logging
from typing import List, Dict, Any, Optional
from app.core.db import get_db_connection, init_db
from app.schemas.what_if import (
    WhatIfScenario,
    WhatIfModification,
    WhatIfSimulationResult,
    CriterionDelta,
    WhatIfFieldCategoryEnum
)
from app.modules.matching.service import run_patient_trial_matching
from app.schemas.matching import TrialMatchResult

logger = logging.getLogger("clinical_trial_assistant")


def create_what_if_scenario(scenario: WhatIfScenario) -> WhatIfScenario:
    """Create a new what-if scenario record."""
    scenario_id = scenario.scenario_id or f"scen-{uuid.uuid4()}"
    now_iso = datetime.datetime.utcnow().isoformat()

    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO what_if_scenarios (
            id, patient_id, trial_id, scenario_name, status, modifications_json, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            scenario_id, scenario.patient_id, scenario.trial_id, scenario.scenario_name,
            scenario.status, json.dumps([m.model_dump() for m in scenario.modifications]),
            scenario.created_by, now_iso, now_iso
        ))
        conn.commit()

    scenario.scenario_id = scenario_id
    scenario.created_at = now_iso
    return scenario


def run_what_if_simulation(scenario_id: str, user_email: str = "investigator@clinicaltrial.ai") -> WhatIfSimulationResult:
    """Run sandboxed hypothetical matching simulation without updating canonical patient records."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM what_if_scenarios WHERE id = ?;", (scenario_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"What-if scenario '{scenario_id}' not found.")

        scen_dict = dict(row)
        patient_id = scen_dict["patient_id"]
        trial_id = scen_dict["trial_id"]
        modifications = json.loads(scen_dict["modifications_json"]) if scen_dict.get("modifications_json") else []

    # 1. Evaluate baseline matching result (canonical data)
    baseline_match: TrialMatchResult = run_patient_trial_matching(patient_id, trial_id)

    # 2. In-memory sandbox modifications (strictly no DB writes to canonical tables)
    deltas: List[CriterionDelta] = []
    mod_map = {m["field_category"]: m for m in modifications}

    for crit in baseline_match.criterion_results:
        old_state = crit.status.value
        old_val = crit.patient_value or ""
        new_state = old_state
        new_val = old_val
        cause_field = ""
        explanation = "No hypothetical modification affected this criterion."

        # Simulate LAB modification (e.g. hypothetical ANC lab provided)
        if "lab" in mod_map and (crit.category == "laboratory" or "neutrophil" in crit.raw_text.lower() or "anc" in crit.raw_text.lower()):
            lab_mod = mod_map["lab"]
            cause_field = lab_mod["field_name"]
            hypo_val = float(lab_mod["hypothetical_value"]) if lab_mod["hypothetical_value"].replace('.', '', 1).isdigit() else 2.8
            new_val = f"Hypothetical Lab {lab_mod['field_name']}: {hypo_val} {lab_mod.get('raw_unit', '10*3/uL')}"
            
            if hypo_val >= 1.5:
                new_state = "PASS"
                explanation = f"Hypothetical lab {lab_mod['field_name']} = {hypo_val} meets clinical threshold (>= 1.5)."
            else:
                new_state = "FAIL"
                explanation = f"Hypothetical lab {lab_mod['field_name']} = {hypo_val} falls below clinical threshold (< 1.5)."

        # Simulate BIOMARKER modification (e.g. hypothetical positive EGFR)
        elif "biomarker" in mod_map and (crit.category == "biomarker" or "egfr" in crit.raw_text.lower()):
            bm_mod = mod_map["biomarker"]
            cause_field = bm_mod["field_name"]
            is_neg = bm_mod.get("is_negated", False)
            status_str = "NEGATIVE" if is_neg else "POSITIVE"
            new_val = f"Hypothetical Biomarker {bm_mod['field_name']}: {status_str}"

            if not is_neg:
                new_state = "PASS"
                explanation = f"Hypothetical positive biomarker {bm_mod['field_name']} satisfies protocol inclusion requirement."
            else:
                new_state = "FAIL"
                explanation = f"Hypothetical negative biomarker {bm_mod['field_name']} fails protocol requirement."

        # Simulate PRIOR TREATMENT modification
        elif "prior_treatment" in mod_map and (crit.category == "prior_treatment" or "treatment" in crit.raw_text.lower()):
            tx_mod = mod_map["prior_treatment"]
            cause_field = tx_mod["field_name"]
            new_val = f"Hypothetical Prior Treatment: {tx_mod['hypothetical_value']}"
            new_state = "PASS"
            explanation = f"Hypothetical prior treatment record {tx_mod['hypothetical_value']} evaluated."

        # Record delta if state changed
        if old_state != new_state:
            deltas.append(
                CriterionDelta(
                    criterion_id=crit.criterion_id,
                    criterion_text=crit.raw_text,
                    old_state=old_state,
                    new_state=new_state,
                    delta_explanation=explanation,
                    cause_field=cause_field
                )
            )

    # 3. Calculate simulated overall status and score
    orig_status = baseline_match.overall_status.value
    simulated_overall = "ELIGIBLE_FOR_REVIEW" if len(deltas) > 0 and any(d.new_state == "PASS" for d in deltas) else orig_status
    simulated_score = min(100.0, baseline_match.match_score + (30.0 if len(deltas) > 0 else 0.0))

    now_iso = datetime.datetime.utcnow().isoformat()
    audit_id = f"audit-whatif-{uuid.uuid4()}"

    # 4. Save audit log record
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO what_if_audit_logs (
            id, scenario_id, patient_id, trial_id, original_overall_status, simulated_overall_status,
            original_score, simulated_score, deltas_json, executed_by, executed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            audit_id, scenario_id, patient_id, trial_id, orig_status,
            simulated_overall, baseline_match.match_score, simulated_score,
            json.dumps([d.model_dump() for d in deltas]), user_email, now_iso
        ))
        conn.commit()

    return WhatIfSimulationResult(
        scenario_id=scenario_id,
        patient_id=patient_id,
        trial_id=trial_id,
        original_overall_status=orig_status,
        simulated_overall_status=simulated_overall,
        original_score=baseline_match.match_score,
        simulated_score=simulated_score,
        criteria_deltas=deltas,
        audit_event_id=audit_id
    )


def duplicate_scenario(scenario_id: str) -> WhatIfScenario:
    """Duplicate an existing scenario record."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM what_if_scenarios WHERE id = ?;", (scenario_id,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Scenario '{scenario_id}' not found.")

        d = dict(row)
        new_id = f"scen-{uuid.uuid4()}"
        new_name = f"Copy of {d['scenario_name']}"
        now_iso = datetime.datetime.utcnow().isoformat()

        cursor.execute("""
        INSERT INTO what_if_scenarios (
            id, patient_id, trial_id, scenario_name, status, modifications_json, created_by, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, ?);
        """, (
            new_id, d["patient_id"], d["trial_id"], new_name, d["modifications_json"],
            d["created_by"], now_iso, now_iso
        ))
        conn.commit()

        mods = [WhatIfModification(**m) for m in json.loads(d["modifications_json"])]
        return WhatIfScenario(
            scenario_id=new_id,
            patient_id=d["patient_id"],
            trial_id=d["trial_id"],
            scenario_name=new_name,
            status="active",
            modifications=mods,
            created_by=d["created_by"],
            created_at=now_iso
        )


def archive_scenario(scenario_id: str) -> Dict[str, Any]:
    """Archive a what-if scenario record."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE what_if_scenarios SET status = 'archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (scenario_id,))
        conn.commit()
        return {"scenario_id": scenario_id, "status": "archived"}


def get_patient_scenarios(patient_id: str) -> List[WhatIfScenario]:
    """Get active and archived what-if scenarios for patient."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM what_if_scenarios WHERE patient_id = ? ORDER BY created_at DESC;", (patient_id,))
        rows = cursor.fetchall()
        
        scenarios: List[WhatIfScenario] = []
        for r in rows:
            d = dict(r)
            mods = [WhatIfModification(**m) for m in json.loads(d["modifications_json"])] if d.get("modifications_json") else []
            scenarios.append(
                WhatIfScenario(
                    scenario_id=d["id"],
                    patient_id=d["patient_id"],
                    trial_id=d["trial_id"],
                    scenario_name=d["scenario_name"],
                    status=d["status"],
                    modifications=mods,
                    created_by=d["created_by"],
                    created_at=d["created_at"]
                )
            )
        return scenarios
