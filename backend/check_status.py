import asyncio
import httpx
import json

HEADERS = {"X-User-Email": "admin@clinical.org", "X-User-Role": "admin"}
BASE = "http://localhost:8000"

async def check():
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Get patients
        r = await client.get(f"{BASE}/api/v1/patients", headers=HEADERS)
        print(f"Patients status: {r.status_code}")
        if r.status_code == 200:
            patients = r.json()
            items = patients.get("items", patients) if isinstance(patients, dict) else patients
            items = items if isinstance(items, list) else []
            print(f"Total patients: {len(items)}")
            for p in items[:3]:
                pid = p.get("id") or p.get("patient_id") or "?"
                name = p.get("name") or p.get("full_name") or ""
                print(f"  Patient: {pid} - {name}")
                # Get docs for this patient
                r2 = await client.get(f"{BASE}/api/v1/documents/patient/{pid}", headers=HEADERS)
                if r2.status_code == 200:
                    docs = r2.json()
                    dl = docs.get("items", docs) if isinstance(docs, dict) else docs
                    dl = dl if isinstance(dl, list) else []
                    for d in dl[:3]:
                        did = d.get("id") or d.get("document_id") or "?"
                        ents = d.get("extracted_facts_count") or d.get("entity_count") or "?"
                        status = d.get("processing_status") or d.get("status") or "?"
                        fname = d.get("file_name") or d.get("filename") or "?"
                        print(f"    Doc: {fname} | id={did} | entities={ents} | status={status}")
        else:
            print(f"Error body: {r.text[:500]}")

asyncio.run(check())
