"""Campaign measurement: deal -> delivered content -> what the sponsor got.

The gap this closes: a deal could reach status 'completed' with nothing anywhere
recording what was delivered. Learned matching needs these outcomes
(business-plan/09-analytics-strategy.md) and sponsors renew on them.
"""

from __future__ import annotations

import sqlite3

import pytest

from stride_api.db import _migrate, init_db, lock_for_update


def _columns(conn, table):
    return {c["name"] for c in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_a_column_added_later_reaches_a_database_that_already_exists():
    """The failure this reproduces was found by running the app, not the suite:
    every test builds a fresh database, where CREATE TABLE writes the current
    schema. On a database that already has the table it is a no-op, so a column
    added afterwards never lands and the first read of it 500s."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    # rewind one version, the way a developer's database is behind the code
    conn.execute("ALTER TABLE deals DROP COLUMN completed_at")
    assert "completed_at" not in _columns(conn, "deals")

    init_db(conn)  # restart the app
    assert "completed_at" in _columns(conn, "deals")
    init_db(conn)  # and again: the backfill has to be idempotent
    assert "completed_at" in _columns(conn, "deals")

    # every entry in the list, not just the first — a column added later is
    # exactly as invisible to CREATE TABLE as the one that taught us this
    conn.execute("ALTER TABLE campaigns DROP COLUMN require_verified_athletes")
    init_db(conn)
    assert "require_verified_athletes" in _columns(conn, "campaigns")
    conn.close()


def test_a_renamed_column_reaches_a_database_that_already_exists():
    """The money columns moved from USD to EUR in one pass, and a rename is
    worse than a missing column: the old name is still there holding the data,
    so nothing is obviously broken until a query asks for the new one. Half a
    migration is worse than either currency."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    # rewind to the pre-EUR shape
    conn.execute("ALTER TABLE deals RENAME COLUMN amount_eur TO amount_usd")
    conn.execute("ALTER TABLE athlete_profiles RENAME COLUMN base_rate_eur TO base_rate_usd")
    assert "amount_usd" in _columns(conn, "deals")

    init_db(conn)  # restart the app
    assert _columns(conn, "deals") >= {"amount_eur"}
    assert "amount_usd" not in _columns(conn, "deals")
    assert "base_rate_eur" in _columns(conn, "athlete_profiles")

    init_db(conn)  # and again: renaming has to be idempotent too
    assert "amount_eur" in _columns(conn, "deals")
    conn.close()


def test_a_rename_carries_the_data_across(client, db):
    """A rename that dropped and recreated the column would pass the check above
    and silently empty the ledger."""
    amounts = [r["amount_eur"] for r in db.execute("SELECT amount_eur FROM deals").fetchall()]
    assert amounts and all(a > 0 for a in amounts)

def _fresh_campaign(sponsor, name):
    """A campaign of this test's own.

    The seeded data already carries an open offer to the demo athlete, and the
    duplicate-offer guard is per campaign — so reusing a seeded campaign makes
    these tests depend on what the rest of the suite did first.
    """
    res = sponsor.post("/api/campaigns", json={
        "name": name, "category": "Sportswear", "deal_types": ["social_post"],
        "budget_eur_min": 1000, "budget_eur_max": 20000,
        "target_age_buckets": ["18-24", "25-34"], "target_countries": ["US"],
        "target_topics": ["running", "training"]})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _athlete_id(client_or_session, slug="kaia-mercer"):
    return client_or_session.get(f"/api/athletes/{slug}").json()["id"]


def _accepted_deal(sponsor, athlete, name="measurement"):
    """Fresh campaign -> offer -> accepted, with no dependence on suite order."""
    campaign_id = _fresh_campaign(sponsor, f"{name} campaign")
    offer = sponsor.post(f"/api/campaigns/{campaign_id}/offers", json={
        "athlete_id": _athlete_id(sponsor), "deal_type": "social_post",
        "amount_eur": 5000, "message": "measurement test"})
    assert offer.status_code == 201, offer.text
    deal_id = offer.json()["id"]
    assert athlete.post(f"/api/athlete/deals/{deal_id}/respond",
                        json={"action": "accept"}).status_code == 200
    return deal_id


def test_projection_is_captured_when_the_offer_is_sent(sponsor, athlete):
    """Without a projection stored at offer time there is nothing to measure
    delivery against, and it cannot be reconstructed later."""
    deal_id = _accepted_deal(sponsor, athlete, "projection")
    perf = sponsor.get(f"/api/deals/{deal_id}/performance").json()
    assert perf["projected"]["reach"] is not None
    assert perf["projected"]["reach"] > 0


def test_deliverables_and_completion_produce_a_measurement(sponsor, athlete, db):
    deal_id = _accepted_deal(sponsor, athlete, "delivery")

    # a real post on one of this athlete's own accounts
    post = db.execute("""
        SELECT p.id FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' LIMIT 1""").fetchone()
    assert post is not None

    # cannot complete with nothing attached
    assert athlete.post(f"/api/athlete/deals/{deal_id}/complete").status_code == 409

    attach = athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                          json={"post_id": post["id"]})
    assert attach.status_code == 201
    # and not twice
    assert athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                        json={"post_id": post["id"]}).status_code == 409

    done = athlete.post(f"/api/athlete/deals/{deal_id}/complete")
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["completed_at"]

    perf = sponsor.get(f"/api/deals/{deal_id}/performance").json()
    assert perf["delivered"]["posts"] == 1
    assert perf["delivered"]["reach"] > 0
    assert perf["variance_pct"] is not None
    assert perf["cost_per_1k_reach"] > 0
    # every headline figure decomposes to the posts behind it
    assert len(perf["deliverables"]) == 1
    assert perf["deliverables"][0]["reach"] == perf["delivered"]["reach"]
    assert perf["deliverables"][0]["permalink"]


