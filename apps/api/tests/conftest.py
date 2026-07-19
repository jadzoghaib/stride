"""Test bootstrap: configure the environment BEFORE stride_api imports.

The suite runs fully offline and deterministic:
  - Supabase disabled -> registration/login take the local PBKDF2 path
  - fresh temporary SQLite database, seeded by the app's own lifespan
  - chaos enabled so the failure-injection contract is testable
Set STRIDE_TEST_DATABASE_URL to a Postgres DSN to run the same suite on Postgres.
"""

from __future__ import annotations

import os
import tempfile

os.environ["STRIDE_ENV"] = "test"
os.environ["STRIDE_SUPABASE_URL"] = ""
os.environ["STRIDE_SUPABASE_ANON_KEY"] = ""
os.environ["STRIDE_CHAOS"] = "1"
os.environ["STRIDE_DATABASE_URL"] = os.environ.get("STRIDE_TEST_DATABASE_URL", "")
os.environ.setdefault("STRIDE_DB", os.path.join(tempfile.mkdtemp(prefix="stride-test-"), "stride.db"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from stride_api.main import app  # noqa: E402

PASSWORD = "stride123"


@pytest.fixture(scope="session")
def client():
    """App with lifespan run once: schema created + demo data seeded."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db():
    from stride_api.db import connect
    conn = connect()
    yield conn
    conn.close()


def make_session(email: str) -> TestClient:
    """A separate cookie jar logged in as the given demo account."""
    c = TestClient(app)
    res = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert res.status_code == 200, f"login failed for {email}: {res.text}"
    return c


@pytest.fixture(scope="session")
def athlete(client):
    return make_session("athlete@demo.stride")


@pytest.fixture(scope="session")
def sponsor(client):
    return make_session("sponsor@demo.stride")


@pytest.fixture(scope="session")
def fan(client):
    return make_session("fan@demo.stride")


@pytest.fixture(scope="session")
def clubu(client):
    return make_session("club@demo.stride")


@pytest.fixture(scope="session")
def admin(client):
    return make_session("admin@demo.stride")
