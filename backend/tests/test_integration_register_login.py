"""Smoke integration test:
   register → OTP verify → login → add watchlist symbol → list it.

Skips when DB is unavailable. SMTP is monkey-patched to a no-op so no real
email is sent.
"""
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.mark.integration
def test_register_login_flow(app_client, db, monkeypatch):
    # Stub out outbound email
    from services import email_service
    monkeypatch.setattr(email_service, "send_otp", lambda *a, **kw: None)
    monkeypatch.setattr(email_service, "send_welcome", lambda *a, **kw: None)
    monkeypatch.setattr(email_service, "send_password_reset", lambda *a, **kw: None)

    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass-9-Battery"

    r = app_client.post("/register", json={"email": email, "password": password})
    assert r.status_code == 200, r.get_json()

    # Pull OTP straight out of the table (in real life it goes via email)
    from db import get_db_connection
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT otp FROM otp_verification WHERE email=%s", (email,))
            row = cur.fetchone()
            assert row, "OTP record not created"
            otp = row[0]
    finally:
        conn.close()

    r = app_client.post("/verify_otp", json={"email": email, "otp": otp})
    assert r.status_code == 200
    assert r.get_json()["status"] == "success"

    # Now the test client carries a session cookie — add a watchlist entry.
    r = app_client.post("/api/watchlist", json={"symbol": "AAPL"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "success"

    r = app_client.get("/api/watchlist")
    assert r.status_code == 200
    payload = r.get_json()
    assert payload["status"] == "success"
    syms = [it["symbol"] for it in payload["items"]]
    assert "AAPL" in syms

    # Cleanup: delete the user (cascades watchlist).
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE email=%s", (email,))
        conn.commit()
    finally:
        conn.close()
