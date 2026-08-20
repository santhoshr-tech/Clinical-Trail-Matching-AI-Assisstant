import pytest
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

headers = {
    "X-User-Email": "coordinator@clinicaltrial.ai",
    "X-User-Role": "research_coordinator"
}

def test_search_and_rank_trials():
    response = client.get("/api/v1/trials/search?query=Pembrolizumab&search_mode=lexical", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    trials = data["data"]
    assert len(trials) >= 1
    assert "NCT04500000" in [t["nctId"] for t in trials]
    assert trials[0]["rankingScore"] > 0

def test_semantic_search_mode():
    response = client.get("/api/v1/trials/search?query=Lung+Cancer&search_mode=semantic", headers=headers)
    assert response.status_code == 200
    trials = response.json()["data"]
    assert len(trials) >= 1
    assert trials[0]["searchModeUsed"] == "semantic"

def test_filter_trials():
    response = client.get("/api/v1/trials/search?phase=Phase+3&recruitment_status=RECRUITING", headers=headers)
    assert response.status_code == 200
    trials = response.json()["data"]
    for t in trials:
        assert t["phase"] == "Phase 3"
        assert t["recruitmentStatus"] == "RECRUITING"

def test_get_trial_details_and_versions():
    # 1. Fetch Details for synthetic trial NCT04500000
    res_details = client.get("/api/v1/trials/t-nct04500000", headers=headers)
    assert res_details.status_code == 200
    t_data = res_details.json()["data"]
    assert t_data["nctId"] == "NCT04500000"
    assert t_data["sourceUrl"] == "https://clinicaltrials.gov/study/NCT04500000"
    assert t_data["version"] >= 1

    # 2. Fetch Version History
    res_ver = client.get("/api/v1/trials/t-nct04500000/versions", headers=headers)
    assert res_ver.status_code == 200
    versions = res_ver.json()["data"]
    assert len(versions) >= 1
    assert versions[0]["versionNumber"] >= 1

def test_import_and_sync_version():
    # 1. Import new trial NCT09999999
    res_import = client.post("/api/v1/trials/import/NCT09999999", headers=headers)
    assert res_import.status_code == 200
    assert res_import.json()["data"]["nctId"] == "NCT09999999"

    # 2. Sync & Update trial NCT09999999 to increment version
    sync_payload = {
        "title": "Updated Trial Title for Phase 4 Test",
        "changeSummary": "Testing protocol amendment sync"
    }
    res_sync = client.post("/api/v1/trials/t-nct09999999/sync", json=sync_payload, headers=headers)
    assert res_sync.status_code == 200
    assert res_sync.json()["data"]["newVersion"] > 1
