"""Test bootstrap: configure the environment BEFORE stride_api imports.

The suite runs fully offline and deterministic:
  - Supabase disabled -> registration/login take the local PBKDF2 path
  - fresh temporary SQLite database, seeded by the app's own lifespan
  - chaos enabled so the failure-injection contract is testable
Set STRIDE_TEST_DATABASE_URL to a Postgres DSN to run the same suite on Postgres.
"""

from __future__ import annotations

from contextlib import contextmanager

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

from stride_api.db import rows  # noqa: E402
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
def athlete2(client):
    """Sofia Brandt: claimed, and still waiting on the review queue.

    The other athlete account. `athlete` is Kaia Mercer, who is already listed,
    so anything about getting *into* the directory needs somebody who is not.
    """
    return make_session("athlete2@demo.stride")


@pytest.fixture(scope="session")
def sponsor(client):
    return make_session("sponsor@demo.stride")


@pytest.fixture(scope="session")
def sponsor2(client):
    """A second organisation. Anything about one org not reaching another's
    campaigns needs a session that genuinely belongs somewhere else."""
    return make_session("sponsor2@demo.stride")


@pytest.fixture(scope="session")
def fan(client):
    return make_session("fan@demo.stride")


@pytest.fixture(scope="session")
def clubu(client):
    return make_session("club@demo.stride")


@pytest.fixture(scope="session")
def admin(client):
    return make_session("admin@demo.stride")


@pytest.fixture(autouse=True)
def _fresh_api_rate_limit():
    """Give each test its own general-API budget.

    Every request in the suite comes from one client host, so they all share a
    single 300-token bucket. The suite passed until it grew past 300 requests,
    at which point whichever tests ran last began failing with `rate_limited` --
    a failure with no relationship to the code under test, appearing in a file
    that had not changed.

    Both buckets, including `auth:`. Leaving that one alone was the smaller
    change and the wrong one: `test_login_brute_force_rate_limited` drains it on
    purpose, so every session fixture that first logs in *after* that test --
    which is every one added later, in a file that sorts after `test_api` --
    fails on a 429 that has nothing to do with what it is testing. The
    brute-force test still passes: it makes thirty attempts against a bucket of
    twenty inside its own test, so it exhausts it either way.
    """
    from stride_api.security import buckets
    buckets._state.clear()
    yield


# ── shared state isolation ─────────────────────────────────────────────────

#: What the messaging tests write to and then count. Threads are the dangerous
#: one: `may_open` is only consulted when no conversation exists, so a thread
#: left behind by an earlier test silently grants reply rights to a pair the
#: rule under test would have refused.
MESSAGING_TABLES = ("messages", "conversations", "notifications", "subscriptions",
                    "deals", "club_members", "package_commitments")


@contextmanager
def preserved(db, tables):
    """Put `tables` back exactly as they were found — all three ways.

    `db` is session-scoped, so anything a test writes outlives it. There are
    three ways to leave a mark and the original version of this helper undid
    only the first:

    1. rows **added** — deleted here, as before;
    2. rows **changed** in place — several tests do this
       (`UPDATE conversations SET last_message_at = ...` to force an ordering
       tie, `UPDATE deals SET status = 'withdrawn'`), and the change used to
       survive for the rest of the session, quietly reshaping the state every
       later test ran against;
    3. rows **deleted** — a test that unsubscribes the seeded fan used to leave
       it unsubscribed for good.

    The snapshot always captured whole rows; only the ids were ever used, which
    is why 2 and 3 went unrestored. Re-inserting a deleted row needs its
    original id back, and every table here declares `id` as
    `GENERATED ALWAYS AS IDENTITY` on Postgres — hence the override, which is
    Postgres-only syntax and empty on SQLite.

    **`tables` must be ordered child-before-parent.** Phase 1 walks it
    reversed to insert parents first; phase 3 walks it forwards to delete
    children first. Hand it the wrong order and the restore raises on a foreign
    key instead of restoring. `MESSAGING_TABLES` is ordered for this.

    **One hazard this cannot order its way out of.** The three phases have
    circular requirements: reverting a change needs its original foreign-key
    target back (so deletions restore first), deleting an addition needs
    nothing pointing at it (so changes revert first), and re-inserting a
    deleted row needs its unique key free (so additions delete first). No
    single order satisfies all three, so this one favours the case the suite
    actually exercises -- a changed row pointing at an added row, which
    `test_it_survives_a_changed_row_pointing_at_an_added_one` covers.

    Delete-then-re-add of a uniquely-keyed row is handled: phase 1 clears a
    table's added rows before inserting into that table, so the replacement is
    not still holding the key. What remains unhandled is only the three-way
    combination -- a table that both needs a row put back *and* holds an added
    row that some changed row elsewhere still points at. Nothing here does
    that, and if anything ever does it raises the explanatory error below
    rather than a bare IntegrityError from inside a fixture.

    Lives in conftest rather than in a test module because more than one file
    needs it, and a copy in each is a copy that drifts.
    """
    def snapshot(table):
        return {r["id"]: dict(r) for r in rows(db, f"SELECT * FROM {table}")}

    before = {t: snapshot(t) for t in tables}
    try:
        yield
    finally:
        _restore(db, tables, before, {t: snapshot(t) for t in tables})


