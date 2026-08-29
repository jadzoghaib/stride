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
    piles up in every later feed. Both tables are *restored* rather than
    emptied, because the seed legitimately puts rows in each of them -- the demo
    clubs really do have members, and the demo athletes really do have a wall.
    A blanket DELETE would quietly strip the seeded wall for every test that
    ran afterwards, which is a failure that would surface far from its cause.
    """
    def snapshot(table):
        return {r["id"]: dict(r) for r in rows(db, f"SELECT * FROM {table}")}

    def restore(table, saved):
        """Delete what the test made; put back what it changed.

        Not delete-and-reinsert: `id` is GENERATED ALWAYS on Postgres, so
        writing one back is an error there and silently fine on SQLite -- the
        kind of divergence that only shows up in the other backend's CI job.
        Keeping the rows also keeps their ids, which `content_items.part_of`
        points at.
        """
        if saved:
            keep = tuple(saved)
            db.execute(f"DELETE FROM {table} WHERE id NOT IN"
                       f" ({', '.join('?' for _ in keep)})", keep)
        else:
            db.execute(f"DELETE FROM {table}")
        for row_id, saved_row in saved.items():
            cols = [c for c in saved_row if c != "id"]
            db.execute(f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)}"
                       f" WHERE id = ?", tuple(saved_row[c] for c in cols) + (row_id,))

    before = {t: snapshot(t) for t in ("club_members", "content_items")}
    yield
    for table in ("content_items", "club_members"):
        restore(table, before[table])
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


# ── the wall's other half ─────────────────────────────────────────

def test_the_wall_carries_platform_posts_before_anything_is_published(client):
    """A profile has to be worth opening on day one.

    Nothing here has been published in Stride, and the wall is still not empty:
    it carries what the athlete already posts on their own platforms, which is
    the same data the score is computed from.
    """
    news = client.get("/api/athletes/kaia-mercer/news").json()
    assert news, "a connected athlete has a wall before they write anything"
    assert all({"platform", "title", "published_at", "permalink"} <= set(n) for n in news)
    dates = [n["published_at"] for n in news]
    assert dates == sorted(dates, reverse=True), "newest first"


def test_the_public_wall_shows_no_metrics(client):
    """Reach is the athlete's analytics and the sponsor's evidence. A fan gets
    the post, not the numbers behind it."""
    news = client.get("/api/athletes/kaia-mercer/news").json()
    leaked = {k for n in news for k in n} & {"reach", "impressions", "likes", "comments",
                                             "shares", "saves", "engagement_rate"}
    assert leaked == set(), f"metrics on a public wall: {leaked}"


def test_disconnecting_a_platform_empties_its_half_of_the_wall(client, db):
    """RULE 4 on a surface it did not previously reach.

    `own_posts` already honoured this; the public wall is newer, and is exactly
    the place where continuing to show withdrawn data would be worst.
    """
    account = row(db, """
        SELECT pa.id, pa.platform FROM platform_accounts pa
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' AND pa.connection_status = 'connected' LIMIT 1""")
    before = {n["platform"] for n in client.get("/api/athletes/kaia-mercer/news").json()}
    assert account["platform"] in before

    db.execute("UPDATE platform_accounts SET connection_status = 'disconnected' WHERE id = ?",
               (account["id"],))
    db.commit()
    try:
        # counting rows would prove nothing: the wall is capped at `limit`, and
        # the remaining platforms simply fill the gap. The claim is about which
        # platform is allowed to supply it.
        after = {n["platform"] for n in
                 client.get("/api/athletes/kaia-mercer/news", params={"limit": 60}).json()}
        assert account["platform"] not in after, "a withdrawn platform still fed the wall"
        assert after, "and the others still do"
    finally:
        db.execute("UPDATE platform_accounts SET connection_status = 'connected' WHERE id = ?",
                   (account["id"],))
        db.commit()


def test_an_athlete_with_nothing_connected_has_an_empty_wall_not_an_error(client, db):
    db.execute("UPDATE athlete_profiles SET creatorlens_creator_id = NULL WHERE slug = 'lena-virtanen'")
    db.commit()
    res = client.get("/api/athletes/lena-virtanen/news")
    assert res.status_code == 200 and res.json() == []


def test_the_wall_of_an_unknown_athlete_is_a_404(client):
    assert client.get("/api/athletes/nobody-at-all/news").status_code == 404
