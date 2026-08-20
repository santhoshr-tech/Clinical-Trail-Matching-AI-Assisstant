"""End-to-end audit of the trial matching pipeline state."""
import sqlite3
import json
import asyncio
import httpx

DB_PATH = "local_prototype.db"

def q(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

print("=" * 70)
print("1. PATIENTS IN DB")
print("=" * 70)
patients = q("SELECT id, mrn, full_name, age, gender FROM patients LIMIT 5")
for p in patients:
    print(f"  {p['mrn']} | {p['id']} | {p['full_name']} | age={p['age']} | gender={p['gender']}")

print()
print("=" * 70)
print("2. EXTRACTED FACTS FOR MRN-01 (patient_conditions / extracted_facts)")
print("=" * 70)

# Get patient id for MRN-01
mrn01 = q("SELECT id FROM patients WHERE mrn = 'MRN-01'")
pid = mrn01[0]["id"] if mrn01 else None
print(f"  MRN-01 patient_id = {pid}")

if pid:
    conds = q("SELECT fact_type, raw_value, normalized_value FROM extracted_facts WHERE patient_id = ? LIMIT 10", (pid,))
    print(f"  extracted_facts count: {len(conds)}")
    for c in conds:
        print(f"    [{c['fact_type']}] {c['raw_value']} → {c['normalized_value']}")

    # Also check patient_conditions / patient_biomarkers
    pc = q("SELECT normalized_value, stage, verification_status FROM patient_conditions WHERE patient_id = ? LIMIT 5", (pid,))
    print(f"  patient_conditions count: {len(pc)}")
    for c in pc:
        print(f"    {c['normalized_value']} | stage={c.get('stage')} | status={c['verification_status']}")

    pl = q("SELECT normalized_value, numeric_value, unit FROM patient_labs WHERE patient_id = ? LIMIT 5", (pid,))
    print(f"  patient_labs count: {len(pl)}")

    pb = q("SELECT biomarker_name, normalized_value, status_value FROM patient_biomarkers WHERE patient_id = ? LIMIT 5", (pid,))
    print(f"  patient_biomarkers count: {len(pb)}")

print()
print("=" * 70)
print("3. TRIALS IN LOCAL DB")
print("=" * 70)
trials = q("SELECT id, nct_id, title, recruitment_status FROM trials LIMIT 5")
print(f"  Total trials in DB: {len(trials)}")
for t in trials:
    print(f"  {t['nct_id']} | {t['id']} | {t['title'][:60]} | {t['recruitment_status']}")

print()
print("=" * 70)
print("4. TRIAL CRITERIA (approved)")
print("=" * 70)
criteria = q("SELECT trial_id, criterion_type, category, operator, value_primary, approval_status FROM trial_criteria LIMIT 10")
print(f"  Total criteria in DB: {len(criteria)}")
for c in criteria:
    print(f"  [{c['approval_status']}] {c['trial_id']} | {c['criterion_type']} | {c['category']} | {c['operator']} {c['value_primary'] or ''}")

approved = q("SELECT id FROM trial_criteria WHERE approval_status = 'approved'")
print(f"  Approved criteria: {len(approved)}")

print()
print("=" * 70)
print("5. PAST MATCH RESULTS")
print("=" * 70)
matches = q("SELECT patient_id, trial_id, overall_status, match_score, total_criteria, passed_count, failed_count FROM patient_trial_matches LIMIT 5")
print(f"  Total match records: {len(matches)}")
for m in matches:
    print(f"  {m['patient_id']} vs {m['trial_id']} → {m['overall_status']} score={m['match_score']:.1f}% ({m['passed_count']}/{m['total_criteria']} pass)")

print()
print("=" * 70)
print("6. LIVE API TEST: ClinicalTrials.gov")
print("=" * 70)
import urllib.request, urllib.parse
try:
    url = "https://clinicaltrials.gov/api/v2/studies?query.term=osteoporosis&pageSize=3"
    req = urllib.request.Request(url, headers={"User-Agent": "ClinicalTrialResearchAssistant/1.0"})
    with urllib.request.urlopen(req, timeout=6) as r:
        data = json.loads(r.read().decode())
        studies = data.get("studies", [])
        print(f"  Live API returned {len(studies)} results for 'osteoporosis'")
        for s in studies:
            p = s.get("protocolSection", {})
            title = p.get("identificationModule", {}).get("briefTitle", "?")[:60]
            nct = p.get("identificationModule", {}).get("nctId", "?")
            print(f"    {nct}: {title}")
except Exception as e:
    print(f"  Live API FAILED: {e}")
