from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_health_is_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "companies" in body["db_row_counts"]
    assert "financial_ratios" in body["db_row_counts"]
