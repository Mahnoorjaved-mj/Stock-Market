"""Pytest fixtures.

We rely on a live Postgres for the integration tests. If DB_HOST isn't set or
the connection fails, integration-marked tests are skipped automatically.
"""
import os
import sys

import pytest


# Ensure backend/ is on sys.path when pytest is invoked from the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def app_client():
    os.environ.setdefault("FLASK_SECRET_KEY", "test-key")
    os.environ.setdefault("FLASK_DEBUG", "true")
    try:
        from app import app
    except Exception as e:
        pytest.skip(f"Flask app failed to import (missing deps?): {e}")
    app.config["TESTING"] = True
    # Disable CSRF for tests — easier to test JSON endpoints without manual tokens.
    app.config["WTF_CSRF_ENABLED"] = False
    return app.test_client()


@pytest.fixture(scope="session")
def db():
    try:
        from db import get_db_connection
        conn = get_db_connection()
        conn.close()
    except Exception as e:
        pytest.skip(f"DB unavailable: {e}")
    return True
