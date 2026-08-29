"""Content, and the consent a club now needs before it can claim an athlete.

Both were found by using the product rather than by reading it: an athlete had
nowhere to publish anything, and a club could put any listed athlete on its
roster without asking — which matters because player-direct sponsorship packages
are sold against roster membership.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows


@pytest.fixture(autouse=True)
def clean_slate(db):
    """Put the roster and the content library back after each test.

    The database is session-scoped, and both subjects here are cumulative: an
    accepted invitation makes the next invitation a 409, and published content
    piles up in every later feed. Restoring the seeded rosters rather than
    deleting everything, because the demo clubs really do have members.
    """
    before = [dict(r) for r in rows(db, "SELECT * FROM club_members")]
    yield
    db.execute("DELETE FROM content_items")
    db.execute("DELETE FROM club_members")
    for m in before:
        keys = [k for k in m if k != "id"]
        db.execute(f"INSERT INTO club_members ({', '.join(keys)}) VALUES"
                   f" ({', '.join('?' for _ in keys)})", tuple(m[k] for k in keys))
    db.commit()


# ── content ─────────────────────────────────────────────────────────────────

def test_an_athlete_can_publish_and_a_stranger_sees_only_the_free_part(athlete, client, db):
    """The paywall, without a payment: the body is what a locked item withholds,
    and everything a reader needs in order to decide to pay stays visible."""
    free = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Race report: Montseny",
        "body": "Splits, and what went wrong on the descent.", "min_tier": ""})
    assert free.status_code == 201, free.text
    paid = athlete.post("/api/athlete/content", json={
        "kind": "course", "title": "12-week hill block",
        "body": "Week one: two sessions, both easy.", "min_tier": "insider"})
    assert paid.status_code == 201, paid.text

    for item in (free, paid):
        assert athlete.post(f"/api/content/{item.json()['id']}/publish").status_code == 200

    # the author sees their own bodies
    mine = athlete.get("/api/athlete/content").json()
    assert all(i["body"] for i in mine)

    seen = client.get("/api/athletes/kaia-mercer/content").json()
    by_title = {i["title"]: i for i in seen}

    open_one = by_title["Race report: Montseny"]
    assert open_one["locked"] is False
    assert "descent" in open_one["body"]

    shut = by_title["12-week hill block"]
    assert shut["locked"] is True
    assert shut["body"] == ""              # the only thing withheld
    assert shut["title"] and shut["kind"] == "course"
    assert shut["tier_label"] == "Insider · €9.99"   # and what it would take


def test_a_draft_is_not_published(athlete, client):
    athlete.post("/api/athlete/content", json={"kind": "post", "title": "Half-written"})
    titles = [i["title"] for i in client.get("/api/athletes/kaia-mercer/content").json()]
    assert "Half-written" not in titles


def test_sponsored_content_has_to_name_the_sponsor(athlete):
    """`sponsored` is a disclosure obligation, not a badge."""
    res = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "New shoes", "label": "sponsored"})
    assert res.status_code == 422
    assert res.json()["detail"] == "sponsored_needs_sponsor_name"

    ok = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "New shoes", "label": "sponsored", "sponsor_name": "Northwind"})
    assert ok.status_code == 201


def test_the_scarce_kinds_need_a_date(athlete):
    """A session or an event without a time is not a thing anyone can attend —
    and scarcity is the whole argument for pricing them above a post."""
    for kind in ("session", "event"):
        res = athlete.post("/api/athlete/content", json={"kind": kind, "title": "Come train"})
        assert res.status_code == 422, kind
        assert res.json()["detail"] == "scheduled_content_needs_a_date"

    ok = athlete.post("/api/athlete/content", json={
        "kind": "event", "title": "Come train with me", "min_tier": "inner_circle",
        "starts_at": "2027-03-14T09:00:00Z", "location": "Montseny", "capacity": 8})
    assert ok.status_code == 201
    assert ok.json()["capacity"] == 8


def test_a_course_part_cannot_be_hung_off_someone_elses_course(athlete, clubu):
    """Otherwise a course is a way to attach your content to another author."""
    mine = athlete.post("/api/athlete/content", json={
        "kind": "course", "title": "My course"}).json()
    theirs = clubu.post("/api/club/content", json={
        "kind": "course", "title": "Club course"}).json()

    ok = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Week 1", "part_of": mine["id"], "position": 1})
    assert ok.status_code == 201

    bad = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Week 1", "part_of": theirs["id"]})
    assert bad.status_code == 403
    assert bad.json()["detail"] == "not_your_course"


def test_content_belongs_to_its_author(athlete, clubu):
    theirs = clubu.post("/api/club/content", json={"kind": "post", "title": "Club post"}).json()
    assert athlete.post(f"/api/content/{theirs['id']}/publish").status_code == 404
    assert athlete.delete(f"/api/content/{theirs['id']}").status_code == 404


def test_deleting_a_course_with_parts_is_refused(athlete):
    course = athlete.post("/api/athlete/content", json={
        "kind": "course", "title": "Block"}).json()
    athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Week 1", "part_of": course["id"]})
    res = athlete.delete(f"/api/content/{course['id']}")
    assert res.status_code == 409
    assert res.json()["detail"] == "course_has_parts"


def test_the_free_feed_carries_followed_athletes_content(fan, athlete):
    """The free layer: what a fan opens the app for between paid drops."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Easy week", "body": "Recovery.", "min_tier": ""}).json()
    athlete.post(f"/api/content/{made['id']}/publish")

    feed = fan.get("/api/feed/content").json()
    assert any(i["title"] == "Easy week" and i["author_slug"] == "kaia-mercer" for i in feed)


