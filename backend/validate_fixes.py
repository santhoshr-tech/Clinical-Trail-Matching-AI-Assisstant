import urllib.request, json

base = "http://127.0.0.1:8000/api/v1"
headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

def api_get(path):
    req = urllib.request.Request(base + path, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        base + path, data=body,
        headers={**headers, "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()}"}
    except Exception as e:
        return {"error": str(e)}

divider = "=" * 60

# ── VALIDATION 1: Criteria now all approved ────────────────────
print(f"\n{divider}")
print("VALIDATION 1: Approved criteria for NCT04500000")
print(divider)
import sqlite3
conn = sqlite3.connect("local_prototype.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute(
    "SELECT criterion_type, category, operator, approval_status, raw_text "
    "FROM trial_criteria WHERE trial_id='t-nct04500000' ORDER BY criterion_type, category"
)
rows = cur.fetchall()
approved = [r for r in rows if r["approval_status"] == "approved"]
pending  = [r for r in rows if r["approval_status"] == "pending"]
print(f"  Total: {len(rows)} | Approved: {len(approved)} | Pending: {len(pending)}")
print()
for r in rows:
    tick = "✓" if r["approval_status"] == "approved" else "✗"
    print(f"  [{tick}] {r['criterion_type'].upper():<10} | {r['category']:<16} | {r['raw_text'][:55]}")
conn.close()

# ── VALIDATION 2: Live ClinicalTrials.gov API now fires ────────
print(f"\n{divider}")
print("VALIDATION 2: Live ClinicalTrials.gov API (query=osteoporosis)")
print(divider)
r = api_get("/trials/search?query=osteoporosis&condition=osteoporosis")
if r.get("success"):
    trials = r["data"]
    live = [t for t in trials if "gov-" in t.get("id", "")]
    db_t  = [t for t in trials if "gov-" not in t.get("id", "")]
    print(f"  Total results: {len(trials)} | DB: {len(db_t)} | Live API: {len(live)}")
    for t in trials[:5]:
        src = "LIVE" if "gov-" in t.get("id", "") else "DB  "
        print(f"  [{src}] {t['nctId']} | {t['title'][:55]}")
else:
    print(f"  FAIL: {r}")

# ── VALIDATION 3: Full 7-criterion match for Scenario A ───────
print(f"\n{divider}")
print("VALIDATION 3: Full 7-criterion match — Scenario A vs NCT04500000")
print(divider)
r = api_post("/matching/evaluate", {
    "patient_id": "11111111-1111-1111-1111-111111111111",
    "trial_id":   "t-nct04500000"
})
if r.get("success"):
    d = r["data"]
    print(f"  Overall Status : {d['overall_status']}")
    print(f"  Match Score    : {d['match_score']:.1f}%")
    print(f"  Criteria       : {d['total_criteria']} total | {d['passed_count']} PASS | {d['failed_count']} FAIL | {d['unknown_count']} UNKNOWN | {d['conflict_count']} CONFLICT")
    print(f"  Engine         : {d['engine_version']}")
    print()
    for cr in d.get("criterion_results", []):
        icons = {"PASS": "✓", "FAIL": "✗", "UNKNOWN": "?", "CONFLICT": "!"}
        icon = icons.get(cr["status"], "·")
        print(f"  [{icon} {cr['status']:<8}] {cr['criterion_type'].upper():<10} | {cr['category']:<16} | {cr['raw_text'][:52]}")
        if cr.get("patient_value"):
            print(f"              Patient: {cr['patient_value']}  |  Expected: {cr.get('expected_value','—')}")
        if cr.get("source_evidence"):
            print(f"              Evidence: {cr['source_evidence'][:75]}")
        print(f"              Reliability: {cr['evidence_reliability']}  |  Engine: {cr['engine_version']}")
        print()
else:
    print(f"  FAIL: {r}")

# ── VALIDATION 4: MRN-01 (real OCR patient) full match ────────
print(f"\n{divider}")
print("VALIDATION 4: Real MRN-01 (99999999...) vs NCT04500000 — 7 criteria")
print(divider)
r = api_post("/matching/evaluate", {
    "patient_id": "99999999-9999-9999-9999-999999999999",
    "trial_id":   "t-nct04500000"
})
if r.get("success"):
    d = r["data"]
    print(f"  Overall Status : {d['overall_status']}")
    print(f"  Match Score    : {d['match_score']:.1f}%")
    print(f"  Criteria       : {d['total_criteria']} total | {d['passed_count']} PASS | {d['failed_count']} FAIL | {d['unknown_count']} UNKNOWN | {d['conflict_count']} CONFLICT")
    print()
    for cr in d.get("criterion_results", []):
        icons = {"PASS": "✓", "FAIL": "✗", "UNKNOWN": "?", "CONFLICT": "!"}
        icon = icons.get(cr["status"], "·")
        print(f"  [{icon} {cr['status']:<8}] {cr['criterion_type'].upper():<10} | {cr['category']:<16} | {cr['raw_text'][:52]}")
        if cr.get("patient_value"):
            print(f"              Patient Val: {cr['patient_value']}  |  Expected: {cr.get('expected_value','—')}")
        if cr.get("source_evidence"):
            print(f"              Evidence: {cr['source_evidence'][:75]}")
        print()
else:
    print(f"  FAIL: {r}")

print(f"\n{divider}")
print("All validations complete.")
print(divider)
