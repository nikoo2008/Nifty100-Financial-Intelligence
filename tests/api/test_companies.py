from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_company_list_and_profile():
    response = client.get("/api/v1/companies")
    assert response.status_code == 200
    assert len(response.json()) == 101
    profile = client.get("/api/v1/companies/TCS")
    assert profile.status_code == 200
    assert profile.json()["id"] == "TCS"


def test_unknown_company_is_404():
    assert client.get("/api/v1/companies/INVALID").status_code == 404


def test_company_histories_and_ratios():
    for suffix in ("pl", "bs", "cashflow", "ratios"):
        response = client.get(f"/api/v1/companies/TCS/{suffix}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