# ── the roster is a request, not an assertion ───────────────────────────────

def test_a_club_cannot_put_an_athlete_on_its_roster_unilaterally(clubu, db):
    """A club used to write `active` straight into the roster. Player-direct
    sponsorship packages are sold against roster membership, so that let a club
    claim an athlete and monetise their audience while the athlete found out by
    looking at their own profile."""
    res = clubu.post("/api/club/members", json={"athlete_slug": "sofia-brandt", "position": "Runner"})
    assert res.status_code == 201

    membership = row(db, """
        SELECT cm.status FROM club_members cm JOIN athlete_profiles a ON a.id = cm.athlete_id
        WHERE a.slug = 'sofia-brandt'""")
    assert membership["status"] == "invited", "an invitation is not a membership"

    # and the guard that matters still refuses
    packages = clubu.post("/api/club/packages", json={
        "name": "Sofia direct", "package_type": "player_direct", "price_eur": 5000,
        "description": "x", "athlete_slug": "sofia-brandt", "perks": []})
    assert packages.status_code == 409
    assert packages.json()["detail"] == "athlete_not_on_roster"


def test_the_athlete_decides(athlete, clubu, db):
    invite = clubu.post("/api/club/members",
                        json={"athlete_slug": "kaia-mercer", "position": "Distance"})
    assert invite.status_code == 201

    pending = athlete.get("/api/athlete/invitations").json()
    assert len(pending) == 1 and pending[0]["name"] == "Meridian FC"

    accepted = athlete.post(f"/api/athlete/invitations/{pending[0]['invitation_id']}/respond",
                            json={"action": "accept"})
    assert accepted.status_code == 200 and accepted.json()["status"] == "active"
    assert athlete.get("/api/athlete/invitations").json() == []

    # and it cannot be answered twice
    again = athlete.post(f"/api/athlete/invitations/{pending[0]['invitation_id']}/respond",
                         json={"action": "accept"})
    assert again.status_code == 409


def test_declining_leaves_the_club_without_a_member(athlete, clubu, db):
    clubu.post("/api/club/members", json={"athlete_slug": "kaia-mercer"})
    pending = athlete.get("/api/athlete/invitations").json()
    athlete.post(f"/api/athlete/invitations/{pending[0]['invitation_id']}/respond",
                 json={"action": "decline"})

    active = rows(db, """
        SELECT cm.id FROM club_members cm JOIN athlete_profiles a ON a.id = cm.athlete_id
        WHERE a.slug = 'kaia-mercer' AND cm.status = 'active'""")
    assert active == []


def test_an_invitation_can_only_be_answered_by_its_athlete(athlete, clubu, db):
    clubu.post("/api/club/members", json={"athlete_slug": "sofia-brandt"})
    theirs = row(db, """
        SELECT cm.id FROM club_members cm JOIN athlete_profiles a ON a.id = cm.athlete_id
        WHERE a.slug = 'sofia-brandt' AND cm.status = 'invited'""")
    res = athlete.post(f"/api/athlete/invitations/{theirs['id']}/respond",
                       json={"action": "accept"})
    assert res.status_code == 404
