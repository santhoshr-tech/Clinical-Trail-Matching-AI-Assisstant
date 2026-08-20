import sqlite3
DB = "local_prototype.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== ALL PATIENTS ===")
cur.execute("SELECT id, mrn_synthetic, age, gender, primary_diagnosis, source FROM patients ORDER BY mrn_synthetic")
for r in cur.fetchall():
    print(dict(r))

print("\n=== CRITERIA TOTALS ===")
cur.execute("SELECT trial_id, approval_status, COUNT(*) as cnt FROM trial_criteria GROUP BY trial_id, approval_status")
for r in cur.fetchall():
    print(dict(r))

print("\n=== APPROVED CRITERIA ===")
cur.execute("SELECT id, trial_id, criterion_type, category, operator, raw_text FROM trial_criteria WHERE approval_status='approved'")
rows = cur.fetchall()
print(f"Approved count: {len(rows)}")
for r in rows:
    print(dict(r))

print("\n=== EXTRACTED FACTS BREAKDOWN ===")
cur.execute("SELECT patient_id, category, COUNT(*) as cnt FROM extracted_clinical_facts GROUP BY patient_id, category")
for r in cur.fetchall():
    print(dict(r))

print("\n=== MATCH HISTORY ===")
cur.execute("SELECT patient_id, trial_id, overall_status, match_score, total_criteria, engine_version FROM patient_trial_matches ORDER BY evaluated_at DESC LIMIT 5")
rows = cur.fetchall()
print(f"Total matches: {len(rows)}")
for r in rows:
    print(dict(r))

print("\n=== PATIENT CONDITIONS (all) ===")
cur.execute("SELECT patient_id, normalized_value, source FROM patient_conditions LIMIT 20")
for r in cur.fetchall():
    print(dict(r))

conn.close()
print("\nDone.")
