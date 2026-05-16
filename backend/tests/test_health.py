"""Smoke test of the /api/health endpoint."""


def test_health_returns_json(app_client):
    res = app_client.get("/api/health")
    # status 200 (all-good) or 503 (degraded), but always a JSON body
    assert res.status_code in (200, 503)
    data = res.get_json()
    assert "status" in data
    assert "db" in data
    assert "scheduler" in data


def test_check_auth_unauthenticated(app_client):
    res = app_client.get("/check-auth")
    assert res.status_code == 200
    assert res.get_json()["logged_in"] is False
