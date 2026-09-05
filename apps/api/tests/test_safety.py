"""Block and report.

The permission matrix says who may start a thread. It cannot say who a person
wants to hear from. These are the two levers that let them say it.
"""

from __future__ import annotations

import pytest

from stride_api.db import row


@pytest.fixture
def ids(db):
    return {
        "kaia": row(db, "SELECT id FROM users WHERE email = 'athlete@demo.stride'")["id"],
        "sponsor": row(db, "SELECT id FROM users WHERE email = 'sponsor@demo.stride'")["id"],
        "fan": row(db, "SELECT id FROM users WHERE email = 'fan@demo.stride'")["id"],
    }


@pytest.fixture(autouse=True)
def _clean(db):
    yield
    db.execute("DELETE FROM user_blocks")
    db.execute("DELETE FROM reports")
    db.execute("UPDATE users SET status = 'active' WHERE email LIKE '%@demo.stride'")
    db.commit()


# ── blocks ───────────────────────────────────────────────────────────────────

def test_a_block_ends_contact_in_both_directions(athlete, sponsor, ids):
    # the open network says a sponsor may write to an athlete
    assert sponsor.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is True
    assert athlete.post(f"/api/blocks/{ids['sponsor']}").status_code == 201

    # now neither side can reach the other, thread history or not
    assert sponsor.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is False
    r = sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "hello?"})
    assert r.status_code == 403 and r.json()["detail"] == "cannot_message_this_person"
    r = athlete.post("/api/messages", json={"to_user": ids["sponsor"], "body": "..."})
    assert r.status_code == 403, "the blocker cannot keep the channel open from their side either"

    # the block is visible to the one who placed it, and to nobody else
    mine = athlete.get("/api/blocks").json()
    assert [b["user_id"] for b in mine] == [ids["sponsor"]]
    assert sponsor.get("/api/blocks").json() == []

    # and lifting it restores the matrix's answer
    assert athlete.delete(f"/api/blocks/{ids['sponsor']}").status_code == 200
    assert sponsor.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is True


def test_an_existing_thread_shows_the_block_and_refuses_the_composer(athlete, sponsor, ids):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "before the block"})
    athlete.post(f"/api/blocks/{ids['sponsor']}")
    threads = athlete.get("/api/inbox").json()
    t = next(x for x in threads if x["with"]["id"] == ids["sponsor"])
    assert t["with"]["blocked"] is True, "the thread is still there to read"
    # but the sponsor's view of the same thread does not say they were blocked
    s = next(x for x in sponsor.get("/api/inbox").json() if x["with"]["id"] == ids["kaia"])
    assert s["with"]["blocked"] is False, "the other side is told nothing"
    assert sponsor.post("/api/messages", json={"to_user": ids["kaia"], "body": "after"}).status_code == 403


def test_blocking_is_idempotent_and_never_yourself(athlete, ids):
    assert athlete.post(f"/api/blocks/{ids['sponsor']}").json()["already"] is False
    assert athlete.post(f"/api/blocks/{ids['sponsor']}").json()["already"] is True
    assert athlete.post(f"/api/blocks/{ids['kaia']}").status_code == 409
    assert athlete.post("/api/blocks/999999").status_code == 404


def test_a_block_clears_the_unread_noise_from_that_person(athlete, sponsor, ids, db):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "ping"})
    before = row(db, "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND actor_user_id = ?"
                     " AND read_at IS NULL", (ids["kaia"], ids["sponsor"]))["n"]
    assert before >= 1
    athlete.post(f"/api/blocks/{ids['sponsor']}")
    after = row(db, "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND actor_user_id = ?"
                    " AND read_at IS NULL", (ids["kaia"], ids["sponsor"]))["n"]
    assert after == 0


# ── reports ──────────────────────────────────────────────────────────────────

