"""Access, portability, erasure -- the three rights the data page had marked
"specified, not built". Now built, and held to what the Privacy Policy says:
everything about you comes out; everything that names you goes; the ledger
keeps its numbers.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from stride_api.db import row
from stride_api.main import app

NEW = {"email": "rights@test.local", "password": "longenough1", "display_name": "Rights Tester",
       "role": "fan", "accept_terms": True}


def _cleanup(db, email_like: str) -> None:
    for u in db.execute("SELECT id FROM users WHERE email LIKE ?", (email_like,)).fetchall():
        uid = u["id"] if hasattr(u, "keys") else u[0]
        for t, col in (("auth_tokens", "user_id"), ("notifications", "user_id"), ("follows", "user_id"),
                       ("subscriptions", "user_id"), ("poll_votes", "user_id"), ("fan_posts", "user_id"),
                       ("email_outbox", "to_user_id")):
            db.execute(f"DELETE FROM {t} WHERE {col} = ?", (uid,))
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
    db.commit()


# ── export ───────────────────────────────────────────────────────────────────

def test_an_export_is_one_json_document_with_everything_in_it(athlete):
    out = athlete.get("/api/account/export").json()
    assert out["format"] == "stride-export-1"
    assert out["account"]["email"] == "athlete@demo.stride"
    assert "password_hash" not in out["account"] and "token_version" not in out["account"]
    assert out["profile"]["slug"] == "kaia-mercer"
    assert out["platform_accounts"], "the connected platforms are hers"
    assert out["score_snapshots"], "and so is every score computed from them"
    assert out["content"], "the wall she wrote"
    assert out["deals"], "the offers made to her"
    assert out["conversations"], "the threads she is in"
    assert all("email" not in c["with"] for c in out["conversations"]), \
        "other people appear as they appear inside the product -- never their email"
    assert any(e["event_type"] == "user.exported" for e in
               athlete.get("/api/account/export").json()["audit_trail"]), \
        "taking the export is itself on the record"


def test_every_role_can_export(sponsor, clubu, fan, admin):
    for who, key in ((sponsor, "campaigns"), (clubu, "packages"), (fan, "follows")):
        out = who.get("/api/account/export").json()
        assert out["account"]["role"] in ("sponsor", "club", "fan")
        assert key in out and out[key], f"{out['account']['role']} export carries its {key}"
    assert admin.get("/api/account/export").status_code == 200


def test_export_needs_a_session(client):
    assert client.get("/api/account/export").status_code == 401


# ── erasure ──────────────────────────────────────────────────────────────────

def test_deletion_needs_the_password_and_the_word(db):
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json=NEW)
        r = c.post("/api/account/delete", json={"password": "longenough1", "confirm": "yes"})
        assert r.status_code == 422 and r.json()["detail"] == "confirmation_word_mismatch"
        r = c.post("/api/account/delete", json={"password": "wrong-one", "confirm": "DELETE"})
        assert r.status_code == 403 and r.json()["detail"] == "wrong_password"
        assert c.get("/api/auth/me").status_code == 200, "a refused deletion changes nothing"
    finally:
        _cleanup(db, "rights@test.local")


def test_deleting_an_account_removes_the_person_and_keeps_the_ledger(db, client):
    """Register a fan, make them do things, delete them, and check each kind of
    row met the fate the policy promises it."""
    c = TestClient(app)
    kaia = row(db, "SELECT id, user_id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    try:
        me = c.post("/api/auth/register", json=NEW).json()
        uid = me["id"]
        assert c.post(f"/api/follows/{kaia['id']}").status_code == 201
        assert c.post(f"/api/subscriptions/athlete/{kaia['id']}").status_code == 201
        assert c.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "hello from a fan"}).status_code == 201
        assert c.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "great race"}).status_code == 201
        before_msgs = row(db, "SELECT COUNT(*) AS n FROM messages WHERE sender_id = ?", (uid,))["n"]
        assert before_msgs == 1

        done = c.post("/api/account/delete", json={"password": "longenough1", "confirm": "DELETE"})
        assert done.status_code == 200 and done.json()["deleted_at"]

        # the session is gone and the credentials are dead
        assert c.get("/api/auth/me").status_code == 401
        assert TestClient(app).post("/api/auth/login", json={
            "email": NEW["email"], "password": NEW["password"]}).status_code == 401

        # the row remains, with nothing on it that names a person
        u = row(db, "SELECT * FROM users WHERE id = ?", (uid,))
        assert u["email"] == f"deleted-{uid}@removed.invalid"
        assert u["display_name"] == "Deleted account" and u["status"] == "suspended" and u["deleted_at"]

        # everything that existed only because they were here is gone
        for t in ("follows", "subscriptions", "fan_posts", "notifications", "auth_tokens"):
            assert row(db, f"SELECT COUNT(*) AS n FROM {t} WHERE user_id = ?", (uid,))["n"] == 0, t
        # their words are gone; the thread survives for the athlete who also wrote in it
        assert row(db, "SELECT body FROM messages WHERE sender_id = ?", (uid,))["body"] == "[deleted]"
        assert row(db, "SELECT COUNT(*) AS n FROM conversations WHERE user_a = ? OR user_b = ?",
                   (uid, uid))["n"] == 1
        # and it is on the record, without a name
        ev = row(db, "SELECT detail_json FROM events WHERE event_type = 'user.deleted'"
                     " AND object_id = ?", (uid,))
        assert ev and "rights@test.local" not in ev["detail_json"]
    finally:
        # the anonymised row is the point; but the session-scoped database
        # should not accumulate one per run
        db.execute("UPDATE messages SET body = 'x' WHERE sender_id IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')")
        db.execute("DELETE FROM messages WHERE sender_id IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')")
        db.execute("DELETE FROM conversations WHERE user_a IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')"
                   " OR user_b IN (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')")
        db.execute("DELETE FROM events WHERE object_type = 'user' AND object_id IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')")
        _cleanup(db, "deleted-%@removed.invalid")
        _cleanup(db, "rights@test.local")


def test_an_athlete_deletion_hides_the_profile_and_keeps_the_deals(db):
    """The one role where the ledger argument bites: deals point at the
    profile, and a sponsor's accounting needs them to keep resolving."""
    c = TestClient(app)
    try:
        c.post("/api/auth/register", json={**NEW, "role": "athlete", "sport": "Rowing", "country": "Ireland"})
        uid = c.get("/api/auth/me").json()["id"]
        profile = row(db, "SELECT id FROM athlete_profiles WHERE user_id = ?", (uid,))
        # give them a deal the ledger must keep
        camp = row(db, "SELECT id, org_id FROM campaigns ORDER BY id LIMIT 1")
        db.execute("INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_eur, message,"
                   " status, created_at) VALUES (?, ?, ?, 'social_post', 1200, 'ledger', 'completed', ?)",
                   (camp["id"], camp["org_id"], profile["id"], "2026-09-05T00:00:00Z"))
        db.commit()

        assert c.post("/api/account/delete", json={"password": "longenough1", "confirm": "DELETE"}).status_code == 200

        p = row(db, "SELECT * FROM athlete_profiles WHERE id = ?", (profile["id"],))
        assert p["status"] == "hidden" and p["display_name"] == "Deleted athlete" and p["bio"] == ""
        assert row(db, "SELECT COUNT(*) AS n FROM deals WHERE athlete_id = ?", (profile["id"],))["n"] == 1, \
            "the deal record survives, pointing at a profile with no name on it"
        assert TestClient(app).get(f"/api/athletes").json()  # directory still serves
        assert all(a["slug"] != p["slug"] for a in TestClient(app).get("/api/athletes").json()["athletes"]), \
            "and does not list the hidden profile"
    finally:
        db.execute("DELETE FROM deals WHERE message = 'ledger'")
        db.execute("DELETE FROM athlete_profiles WHERE user_id IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid' OR email = 'rights@test.local')")
        db.execute("DELETE FROM events WHERE object_type = 'user' AND object_id IN"
                   " (SELECT id FROM users WHERE email LIKE 'deleted-%@removed.invalid')")
        _cleanup(db, "deleted-%@removed.invalid")
        _cleanup(db, "rights@test.local")


def test_an_admin_cannot_delete_themselves_from_here(admin):
    r = admin.post("/api/account/delete", json={"password": "stride123", "confirm": "DELETE"})
    assert r.status_code == 409
