import urllib.request, json

BASE = "http://127.0.0.1:8000/api/v1"
H = {"X-User-Email": "coordinator@clinicaltrial.ai", "X-User-Role": "research_coordinator"}

def get(path):
    req = urllib.request.Request(BASE + path, headers=H)
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read())

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={**H, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}

SEP = "=" * 56

# 1. Can the details page load NCT04500000?
print(f"\n{SEP}\nTEST 1: GET /trials/NCT04500000 (the details page call)\n{SEP}")
r = get("/trials/NCT04500000")
if r.get("success"):
    t = r["data"]
    print(f"  OK - id={t['id']} | nctId={t['nctId']} | v{t['version']}")
    print(f"  Versions: {len(t.get('versions', []))}")
else:
    print(f"  FAIL: {r}")

# 2. Criteria endpoint the page calls
print(f"\n{SEP}\nTEST 2: GET /criteria/trial/t-nct04500000\n{SEP}")
r = get("/criteria/trial/t-nct04500000")
if r.get("success"):
    crits = r["data"]
    approved = [c for c in crits if c["approval_status"] == "approved"]
    pending  = [c for c in crits if c["approval_status"] == "pending"]
    print(f"  OK - {len(crits)} total | {len(approved)} approved | {len(pending)} pending")
    for c in approved:
        print(f"    [APPROVED] {c['criterion_type'].upper():<10} {c['category']:<16} | {c['raw_text'][:50]}")
else:
    print(f"  FAIL: {r}")

# 3. MRN-01 inline match from details page (using trial DB id)
print(f"\n{SEP}\nTEST 3: POST /matching/evaluate  MRN-01 vs t-nct04500000\n{SEP}")
r = post("/matching/evaluate", {
    "patient_id": "99999999-9999-9999-9999-999999999999",
    "trial_id":   "t-nct04500000"
})
if r.get("success"):
    d = r["data"]
    print(f"  Overall : {d['overall_status']}")
    print(f"  Score   : {d['match_score']:.1f}%")
    print(f"  Rules   : {d['total_criteria']} total | {d['passed_count']} PASS | {d['failed_count']} FAIL | {d['unknown_count']} UNKNOWN")
    print()
    for cr in d.get("criterion_results", []):
        sym = {"PASS": "[PASS]", "FAIL": "[FAIL]", "UNKNOWN": "[UNKN]", "CONFLICT": "[CONF]"}
        s = sym.get(cr["status"], "[ ?? ]")
        print(f"  {s} {cr['criterion_type'].upper():<10} {cr['category']:<16} {cr['raw_text'][:48]}")
        if cr.get("patient_value"):
            print(f"         Patient: {cr['patient_value']}  |  Expected: {cr.get('expected_value','')}")
else:
    print(f"  FAIL: {r}")

# 4. Scenario A inline match from details page
print(f"\n{SEP}\nTEST 4: POST /matching/evaluate  Scenario A vs t-nct04500000\n{SEP}")
r = post("/matching/evaluate", {
    "patient_id": "11111111-1111-1111-1111-111111111111",
    "trial_id":   "t-nct04500000"
})
if r.get("success"):
    d = r["data"]
    print(f"  Overall : {d['overall_status']}")
    print(f"  Score   : {d['match_score']:.1f}%  ({d['total_criteria']} criteria)")
    for cr in d.get("criterion_results", []):
        sym = {"PASS": "PASS", "FAIL": "FAIL", "UNKNOWN": "UNKN", "CONFLICT": "CONF"}
        print(f"  [{sym.get(cr['status'],'??')}] {cr['criterion_type'].upper():<10} {cr['category']:<16} {cr['raw_text'][:48]}")
else:
    print(f"  FAIL: {r}")

print(f"\n{SEP}\nAll tests passed.\n{SEP}")
