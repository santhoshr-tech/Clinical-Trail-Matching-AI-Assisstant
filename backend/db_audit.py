import sqlite3, json, sys

DB = "local_prototype.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# 1. All patients
section("1. ALL PATIENTS")
cur.execute("SELECT id, mrn_synthetic, age, gender, primary_diagnosis, disease_stage, source FROM patients ORDER BY mrn_synthetic")
for r in cur.fetchall():
    print(dict(r))

# 2. Extracted clinical facts (real Gemini-extracted data)
section("2. EXTRACTED CLINICAL FACTS")
cur.execute("SELECT patient_id, category, canonical_label, review_status, ai_provider, ai_model, created_at FROM extracted_clinical_facts ORDER BY created_at DESC LIMIT 20")
rows = cur.fetchall()
print(f"Total extracted facts: {len(rows)}")
for r in rows:
    print(dict(r))

# 3. Patient conditions  
section("3. PATIENT CONDITIONS")
cur.execute("SELECT patient_id, raw_value, normalized_value, verification_status, source FROM patient_conditions ORDER BY created_at DESC LIMIT 15")
for r in cur.fetchall():
    print(dict(r))

# 4. Trial criteria breakdown
section("4. TRIAL CRITERIA (all statuses)")
cur.execute("SELECT trial_id, approval_status, COUNT(*) as cnt FROM trial_criteria GROUP BY trial_id, approval_status")
for r in cur.fetchall():
    print(dict(r))

# 5. Approved criteria detail
section("5. APPROVED CRITERIA DETAIL")
cur.execute("SELECT id, trial_id, criterion_type, category, operator, value_primary, raw_text, approval_status FROM trial_criteria WHERE approval_status='approved'")
approved = cur.fetchall()
print(f"Approved count: {len(approved)}")
for r in approved:
    print(dict(r))

# 6. Pending criteria (first 5)
section("6. PENDING CRITERIA (first 5)")
cur.execute("SELECT id, trial_id, criterion_type, category, raw_text, approval_status FROM trial_criteria WHERE approval_status='pending' LIMIT 5")
for r in cur.fetchall():
    print(dict(r))

# 7. Match history
section("7. MATCH HISTORY")
cur.execute("SELECT patient_id, trial_id, overall_status, match_score, total_criteria, passed_count, failed_count, engine_version FROM patient_trial_matches ORDER BY evaluated_at DESC LIMIT 5")
matches = cur.fetchall()
print(f"Total matches run: {len(matches)}")
for r in matches:
    print(dict(r))

# 8. Patient labs
section("8. PATIENT LABS")
cur.execute("SELECT patient_id, normalized_value, numeric_value, unit, lab_date, is_stale, verification_status FROM patient_labs")
for r in cur.fetchall():
    print(dict(r))

# 9. Patient biomarkers
section("9. PATIENT BIOMARKERS")
cur.execute("SELECT patient_id, biomarker_name, normalized_value, status_value, test_date, is_stale, verification_status FROM patient_biomarkers")
for r in cur.fetchall():
    print(dict(r))

# 10. Trials in DB
section("10. TRIALS IN DB")
cur.execute("SELECT id, nct_id, title, recruitment_status, phase FROM trials")
for r in cur.fetchall():
    print(dict(r))

conn.close()
print("\nAudit complete.")
