from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_demo_auth_token():
    response = client.get("/auth/demo-token")
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_dashboard_ui_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "CRM Autopilot" in response.text
