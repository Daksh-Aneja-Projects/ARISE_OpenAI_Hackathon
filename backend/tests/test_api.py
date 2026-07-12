from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    """Smoke test to ensure the FastAPI app boots and health endpoint responds."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()
