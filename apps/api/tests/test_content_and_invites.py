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

    # children before parents: poll rows reference content_items, and a delete
    # in the wrong order fails the whole restore, leaves the transaction open,
    # and locks the database for whichever test runs next
    tables = ("poll_votes", "poll_options", "content_items", "club_members",
              "subscriptions", "follows")
    before = {t: snapshot(t) for t in tables}
    yield
    for table in tables:
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
    assert shut["tier_label"] == "Subscribers"       # and what it would take


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


# ── following buys the free tier ────────────────────────────────────────────


def test_the_follower_feed_carries_platform_posts(fan, db):
    """Following is the *free* tier, and an athlete's public platform posts are
    the largest part of what that is.

    Leaving them out meant a fan who followed four athletes saw only what those
    four had published inside Stride — which on a young profile is nothing, so
    the tier that exists to keep fans coming back was empty for exactly them.
    """
    from stride_api.db import row, rows
    feed = fan.get("/api/feed/news").json()
    assert feed, "the seeded fan follows athletes with synced accounts"

    followed = {r["slug"] for r in rows(db, """
        SELECT a.slug FROM athlete_profiles a
        JOIN follows f ON f.athlete_id = a.id WHERE f.user_id = ?""",
        (row(db, "SELECT id FROM users WHERE email = 'fan@demo.stride'")["id"],))}
    assert {p["author_slug"] for p in feed} <= followed,         "the feed must not carry an athlete this reader does not follow"

    # more than one athlete, which is the whole reason the card needs an author
    assert len({p["author_slug"] for p in feed}) > 1
    assert all(p["author"] for p in feed)


def test_the_follower_feed_is_newest_first(fan):
    feed = fan.get("/api/feed/news").json()
    stamps = [p["published_at"] for p in feed]
    assert stamps == sorted(stamps, reverse=True)


def test_a_follower_gets_the_post_and_not_the_numbers_behind_it(fan):
    """Reach and engagement are the athlete's own analytics and the sponsor's
    evidence. A fan gets the post."""
    for p in fan.get("/api/feed/news").json():
        assert not ({"reach", "impressions", "likes", "engagement_rate"} & set(p))


def test_disconnecting_a_platform_withdraws_it_from_the_follower_feed(fan, athlete, db):
    """The consent rule, on the second surface that has to honour it. The rows
    stay so scores remain reproducible; they stop being shown."""
    from stride_api.db import row
    before = [p for p in fan.get("/api/feed/news").json() if p["author_slug"] == "kaia-mercer"]
    assert before, "kaia is followed and has synced posts"
    platform = before[0]["platform"]

    account = row(db, """
        SELECT pa.id FROM platform_accounts pa
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' AND pa.platform = ?""", (platform,))
    db.execute("UPDATE platform_accounts SET connection_status = 'disconnected' WHERE id = ?",
               (account["id"],))
    db.commit()
    try:
        after = fan.get("/api/feed/news").json()
        assert not [p for p in after
                    if p["author_slug"] == "kaia-mercer" and p["platform"] == platform]
    finally:
        db.execute("UPDATE platform_accounts SET connection_status = 'connected' WHERE id = ?",
                   (account["id"],))
        db.commit()


def test_a_club_cannot_read_the_follower_feed(clubu, client):
    """A club cannot follow anybody, so the permission would buy an empty list —
    and a grant that leads nowhere gets copied to the next endpoint as if it
    meant something."""
    assert clubu.get("/api/feed/news").status_code == 403
    assert client.get("/api/feed/news").status_code == 401


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


# ── products: the one kind Stride does not deliver ────────────────────────

def test_a_product_needs_a_link(athlete):
    """Merch lives on Shopify or Amazon. Without the link the row is a
    photograph of a t-shirt."""
    res = athlete.post("/api/athlete/content", json={"kind": "product", "title": "Team tee"})
    assert res.status_code == 422
    assert res.json()["detail"] == "product_needs_a_link"


def test_a_product_link_has_to_be_openable(athlete):
    """Structural check only -- the same one admission proofs use. It never
    resolves or fetches the URL, so a form field cannot become a request from
    our network."""
    res = athlete.post("/api/athlete/content", json={
        "kind": "product", "title": "Team tee", "external_url": "not a url"})
    assert res.status_code == 422
    assert res.json()["detail"] == "product_link_is_not_openable"


