"""The five things that make it safe to give a real person a login.

Terms accepted and recorded, an address that can be confirmed, a password that
can be recovered without anyone's help, changed without losing the session, and
every one of those flows going through the outbox rather than a mail provider
that does not exist yet.
"""

from __future__ import annotations

import pathlib
import re

from fastapi.testclient import TestClient

from stride_api.config import settings
from stride_api.db import row
from stride_api.main import app

REGISTER = {"email": "safety@test.local", "password": "longenough1",
            "display_name": "Safety Tester", "role": "fan"}


def _outbox_link(db, email: str, kind: str) -> str:
    mail = row(db, "SELECT body FROM email_outbox WHERE to_email = ? AND kind = ?"
                   " ORDER BY id DESC LIMIT 1", (email, kind))
    assert mail, f"no {kind} email queued for {email}"
    m = re.search(r"token=([A-Za-z0-9_\-]+)", mail["body"])
    assert m, "the email carries the link"
    return m.group(1)


def _cleanup(db, email: str) -> None:
    u = row(db, "SELECT id FROM users WHERE email = ?", (email,))
    if u:
        for t in ("auth_tokens", "notifications"):
            db.execute(f"DELETE FROM {t} WHERE user_id = ?", (u["id"],))
        db.execute("DELETE FROM email_outbox WHERE to_user_id = ?", (u["id"],))
        db.execute("DELETE FROM follows WHERE user_id = ?", (u["id"],))
        db.execute("DELETE FROM users WHERE id = ?", (u["id"],))
        db.commit()


# ── terms ────────────────────────────────────────────────────────────────────

def test_registration_without_accepting_the_terms_is_refused(client):
    r = client.post("/api/auth/register", json=REGISTER)
    assert r.status_code == 422
    assert r.json()["detail"] == "terms_not_accepted"


def test_acceptance_is_recorded_with_the_version_shown(db):
    c = TestClient(app)
    try:
        r = c.post("/api/auth/register", json={**REGISTER, "accept_terms": True,
                                               "policy_version": "2026-08-17"})
        assert r.status_code == 201
        u = row(db, "SELECT accepted_policy_version, accepted_at FROM users WHERE email = ?",
                (REGISTER["email"],))
        assert u["accepted_policy_version"] == "2026-08-17"
        assert u["accepted_at"]
        assert r.json()["accepted_policy_version"] == "2026-08-17"
    finally:
        _cleanup(db, REGISTER["email"])


def test_the_server_and_the_client_agree_on_the_policy_version():
    """Two constants, one meaning. The client shows the documents and sends
    the version; the server records it. If they drift, an account would be
    stamped with a version nobody was shown."""
    legal = pathlib.Path(__file__).resolve().parents[2] / "web/src/lib/legal.ts"
    shown = re.search(r"export const POLICY_VERSION = '([^']+)'", legal.read_text(encoding="utf-8"))
    assert shown and shown.group(1) == settings.legal_policy_version


# ── email verification ───────────────────────────────────────────────────────

def test_registration_queues_a_verification_email_and_the_link_verifies(db):
    c = TestClient(app)
    try:
        me = c.post("/api/auth/register", json={**REGISTER, "accept_terms": True}).json()
        assert me["email_verified"] is False
        token = _outbox_link(db, REGISTER["email"], "auth.verify_email")

        # works from a device with no session at all
        assert TestClient(app).post("/api/auth/verify-email", json={"token": token}).status_code == 200
        assert c.get("/api/auth/me").json()["email_verified"] is True

        # and only once
        again = TestClient(app).post("/api/auth/verify-email", json={"token": token})
        assert again.status_code == 400
        assert again.json()["detail"] == "invalid_or_expired_token"
    finally:
        _cleanup(db, REGISTER["email"])


def test_resending_retires_the_earlier_link(db):
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        first = _outbox_link(db, REGISTER["email"], "auth.verify_email")
        assert c.post("/api/auth/resend-verification").json()["already_verified"] is False
        second = _outbox_link(db, REGISTER["email"], "auth.verify_email")
        assert first != second
        assert TestClient(app).post("/api/auth/verify-email", json={"token": first}).status_code == 400
        assert TestClient(app).post("/api/auth/verify-email", json={"token": second}).status_code == 200
    finally:
        _cleanup(db, REGISTER["email"])


def test_demo_accounts_arrive_verified(athlete):
    assert athlete.get("/api/auth/me").json()["email_verified"] is True


# ── password reset ───────────────────────────────────────────────────────────

def test_forgot_does_not_reveal_whether_an_address_exists(client, db):
    known = client.post("/api/auth/forgot", json={"email": "fan@demo.stride"})
    unknown = client.post("/api/auth/forgot", json={"email": "nobody@nowhere.test"})
    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()
    assert row(db, "SELECT id FROM email_outbox WHERE to_email = 'fan@demo.stride'"
                   " AND kind = 'auth.reset_password'")
    assert not row(db, "SELECT id FROM email_outbox WHERE to_email = 'nobody@nowhere.test'")
    db.execute("DELETE FROM email_outbox WHERE kind = 'auth.reset_password'")
    db.execute("DELETE FROM auth_tokens WHERE purpose = 'reset_password'")
    db.commit()


