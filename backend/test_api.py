import urllib.request, json

base = "http://127.0.0.1:8000/api/v1"
headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

def api_get(path):
    req = urllib.request.Request(base + path, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

def api_post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        base + path,
        data=body,
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

# ---- TEST 1: Trials search (local DB) ----
print("=== TEST 1: Trials Search (local DB) ===")
r = api_get("/trials/search")
if r.get("success"):
    trials = r["data"]
    print(f"STATUS: OK - {len(trials)} trials from DB")
    for t in trials[:3]:
        print(f"  {t['nctId']} | Score={t['rankingScore']} | {t['title'][:55]}")
else:
    print(f"FAIL: {r}")

# ---- TEST 2: Trials search with LIVE API query ----
print()
print("=== TEST 2: Trials Search (live ClinicalTrials.gov query=cancer) ===")
r = api_get("/trials/search?query=cancer&condition=cancer")
if r.get("success"):
    trials = r["data"]
    live = [t for t in trials if "gov-" in t.get("id", "")]
    db_t = [t for t in trials if "gov-" not in t.get("id", "")]
    print(f"STATUS: OK - {len(trials)} total, {len(db_t)} from DB, {len(live)} from live API")
    for t in trials[:4]:
        src = "LIVE API" if "gov-" in t.get("id", "") else "LOCAL DB"
        print(f"  [{src}] {t['nctId']} | {t['title'][:50]}")
else:
    print(f"FAIL: {r}")

# ---- TEST 3: Run matching for Scenario A patient vs NCT04500000 ----
print()
print("=== TEST 3: Run Eligibility Matching (Scenario A vs NCT04500000) ===")
patient_a = "11111111-1111-1111-1111-111111111111"
trial = "t-nct04500000"
r = api_post("/matching/evaluate", {"patient_id": patient_a, "trial_id": trial})
if r.get("success"):
    d = r["data"]
    print(f"STATUS: OK - Overall: {d['overall_status']}, Score: {d['match_score']}%")
    print(f"  Criteria: total={d['total_criteria']}, pass={d['passed_count']}, fail={d['failed_count']}, unknown={d['unknown_count']}, conflict={d['conflict_count']}")
    print(f"  Engine: {d['engine_version']}")
    for cr in d.get("criterion_results", []):
        print(f"  [{cr['status']}] {cr['criterion_type'].upper()} | {cr['category']} | {cr['raw_text'][:55]}")
        if cr.get("patient_value"):
            print(f"         Patient Val: {cr['patient_value']} | Expected: {cr.get('expected_value')}")
else:
    print(f"FAIL: {r}")

# ---- TEST 4: Run matching for Scenario A vs phase9 trial (which has approved criteria) ----
print()
print("=== TEST 4: Run Eligibility Matching (Scenario A vs t-phase9-trial) ===")
r = api_post("/matching/evaluate", {"patient_id": patient_a, "trial_id": "t-phase9-trial"})
if r.get("success"):
    d = r["data"]
    print(f"STATUS: OK - Overall: {d['overall_status']}, Score: {d['match_score']}%")
    print(f"  Criteria: total={d['total_criteria']}, pass={d['passed_count']}, fail={d['failed_count']}, unknown={d['unknown_count']}, conflict={d['conflict_count']}")
    for cr in d.get("criterion_results", []):
        print(f"  [{cr['status']}] {cr['criterion_type'].upper()} | {cr['category']} | {cr['raw_text'][:55]}")
else:
    print(f"FAIL: {r}")

# ---- TEST 5: MRN-01 real patient (99999999...) matching ----
print()
print("=== TEST 5: Run Matching for Real MRN-01 Patient (99999999...) ===")
mrn01_id = "99999999-9999-9999-9999-999999999999"
r = api_post("/matching/evaluate", {"patient_id": mrn01_id, "trial_id": "t-phase9-trial"})
if r.get("success"):
    d = r["data"]
    print(f"STATUS: OK - Overall: {d['overall_status']}, Score: {d['match_score']}%")
    print(f"  Criteria: total={d['total_criteria']}, pass={d['passed_count']}, fail={d['failed_count']}, unknown={d['unknown_count']}")
    for cr in d.get("criterion_results", []):
        print(f"  [{cr['status']}] {cr['criterion_type'].upper()} | {cr['category']} | {cr['raw_text'][:55]}")
        if cr.get("source_evidence"):
            print(f"         Evidence: {cr['source_evidence'][:80]}")
else:
    print(f"FAIL: {r}")

# ---- TEST 6: Match history for Scenario A ----
print()
print("=== TEST 6: Get Match History for Scenario A ===")
r = api_get("/matching/patient/11111111-1111-1111-1111-111111111111")
if r.get("success"):
    print(f"STATUS: OK - {len(r['data'])} historical matches")
    for m in r["data"][:3]:
        print(f"  {m.get('trial_id')} | {m.get('overall_status')} | score={m.get('match_score')}")
else:
    print(f"FAIL: {r}")

print()
print("All tests complete.")
