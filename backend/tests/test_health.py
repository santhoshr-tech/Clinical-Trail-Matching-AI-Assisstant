import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "healthy"

def test_config_status_endpoint():
    response = client.get("/api/config/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    data = json_data["data"]
    # Check that output contains only sanitized status strings (configured/missing/invalid)
    assert data["status"] in ["configured", "missing", "invalid"]
    assert data["geminiStatus"] in ["configured", "missing", "invalid"]
    assert data["ollamaStatus"] in ["configured", "missing", "invalid"]
    assert data["clinicalTrialsApiStatus"] in ["configured", "missing", "invalid"]

def test_module_routers():
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    assert response.json()["success"] is True