def test_a_report_reaches_the_reviewer_with_the_message_attached(fan, athlete, admin, ids, db):
    """A fan who subscribes may message the athlete; if the athlete answers
    badly, the fan reports that message and the reviewer sees the words."""
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")["id"]
    fan.post(f"/api/subscriptions/athlete/{kaia}")
    fan.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "hi"})
    athlete.post("/api/messages", json={"to_user": ids["fan"], "body": "something unpleasant"})
    thread = next(t for t in fan.get("/api/inbox").json() if t["with"]["id"] == ids["kaia"])
    # the latest of theirs, not the first: earlier tests may already have put
    # words from Kaia in this thread
    msg = [m for m in fan.get(f"/api/inbox/{thread['id']}").json()["messages"] if not m["mine"]][-1]

    filed = fan.post("/api/reports", json={"user_id": ids["kaia"], "reason": "harassment",
                                           "detail": "see the message", "message_id": msg["id"]})
    assert filed.status_code == 201

    queue = admin.get("/api/admin/reports").json()
    r = next(x for x in queue if x["id"] == filed.json()["id"])
    assert r["reported_name"] == "Kaia Mercer" and r["reporter_role"] == "fan"
    assert r["message_body"] == "something unpleasant", "the reviewer reads the actual words"
    assert r["resolved_at"] is None
    fan.delete(f"/api/subscriptions/athlete/{kaia}")


def test_a_report_cannot_be_used_to_read_a_message_you_are_not_in(fan, sponsor, athlete, ids, db):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "private sponsor talk"})
    private = row(db, "SELECT id FROM messages WHERE sender_id = ? ORDER BY id DESC LIMIT 1",
                  (ids["sponsor"],))["id"]
    r = fan.post("/api/reports", json={"user_id": ids["sponsor"], "reason": "spam", "message_id": private})
    assert r.status_code == 404, "not in that thread, so that message does not exist for you"


def test_reports_need_a_known_reason_and_not_yourself(fan, ids):
    assert fan.post("/api/reports", json={"user_id": ids["kaia"], "reason": "because"}).status_code == 422
    assert fan.post("/api/reports", json={"user_id": ids["fan"], "reason": "spam"}).status_code == 409


def test_resolving_suspended_ends_every_session_and_the_login(fan, admin, db):
    """On a throwaway account, not a demo one: suspension bumps token_version,
    which would sign the session-scoped fixture out for every later test."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from stride_api.main import app  # noqa: PLC0415
    bad = TestClient(app)
    me = bad.post("/api/auth/register", json={
        "email": "reported@test.local", "password": "longenough1", "display_name": "Reported Person",
        "role": "fan", "accept_terms": True}).json()
    try:
        fan.post("/api/reports", json={"user_id": me["id"], "reason": "impersonation"})
        rid = admin.get("/api/admin/reports").json()[0]["id"]
        assert admin.post(f"/api/admin/reports/{rid}/resolve",
                          json={"resolution": "suspended", "note": "confirmed"}).status_code == 200
        assert bad.get("/api/auth/me").status_code == 401, "their sessions died with the status"
        assert TestClient(app).post("/api/auth/login", json={
            "email": "reported@test.local", "password": "longenough1"}).status_code == 403, "and the login refuses"
        assert admin.post(f"/api/admin/reports/{rid}/resolve",
                          json={"resolution": "dismissed"}).status_code == 409, "resolved once"
        assert admin.get("/api/admin/reports?status=open").json() == []
        assert admin.get("/api/admin/reports?status=resolved").json()[0]["resolution"] == "suspended"
    finally:
        db.execute("DELETE FROM reports WHERE reported_user_id = ?", (me["id"],))
        for t, col in (("auth_tokens", "user_id"), ("notifications", "user_id"), ("email_outbox", "to_user_id")):
            db.execute(f"DELETE FROM {t} WHERE {col} = ?", (me["id"],))
        db.execute("DELETE FROM users WHERE id = ?", (me["id"],))
        db.commit()


def test_the_queue_is_admin_only(fan, athlete, sponsor, client):
    for who in (fan, athlete, sponsor):
        assert who.get("/api/admin/reports").status_code == 403
    assert client.get("/api/admin/reports").status_code == 401
    assert client.post("/api/blocks/1").status_code == 401
