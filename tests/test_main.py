from fastapi.testclient import TestClient
from mpips.api import app

client = TestClient(app)


def test_read_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["service"] == "mpips"
    assert "links" in data
    assert data["links"]["docs"] == "/docs"
    assert data["links"]["health"] == "/health"
