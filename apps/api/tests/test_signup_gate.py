"""Registration can be closed by configuration, and the client is told first.

A public demo of this product has to close registration, for a reason that is
not about policy: **nothing in this system sends email.** `email_outbox` records
what a person is owed and the schema comment says plainly that `sent_at` stays
NULL "forever until a provider is attached". A stranger who registered would be
stranded at an address they could never verify, holding a password they could
never reset — while accepting terms that still render a "pending legal review"
banner.

So the deployed demo runs with `STRIDE_ALLOW_SIGNUP=0` and collects no personal
data at all. These tests pin both halves of that: the refusal, and the fact that
a client can discover the policy before it draws a form nobody can submit.
"""
from __future__ import annotations

import pytest

from stride_api.config import settings


@pytest.fixture
def signup_closed():
    """Close registration for one test, whatever the environment default is."""
    original = settings.allow_signup
    settings.allow_signup = False
    try:
        yield
    finally:
        settings.allow_signup = original


@pytest.fixture
def signup_open():
    """Open it, for the same reason the fixture above closes it.

    `Settings` reads `STRIDE_ALLOW_SIGNUP` once at import, so a suite run in the
    deployed environment -- where it is `0` -- would fail every test that
    assumed the default was open. Asserting a default is asserting something
    about the machine rather than about the code.
    """
    original = settings.allow_signup
    settings.allow_signup = True
    try:
        yield
    finally:
        settings.allow_signup = original


def test_meta_is_public_and_says_signup_is_open(client, signup_open):
    r = client.get("/api/meta")
    assert r.status_code == 200, "no auth: the client reads this before anyone signs in"
    assert r.json()["signup_open"] is True
    assert r.json()["policy_version"]


def test_meta_reports_a_closed_signup(client, signup_closed):
    body = client.get("/api/meta").json()
    assert body["signup_open"] is False
    # and it tells the client to offer the demo accounts instead, so the sign-in
    # page has something to say rather than a missing tab and no explanation
    assert body["demo_accounts"] is True


def test_registration_is_refused_when_closed(client, signup_closed):
    r = client.post("/api/auth/register", json={
        "email": "stranger@example.com", "password": "correct-horse-battery",
        "display_name": "A Stranger", "role": "fan"})
    # 403, not 404: the route exists and the refusal is a stated policy rather
    # than a secret. 404 would be a lie about the shape of the API.
    assert r.status_code == 403
    assert r.json()["detail"] == "signup_closed"


def test_a_malformed_registration_is_still_refused_as_closed(client, signup_closed):
    """The gate runs before validation, so the answer is about the policy.

    Held inside the handler it sat behind `RegisterIn`, and a body that failed
    validation got 422 -- a complaint about the display name -- from a
    deployment that does not accept registrations at all. Two different reasons
    to say no, and the wrong one was winning.
    """
    r = client.post("/api/auth/register", json={"display_name": "x"})  # nothing valid here
    assert r.status_code == 403
    assert r.json()["detail"] == "signup_closed"


def test_no_account_is_created_when_signup_is_closed(client, db, signup_closed):
    before = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    client.post("/api/auth/register", json={
        "email": "stranger2@example.com", "password": "correct-horse-battery",
        "display_name": "Another", "role": "fan"})
    after = db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    assert after == before, "a refused registration must not leave a row behind"


def test_nothing_is_owed_an_email_when_signup_is_closed(client, db, signup_closed):
    """The point of closing it: no address enters the outbox that nothing drains."""
    before = db.execute("SELECT COUNT(*) AS n FROM email_outbox").fetchone()["n"]
    client.post("/api/auth/register", json={
        "email": "stranger3@example.com", "password": "correct-horse-battery",
        "display_name": "A Third", "role": "athlete"})
    after = db.execute("SELECT COUNT(*) AS n FROM email_outbox").fetchone()["n"]
    assert after == before


def test_the_seeded_demo_accounts_still_sign_in(client, signup_closed):
    """Closing the door must not lock out the accounts the demo runs on."""
    try:
        r = client.post("/api/auth/login",
                        json={"email": "sponsor@demo.stride", "password": "stride123"})
        assert r.status_code == 200
        assert r.json()["role"] == "sponsor"
    finally:
        # `client` is session-scoped: a successful login leaves it holding a
        # sponsor session. Cleared here rather than relying on the next test in
        # the file to do it, which is a dependency on declaration order that
        # nothing enforces and a reorder would silently break.
        client.cookies.clear()


def test_registration_still_works_when_open(client, signup_open):
    """Open is the default, so dev and the rest of this suite are unaffected —
    the gate only closes where a deployment says so."""
    assert settings.allow_signup is True
    try:
        r = client.post("/api/auth/register", json={
            "email": "opendoor@example.com", "password": "correct-horse-battery",
            "display_name": "Open Door", "role": "fan",
            # acceptance is required rather than defaulted -- see RegisterIn
            "accept_terms": True, "policy_version": settings.legal_policy_version})
        assert r.status_code == 201
    finally:
        # `client` is session-scoped and shared, and a successful registration
        # signs it in. Left holding that cookie it stops being the anonymous
        # caller every other test believes it is -- which is how this landed a
        # 403 where `test_the_org_routes_are_the_sponsor_role_only` asserts 401,
        # a failure in a file this one never touches.
        client.cookies.clear()
