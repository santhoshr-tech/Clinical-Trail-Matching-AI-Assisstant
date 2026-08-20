import sqlite3
import json

DB = "local_prototype.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# --- FIX 1: Approve all pending criteria for t-nct04500000 ---
cur.execute(
    "SELECT id, criterion_type, category, raw_text, approval_status FROM trial_criteria WHERE trial_id = 't-nct04500000'"
)
rows = cur.fetchall()
print(f"Criteria for t-nct04500000 ({len(rows)} total):")
for r in rows:
    print(f"  [{r['approval_status'].upper()}] {r['criterion_type']} | {r['category']} | {r['raw_text'][:60]}")

pending_ids = [r['id'] for r in rows if r['approval_status'] == 'pending']
print(f"\nApproving {len(pending_ids)} pending criteria...")

for cid in pending_ids:
    cur.execute(
        "UPDATE trial_criteria SET approval_status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (cid,)
    )
    print(f"  Approved: {cid}")

conn.commit()

# Verify
cur.execute(
    "SELECT approval_status, COUNT(*) as cnt FROM trial_criteria WHERE trial_id = 't-nct04500000' GROUP BY approval_status"
)
print("\nPost-fix criteria status for t-nct04500000:")
for r in cur.fetchall():
    print(f"  {r['approval_status']}: {r['cnt']}")

conn.close()
print("\nFix 1 complete.")
