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

#: The suite runs on SQLite by default and on Postgres when this is set, so a
#: test whose subject *is* one backend has to say which.
ON_POSTGRES = bool(os.environ.get("STRIDE_TEST_DATABASE_URL"))
requires_postgres = pytest.mark.skipif(
    not ON_POSTGRES, reason="needs a Postgres server (set STRIDE_TEST_DATABASE_URL)")


@pytest.fixture
def sqlite_backend():
    """Force the SQLite code path whichever way the suite was invoked.

    A few tests build their own `sqlite3` connection to exercise migration and
    locking mechanics that only exist there. `init_db` and `lock_for_update`
    dispatch on `settings.db_backend`, so under the Postgres run they aimed
    Postgres DDL at a SQLite connection and failed for an unrelated reason.
    """
    from stride_api.config import settings
    original = settings.database_url
    settings.database_url = ""
    yield
    settings.database_url = original


@pytest.fixture(scope="session")
def client():
    """App with lifespan run once: schema created + demo data seeded."""
    if ON_POSTGRES:
        # SQLite gets a fresh temp file every session; Postgres gets whatever is
        # in the DSN, so without this the second run of the suite starts on the
        # first run's data and fails on things like a duplicate registration —
        # a difference between the backends that is nothing to do with the code
        # under test.
        from stride_api.db import connect, drop_all
        conn = connect()
        drop_all(conn)
        conn.close()
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
