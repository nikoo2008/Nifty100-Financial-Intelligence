from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_screener_filter():
    response = client.get("/api/v1/screener", params={"min_roe": 15})
    assert response.status_code == 200
    assert all(
        (row.get("return_on_equity_pct") is None or row["return_on_equity_pct"] >= 15)
        for row in response.json()
    )


def test_screener_rejects_extreme_parameter():
    assert (
        client.get("/api/v1/screener", params={"min_roe": 2_000_000}).status_code == 400
    )
