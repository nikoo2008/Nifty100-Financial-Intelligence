from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_sector_routes():
    response = client.get("/api/v1/sectors")
    assert response.status_code == 200
    assert len(response.json()) == 11
    assert client.get("/api/v1/sectors/IT/companies").status_code == 200
    assert client.get("/api/v1/sectors/unknown").status_code == 404
