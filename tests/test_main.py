from fastapi.testclient import TestClient
from mpips.api import app

client = TestClient(app)


def test_read_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mpips"