def test_a_product_cannot_be_locked(athlete):
    """The store takes the money and the store is public. Locking the link
    behind a Stride tier would hide a page anyone can already reach."""
    res = athlete.post("/api/athlete/content", json={
        "kind": "product", "title": "Team tee", "min_tier": "insider",
        "external_url": "https://shop.example/tee"})
    assert res.status_code == 422
    assert res.json()["detail"] == "a_product_cannot_be_locked"


def test_only_a_product_carries_a_link(athlete):
    """Otherwise every post becomes a place to park an outbound link, which is
    the shape spam takes on a creator platform."""
    res = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Read this", "external_url": "https://shop.example/tee"})
    assert res.status_code == 422
    assert res.json()["detail"] == "only_a_product_takes_a_link"


def test_a_published_product_reaches_a_stranger_with_its_link(athlete, client):
    made = athlete.post("/api/athlete/content", json={
        "kind": "product", "title": "Trail cap", "body": "Cotton, one size.",
        "external_url": "https://shop.example/trail-cap"})
    assert made.status_code == 201, made.text
    athlete.post(f"/api/content/{made.json()['id']}/publish")

    seen = [i for i in client.get("/api/athletes/kaia-mercer/content").json()
            if i["title"] == "Trail cap"]
    assert len(seen) == 1
    item = seen[0]
    assert item["locked"] is False, "a product is never locked"
    assert item["external_url"] == "https://shop.example/trail-cap"
    assert item["body"] == "Cotton, one size."


# ── editing ───────────────────────────────────────────────────

def test_a_product_link_can_be_corrected(athlete):
    """The update used to leave `external_url` alone, so a moved store link
    silently kept pointing at the old page -- the request succeeded and nothing
    changed, which is the worst way for an edit to fail."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "product", "title": "Trail cap",
        "external_url": "https://old-shop.example/cap"}).json()

    edited = athlete.post(f"/api/content/{made['id']}", json={
        "kind": "product", "title": "Trail cap (restocked)",
        "external_url": "https://new-shop.example/cap"})
    assert edited.status_code == 200, edited.text
    assert edited.json()["external_url"] == "https://new-shop.example/cap"
    assert edited.json()["title"] == "Trail cap (restocked)"


def test_editing_keeps_the_item_and_its_place_in_a_course(athlete, db):
    """Delete-and-recreate would have been the alternative, and it loses the id
    a course part hangs off."""
    course = athlete.post("/api/athlete/content", json={
        "kind": "course", "title": "Block"}).json()
    part = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Week 1", "part_of": course["id"], "position": 1}).json()

    athlete.post(f"/api/content/{part['id']}", json={
        "kind": "post", "title": "Week 1: easy volume", "position": 1})

    after = row(db, "SELECT * FROM content_items WHERE id = ?", (part["id"],))
    assert after["title"] == "Week 1: easy volume"
    assert after["part_of"] == course["id"], "the edit kept it in its course"


def test_editing_does_not_publish(athlete):
    """Status is a separate decision. A save that also published would make the
    edit button the most dangerous control on the page."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Half-written"}).json()
    assert made["status"] == "draft"
    edited = athlete.post(f"/api/content/{made['id']}", json={
        "kind": "post", "title": "Still half-written"}).json()
    assert edited["status"] == "draft"


def test_you_cannot_edit_someone_elses_item(athlete, clubu):
    theirs = clubu.post("/api/club/content", json={"kind": "post", "title": "Club post"}).json()
    res = athlete.post(f"/api/content/{theirs['id']}", json={"kind": "post", "title": "Mine now"})
    assert res.status_code == 404