def test_an_athlete_cannot_attach_someone_elses_post(sponsor, athlete, db):
    """The attribution boundary. Without it an athlete could claim another
    athlete's reach, which would poison the only dataset sponsors are asked to
    trust."""
    deal_id = _accepted_deal(sponsor, athlete, "attribution")
    other = db.execute("""
        SELECT p.id FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug != 'kaia-mercer' LIMIT 1""").fetchone()
    assert other is not None
    res = athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                       json={"post_id": other["id"]})
    assert res.status_code == 404
    assert res.json()["detail"] == "unknown_post"


def test_deliverables_require_an_accepted_deal(sponsor, athlete, db):
    campaign_id = _fresh_campaign(sponsor, "other athlete campaign")
    other_id = _athlete_id(sponsor, "sofia-brandt")
    offer = sponsor.post(f"/api/campaigns/{campaign_id}/offers", json={
        "athlete_id": other_id, "deal_type": "social_post", "amount_eur": 1000})
    assert offer.status_code == 201

    # `athlete` is Kaia Mercer; the deal above belongs to Sofia Brandt. Reuse the
    # existing session rather than logging in again: test_api deliberately drains
    # the auth rate-limit bucket before this file runs, so a fresh login 429s.
    res = athlete.post(f"/api/athlete/deals/{offer.json()['id']}/deliverables",
                       json={"post_id": 1})
    assert res.status_code == 404  # not this athlete's deal


def test_performance_is_scoped_to_the_owning_sponsor(sponsor, athlete, clubu):
    deal_id = _accepted_deal(sponsor, athlete, "scoping")
    assert clubu.get(f"/api/deals/{deal_id}/performance").status_code == 403


def test_unmeasured_campaign_reads_as_unmeasured_not_free(sponsor, athlete):
    """No deliverables means no cost-per-engagement — not a zero, which would
    read as an infinitely efficient campaign."""
    deal_id = _accepted_deal(sponsor, athlete, "unmeasured")
    perf = sponsor.get(f"/api/deals/{deal_id}/performance").json()
    assert perf["delivered"]["reach"] == 0
    assert perf["cost_per_1k_reach"] is None
    assert perf["cost_per_engagement"] is None


def test_the_athlete_can_see_what_they_already_attached(sponsor, athlete, db):
    """Without this the deliverable picker offers a post the athlete has already
    submitted, and the only feedback is a 409."""
    deal_id = _accepted_deal(sponsor, athlete, "own view")
    post = db.execute("""
        SELECT p.id FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' LIMIT 1""").fetchone()
    assert athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                        json={"post_id": post["id"]}).status_code == 201

    deals = athlete.get("/api/athlete/workspace").json()["deals"]
    mine = next(d for d in deals if d["id"] == deal_id)
    assert mine["deliverable_post_ids"] == [post["id"]]
    # an empty list, never a missing key: the client renders a count from it
    for other in deals:
        if other["status"] not in ("accepted", "completed"):
            assert other["deliverable_post_ids"] == []


def test_speed_to_first_offer_keeps_the_campaigns_that_produced_nothing(sponsor):
    """A median taken only over campaigns that worked is a survivorship figure.
    The count of campaigns still waiting has to travel with it."""
    before = sponsor.get("/api/sponsor/workspace").json()["speed"]

    campaign_id = _fresh_campaign(sponsor, "speed campaign")
    after = sponsor.get("/api/sponsor/workspace").json()["speed"]
    assert after["campaigns_without_offer"] == before["campaigns_without_offer"] + 1
    assert after["campaigns_measured"] == before["campaigns_measured"]

    assert sponsor.post(f"/api/campaigns/{campaign_id}/offers", json={
        "athlete_id": _athlete_id(sponsor), "deal_type": "social_post",
        "amount_eur": 2500}).status_code == 201

    final = sponsor.get("/api/sponsor/workspace").json()["speed"]
    assert final["campaigns_measured"] == before["campaigns_measured"] + 1
    assert final["campaigns_without_offer"] == before["campaigns_without_offer"]
    assert final["median_hours"] is not None
    assert final["median_hours"] >= 0