def _restore(db, tables, before, after):
    """Put the tables back, or explain why it could not.

    A fixture that dies with a bare IntegrityError sends the next person
    reading it into the wrong file. Anything raised here is a limitation of
    this helper rather than a fault in the test that tripped it, and the
    message says so.
    """
    try:
        _restore_phases(db, tables, before, after)
    except Exception as exc:      # noqa: BLE001 -- re-raised immediately
        raise RuntimeError(
            "preserved() could not restore the database. This is a limitation of"
            " the helper, not of the test that hit it -- see its docstring. The"
            " usual cause is a scope that deleted a uniquely-keyed row and added"
            " another with the same key, which the phase order cannot undo."
            f" Original error: {exc!r}") from exc


def _restore_phases(db, tables, before, after):

    # Three phases, and the order between them is the whole correctness
    # argument. Foreign keys are enforced on both backends -- SQLite gets
    # `PRAGMA foreign_keys = ON` in db.py -- so a restore that runs them in
    # the wrong order raises instead of restoring, and leaves the database
    # worse than it found it.
    #
    # Deleting additions last is the part that is easy to get backwards. A
    # test can point a *pre-existing* row at a row it added
    # (`UPDATE messages SET conversation_id = <a new conversation>`); delete
    # the added parent first and that still-modified child blocks it.
    override = " OVERRIDING SYSTEM VALUE" if ON_POSTGRES else ""

    # 1 · Put deleted rows back, parent before child. Their original values
    #     reference rows that existed at snapshot time, which are either
    #     still here or restored earlier in this same pass.
    #
    #     Where a table needs a row put back, that table's *added* rows are
    #     cleared first, because a test that deletes a uniquely-keyed row and
    #     adds another with the same key would otherwise have the replacement
    #     still sitting on the key -- `subscriptions` is unique on
    #     `(user_id, athlete_id)` and unsubscribe-then-resubscribe is an
    #     ordinary thing for a test to do. Only tables being inserted into are
    #     touched, so the additions phase 3 defers on behalf of a changed row
    #     pointing at them are left exactly where they are.
    for table in reversed(tables):
        missing = [i for i in before[table] if i not in after[table]]
        if not missing:
            continue
        added = [i for i in after[table] if i not in before[table]]
        if added:
            db.execute(f"DELETE FROM {table} WHERE id IN"
                       f" ({', '.join('?' for _ in added)})", added)
        for row_id in missing:
            original = before[table][row_id]
            cols = list(original)
            db.execute(
                f"INSERT INTO {table} ({', '.join(cols)}){override}"
                f" VALUES ({', '.join('?' for _ in cols)})",
                [original[c] for c in cols])

    # 2 · Revert rows that were changed in place. Every foreign key they
    #     originally held now resolves again, because of phase 1.
    for table in reversed(tables):
        for row_id, original in before[table].items():
            current = after[table].get(row_id)
            if current is None or current == original:
                continue
            cols = [c for c in original if c != "id"]
            db.execute(
                f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)}"
                f" WHERE id = ?",
                [original[c] for c in cols] + [row_id])

    # 3 · Only now delete what was added, child before parent. Nothing that
    #     survives still points at these: every pre-existing reference was
    #     reverted in phase 2, and references between added rows are handled
    #     by the child-first order of `tables`.
    for table in tables:
        added = [i for i in after[table] if i not in before[table]]
        if added:
            db.execute(f"DELETE FROM {table} WHERE id IN"
                       f" ({', '.join('?' for _ in added)})", added)
    db.commit()


@pytest.fixture
def clean_slate(db):
    """Isolation for the messaging tests, defined once.

    Not autouse: in conftest that would apply it to every file in the suite.
    The messaging modules opt in with a module-level
    `pytestmark = pytest.mark.usefixtures("clean_slate")`.
    """
    with preserved(db, MESSAGING_TABLES):
        yield