def test_a_reset_link_sets_the_password_and_signs_everyone_else_out(db):
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        other_device = TestClient(app)
        assert other_device.post("/api/auth/login", json={
            "email": REGISTER["email"], "password": REGISTER["password"]}).status_code == 200

        TestClient(app).post("/api/auth/forgot", json={"email": REGISTER["email"]})
        token = _outbox_link(db, REGISTER["email"], "auth.reset_password")

        fresh = TestClient(app)
        done = fresh.post("/api/auth/reset", json={"token": token, "password": "brandnewpass2"})
        assert done.status_code == 200
        assert fresh.get("/api/auth/me").status_code == 200, "signed in on the device that reset"

        # the old password is dead, the new one works, the other device is out
        assert TestClient(app).post("/api/auth/login", json={
            "email": REGISTER["email"], "password": REGISTER["password"]}).status_code == 401
        assert TestClient(app).post("/api/auth/login", json={
            "email": REGISTER["email"], "password": "brandnewpass2"}).status_code == 200
        assert other_device.get("/api/auth/me").status_code == 401

        # and the link is spent
        assert TestClient(app).post("/api/auth/reset", json={
            "token": token, "password": "thirdpassword3"}).status_code == 400
    finally:
        _cleanup(db, REGISTER["email"])


def test_the_recovery_endpoints_share_the_strict_auth_bucket(client):
    """A reset endpoint is a credential surface. It gets the login limiter,
    not the generous general one."""
    codes = [client.post("/api/auth/forgot", json={"email": "nobody@nowhere.test"}).status_code
             for _ in range(30)]
    assert codes[-1] == 429


# ── change password ──────────────────────────────────────────────────────────

def test_changing_the_password_needs_the_current_one_and_keeps_this_session(db):
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        wrong = c.post("/api/auth/password", json={"current_password": "not-it",
                                                   "new_password": "brandnewpass2"})
        assert wrong.status_code == 403 and wrong.json()["detail"] == "wrong_password"

        elsewhere = TestClient(app)
        elsewhere.post("/api/auth/login", json={"email": REGISTER["email"],
                                                "password": REGISTER["password"]})
        assert c.post("/api/auth/password", json={"current_password": REGISTER["password"],
                                                  "new_password": "brandnewpass2"}).status_code == 200
        assert c.get("/api/auth/me").status_code == 200, "the device that changed it stays in"
        assert elsewhere.get("/api/auth/me").status_code == 401, "every other device is out"
        assert TestClient(app).post("/api/auth/login", json={
            "email": REGISTER["email"], "password": "brandnewpass2"}).status_code == 200
    finally:
        _cleanup(db, REGISTER["email"])


# ── change of address ────────────────────────────────────────────────────────

def test_changing_the_address_waits_for_the_new_one_to_confirm(db):
    """A typo that took effect immediately would lock the account out of its
    own recovery: reset is the only way back, and it mails the address on
    file. So the live address does not move until the new one opens a link."""
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        asked = c.post("/api/auth/email", json={"password": REGISTER["password"],
                                                "new_email": "moved@test.local"})
        assert asked.status_code == 200
        assert asked.json()["pending_email"] == "moved@test.local"

        # nothing has moved yet, and the old address still signs in
        assert c.get("/api/auth/me").json()["email"] == REGISTER["email"]
        assert TestClient(app).post("/api/auth/login", json={
            "email": REGISTER["email"], "password": REGISTER["password"]}).status_code == 200

        # the confirmation went to the NEW address; the old one got a warning
        token = _outbox_link(db, "moved@test.local", "auth.verify_email")
        assert row(db, "SELECT id FROM email_outbox WHERE to_email = ? AND kind ="
                       " 'auth.email_change_notice'", (REGISTER["email"],)), \
            "the address being left is told, so a session-theft cannot move it in silence"

        moved = TestClient(app).post("/api/auth/verify-email", json={"token": token})
        assert moved.status_code == 200 and moved.json()["email"] == "moved@test.local"
        assert TestClient(app).post("/api/auth/login", json={
            "email": "moved@test.local", "password": REGISTER["password"]}).status_code == 200
        assert TestClient(app).post("/api/auth/login", json={
            "email": REGISTER["email"], "password": REGISTER["password"]}).status_code == 401
    finally:
        _cleanup(db, REGISTER["email"])
        _cleanup(db, "moved@test.local")


def test_a_change_of_address_needs_the_password_and_a_free_address(db, athlete):
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        wrong = c.post("/api/auth/email", json={"password": "not-it", "new_email": "x@test.local"})
        assert wrong.status_code == 403 and wrong.json()["detail"] == "wrong_password"

        taken = c.post("/api/auth/email", json={"password": REGISTER["password"],
                                                "new_email": "athlete@demo.stride"})
        assert taken.status_code == 409 and taken.json()["detail"] == "email_exists"

        same = c.post("/api/auth/email", json={"password": REGISTER["password"],
                                               "new_email": REGISTER["email"]})
        assert same.status_code == 409 and same.json()["detail"] == "same_email"

        bad = c.post("/api/auth/email", json={"password": REGISTER["password"], "new_email": "nope"})
        assert bad.status_code == 422
        assert c.get("/api/auth/me").json()["email"] == REGISTER["email"], "nothing moved"
    finally:
        _cleanup(db, REGISTER["email"])


def test_a_plain_verification_still_just_verifies(db):
    """The same endpoint does both jobs. With nothing pending it must not
    invent a change."""
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**REGISTER, "accept_terms": True})
        token = _outbox_link(db, REGISTER["email"], "auth.verify_email")
        done = TestClient(app).post("/api/auth/verify-email", json={"token": token})
        assert done.status_code == 200 and done.json()["email"] == REGISTER["email"]
        assert c.get("/api/auth/me").json()["email_verified"] is True
    finally:
        _cleanup(db, REGISTER["email"])