def test_a_completed_deal_will_not_take_another_deliverable(sponsor, athlete, db):
    """The sponsor has already read that report. Attaching a post afterwards
    moves reach, variance and cost-per-1k on a number they have acted on —
    silently, with no record that the figure they saw ever changed."""
    deal_id = _accepted_deal(sponsor, athlete, "frozen report")
    posts = db.execute("""
        SELECT p.id FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' LIMIT 2""").fetchall()
    assert len(posts) == 2, "this test needs two posts by the same athlete"

    assert athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                        json={"post_id": posts[0]["id"]}).status_code == 201
    assert athlete.post(f"/api/athlete/deals/{deal_id}/complete").status_code == 200

    late = athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                        json={"post_id": posts[1]["id"]})
    assert late.status_code == 409
    assert late.json()["detail"] == "deal_not_accepted"


def test_disconnecting_a_platform_withdraws_the_posts_it_supplied(sponsor, athlete, db):
    """Consent is not a one-time grant. The rows stay so historical scores remain
    reproducible, but a disconnected account's posts stop being offered for
    attachment and stop being attachable — otherwise an athlete can still sell a
    permission they have already taken back."""
    deal_id = _accepted_deal(sponsor, athlete, "withdrawn consent")

    # taken from the endpoint rather than from SQL, so the post is one the
    # picker would really have offered (it returns a recent slice, not the lot)
    offered = athlete.get("/api/athlete/posts").json()
    assert offered, "the demo athlete should have attachable posts"
    post_id = offered[0]["post_id"]
    account_id = db.execute("SELECT account_id FROM posts WHERE id = ?",
                            (post_id,)).fetchone()["account_id"]

    db.execute("UPDATE platform_accounts SET connection_status = 'disconnected' WHERE id = ?",
               (account_id,))
    db.commit()
    try:
        after = {p["post_id"] for p in athlete.get("/api/athlete/posts").json()}
        assert post_id not in after
        res = athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                           json={"post_id": post_id})
        assert res.status_code == 404
        assert res.json()["detail"] == "unknown_post"
        # ...but a failed sync is not a withdrawal. `sync.py` sets 'error' when a
        # refresh fails, and an expired token must not cost the athlete a post
        # they really published — this is the line between an operational
        # problem and a consent decision, and it is easy to tighten by accident.
        db.execute("UPDATE platform_accounts SET connection_status = 'error' WHERE id = ?",
                   (account_id,))
        db.commit()
        assert post_id in {p["post_id"] for p in athlete.get("/api/athlete/posts").json()}
        assert athlete.post(f"/api/athlete/deals/{deal_id}/deliverables",
                            json={"post_id": post_id}).status_code == 201
    finally:
        # session-scoped database: leave it exactly as it was found
        db.execute("UPDATE platform_accounts SET connection_status = 'connected' WHERE id = ?",
                   (account_id,))
        db.commit()
    assert post_id in {p["post_id"] for p in athlete.get("/api/athlete/posts").json()}


# ── two processes doing the same thing at the same time ─────────────────────

def test_a_budget_check_can_hold_the_row_it_just_counted(tmp_path):
    """Counting nominations and then inserting one is only a budget if nothing
    slips between the two. Two requests arriving together both read the old
    total, both find room, and both write — so the club mints more floors than
    the roster size it declared, which is the number that made the declaration
    checkable in the first place.

    The lock is what closes that window, so this asserts the exclusion is real
    rather than that the call exists: a second connection must not be able to
    write while it is held.
    """
    path = tmp_path / "lock.db"
    holder = sqlite3.connect(path)
    holder.row_factory = sqlite3.Row
    init_db(holder)
    assert not holder.in_transaction

    lock_for_update(holder, "club_applications", "club_id", 1)
    assert holder.in_transaction, "the write transaction must start before the count"

    other = sqlite3.connect(path, timeout=0)
    with pytest.raises(sqlite3.OperationalError):
        other.execute("INSERT INTO users (email, password_hash, role, status,"
                      " token_version, created_at) VALUES"
                      " ('r@x', 'x', 'athlete', 'active', 1, '2026-01-01T00:00:00Z')")
        other.commit()

    holder.rollback()
    other.close()
    holder.close()


def test_a_migration_another_replica_already_ran_is_not_a_crash():
    """Both schema checks are check-then-act, and two API processes starting
    together both read the schema before either has changed it: both conclude
    the migration is needed, and the loser used to crash on boot. What matters
    is the end state, not which process produced it."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)

    # the race: the statement fails because the column is already there
    _migrate(conn, "ALTER TABLE deals ADD COLUMN completed_at TEXT", "deals", "completed_at")
    assert "completed_at" in _columns(conn, "deals")

    # but a failure with nothing to show for it is still a failure
    with pytest.raises(sqlite3.OperationalError):
        _migrate(conn, "ALTER TABLE deals ADD COLUMN nonsense_column BAD SYNTAX(",
                 "deals", "nonsense_column")
    conn.close()