def test_a_scheduled_time_is_stored_as_one_canonical_instant(athlete, db):
    """`2027-03-14T09:00` is not a moment in time, and storing it meant the
    event drifted by the reader's offset every time it was saved."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "event", "title": "Trail morning",
        "starts_at": "2027-03-14T09:00:00+02:00"}).json()
    assert made["starts_at"] == "2027-03-14T07:00:00Z", "normalised to UTC"

    stored = row(db, "SELECT starts_at FROM content_items WHERE id = ?", (made["id"],))
    assert stored["starts_at"] == "2027-03-14T07:00:00Z"

    # and saving again does not move it
    again = athlete.post(f"/api/content/{made['id']}", json={
        "kind": "event", "title": "Trail morning", "starts_at": made["starts_at"]}).json()
    assert again["starts_at"] == "2027-03-14T07:00:00Z"


def test_a_time_without_a_zone_is_refused(athlete):
    """The server does not know the author's offset, and guessing one is how a
    session ends up an hour out for everybody who did not create it."""
    res = athlete.post("/api/athlete/content", json={
        "kind": "event", "title": "Trail morning", "starts_at": "2027-03-14T09:00"})
    assert res.status_code == 422
    assert res.json()["detail"] == "starts_at_needs_a_timezone"


def test_a_time_that_is_not_a_time_is_refused(athlete):
    res = athlete.post("/api/athlete/content", json={
        "kind": "event", "title": "Trail morning", "starts_at": "next tuesday"})
    assert res.status_code == 422
    assert res.json()["detail"] == "starts_at_is_not_a_time"


# ── follow is free, subscribe opens the lock ─────────────────────────

def _published(author, **fields):
    made = author.post("/api/athlete/content", json=fields)
    assert made.status_code == 201, made.text
    author.post(f"/api/content/{made.json()['id']}/publish")
    return made.json()["id"]


def test_subscribing_opens_that_authors_locked_posts(athlete, fan, db):
    """The lock used to be permanent: `_visible_tier` answered "free" for
    everybody, so a subscribers-only post could be shown but never opened."""
    _published(athlete, kind="post", title="Members only", body="The good stuff.",
               min_tier="supporter")

    before = {i["title"]: i for i in fan.get("/api/athletes/kaia-mercer/content").json()}
    assert before["Members only"]["locked"] is True
    assert before["Members only"]["body"] == ""

    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    assert fan.post(f"/api/subscriptions/athlete/{kaia['id']}").status_code == 201

    after = {i["title"]: i for i in fan.get("/api/athletes/kaia-mercer/content").json()}
    assert after["Members only"]["locked"] is False
    assert after["Members only"]["body"] == "The good stuff."

    assert fan.delete(f"/api/subscriptions/athlete/{kaia['id']}").status_code == 200
    again = {i["title"]: i for i in fan.get("/api/athletes/kaia-mercer/content").json()}
    assert again["Members only"]["locked"] is True, "unsubscribing closes it again"


def test_a_subscription_opens_one_author_not_all_of_them(athlete, clubu, fan, db):
    """The lock is per author. Paying one person does not open everyone."""
    _published(athlete, kind="post", title="Athlete members only", min_tier="supporter",
               body="Mine.")
    theirs = clubu.post("/api/club/content", json={
        "kind": "post", "title": "Club members only", "min_tier": "supporter",
        "body": "Ours."}).json()
    clubu.post(f"/api/content/{theirs['id']}/publish")

    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    fan.post(f"/api/subscriptions/athlete/{kaia['id']}")
    try:
        mine = {i["title"]: i for i in fan.get("/api/athletes/kaia-mercer/content").json()}
        club = {i["title"]: i for i in fan.get("/api/clubs/meridian-fc/content").json()}
        assert mine["Athlete members only"]["locked"] is False
        assert club["Club members only"]["locked"] is True, "a different author stays shut"
    finally:
        fan.delete(f"/api/subscriptions/athlete/{kaia['id']}")


def test_a_signed_out_reader_sees_the_free_layer_only(athlete, client):
    _published(athlete, kind="post", title="Open to all", body="Read away.", min_tier="")
    _published(athlete, kind="post", title="Shut to all", body="Not this.",
               min_tier="supporter")
    seen = {i["title"]: i for i in client.get("/api/athletes/kaia-mercer/content").json()}
    assert seen["Open to all"]["locked"] is False and seen["Open to all"]["body"]
    assert seen["Shut to all"]["locked"] is True and seen["Shut to all"]["body"] == ""


def test_following_does_not_open_the_lock(athlete, fan, db):
    """Follow and subscribe are different relationships, and the whole point of
    naming them differently is that one of them does not pay."""
    _published(athlete, kind="post", title="Paywalled", body="x", min_tier="supporter")
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    fan.post(f"/api/follows/{kaia['id']}")
    seen = {i["title"]: i for i in fan.get("/api/athletes/kaia-mercer/content").json()}
    assert seen["Paywalled"]["locked"] is True


# ── media and polls ────────────────────────────────────────────

def test_a_post_can_carry_a_picture(athlete, client):
    made = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Race day", "body": "Cold start.",
        "media_url": "https://picsum.photos/seed/x/800/500", "media_kind": "image"})
    assert made.status_code == 201, made.text
    athlete.post(f"/api/content/{made.json()['id']}/publish")
    seen = {i["title"]: i for i in client.get("/api/athletes/kaia-mercer/content").json()}
    assert seen["Race day"]["media_kind"] == "image"
    assert seen["Race day"]["media_url"].startswith("https://")


def test_media_needs_a_kind_and_a_kind_needs_media(athlete):
    no_kind = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "x", "media_url": "https://example.com/a.jpg"})
    assert no_kind.status_code == 422 and no_kind.json()["detail"] == "media_needs_a_kind"

    no_url = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "x", "media_kind": "image"})
    assert no_url.status_code == 422 and no_url.json()["detail"] == "media_kind_without_a_link"

    bad = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "x", "media_url": "not a url", "media_kind": "image"})
    assert bad.status_code == 422 and bad.json()["detail"] == "media_link_is_not_openable"


def test_a_poll_needs_at_least_two_distinct_options(athlete):
    """One answer is a statement, and two identical answers is one answer."""
    one = athlete.post("/api/athlete/content", json={
        "kind": "poll", "title": "Next block?", "options": ["Hills"]})
    assert one.status_code == 422 and one.json()["detail"] == "a_poll_needs_two_options"

    same = athlete.post("/api/athlete/content", json={
        "kind": "poll", "title": "Next block?", "options": ["Hills", "Hills"]})
    assert same.status_code == 422 and same.json()["detail"] == "poll_options_must_differ"

    blank = athlete.post("/api/athlete/content", json={
        "kind": "poll", "title": "Next block?", "options": ["Hills", "   "]})
    assert blank.status_code == 422, "a blank option is not a choice"


def test_only_a_poll_takes_options(athlete):
    res = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "x", "options": ["a", "b"]})
    assert res.status_code == 422 and res.json()["detail"] == "only_a_poll_takes_options"


def test_voting_is_one_per_person_and_changeable(athlete, fan, db):
    made = athlete.post("/api/athlete/content", json={
        "kind": "poll", "title": "Next block?", "min_tier": "",
        "options": ["Hills", "Track", "Trails"]}).json()
    athlete.post(f"/api/content/{made['id']}/publish")

    first = fan.post(f"/api/content/{made['id']}/vote/{made and 0}")
    assert first.status_code == 404, "an option that is not on this poll is refused"

    options = {o["label"]: o["id"] for o in
               fan.get("/api/athletes/kaia-mercer/content").json()[0]["poll"]["options"]}
    voted = fan.post(f"/api/content/{made['id']}/vote/{options['Hills']}").json()
    assert voted["total"] == 1 and voted["voted"] == options["Hills"]

    changed = fan.post(f"/api/content/{made['id']}/vote/{options['Track']}").json()
    assert changed["total"] == 1, "changing a vote does not add one"
    assert changed["voted"] == options["Track"]
    assert rows(db, "SELECT id FROM poll_votes WHERE content_id = ?", (made["id"],)).__len__() == 1


def test_a_locked_poll_cannot_be_voted_in(athlete, fan, db):
    """The options are part of what the subscription buys, so a reader who
    cannot see the result must not be able to shape it."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "poll", "title": "Members poll", "min_tier": "supporter",
        "options": ["Yes", "No"]}).json()
    athlete.post(f"/api/content/{made['id']}/publish")
    option = row(db, "SELECT id FROM poll_options WHERE content_id = ? ORDER BY position",
                 (made["id"],))
    res = fan.post(f"/api/content/{made['id']}/vote/{option['id']}")
    assert res.status_code == 403 and res.json()["detail"] == "subscribe_to_vote"

    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    fan.post(f"/api/subscriptions/athlete/{kaia['id']}")
    try:
        assert fan.post(f"/api/content/{made['id']}/vote/{option['id']}").status_code == 200
    finally:
        fan.delete(f"/api/subscriptions/athlete/{kaia['id']}")


def test_a_locked_post_does_not_leak_its_picture(athlete, client):
    """Blurring an image in the browser is not a paywall: the file is still
    served, and the original is one right-click away."""
    made = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "Behind the scenes", "body": "The full story.",
        "min_tier": "supporter", "media_url": "https://picsum.photos/seed/y/800/500",
        "media_kind": "image"}).json()
    athlete.post(f"/api/content/{made['id']}/publish")

    seen = {i["title"]: i for i in client.get("/api/athletes/kaia-mercer/content").json()}
    shut = seen["Behind the scenes"]
    assert shut["locked"] is True
    assert shut["media_url"] == "", "the address is withheld with the body"
    assert shut["has_media"] is True, "but the reader is told there is something there"
