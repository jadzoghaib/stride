"""Who may open a conversation, and what arrives without being asked for.

The permission rule is the whole feature. An inbox anyone can write into is a
spam surface aimed at exactly the people with the most followers, so every test
here is about refusing rather than delivering.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows


@pytest.fixture(autouse=True)
def clean_slate(db):
    """Threads and notifications accumulate, and both are counted in assertions."""
    def snapshot(table):
        return {r["id"]: dict(r) for r in rows(db, f"SELECT * FROM {table}")}

    def restore(table, saved):
        if saved:
            keep = tuple(saved)
            db.execute(f"DELETE FROM {table} WHERE id NOT IN"
                       f" ({', '.join('?' for _ in keep)})", keep)
        else:
            db.execute(f"DELETE FROM {table}")

    tables = ("messages", "conversations", "notifications", "subscriptions", "deals",
              "club_members", "package_commitments")
    before = {t: snapshot(t) for t in tables}
    yield
    for table in tables:          # messages before conversations: the child first
        restore(table, before[table])
    db.commit()


def _athlete_id(db, slug="kaia-mercer"):
    return row(db, "SELECT id FROM athlete_profiles WHERE slug = ?", (slug,))["id"]


# ── the rule ────────────────────────────────────────────────────────────────

def test_an_athlete_may_message_anyone(athlete, db):
    sponsor_user = row(db, "SELECT id FROM users WHERE email = 'sponsor@demo.stride'")["id"]
    fan_user = row(db, "SELECT id FROM users WHERE email = 'fan@demo.stride'")["id"]
    for target in ({"to_club": "meridian-fc"}, {"to_club": "ironline-combat"},
                   {"to_user": sponsor_user}, {"to_user": fan_user}):
        res = athlete.post("/api/messages", json={"body": "Hello", **target})
        assert res.status_code == 201, (target, res.text)


def test_an_athlete_with_no_account_cannot_be_messaged(athlete, sponsor):
    """Most directory profiles are unclaimed -- scraped or seeded, with nobody
    behind them. There is no inbox to deliver to, and the envelope knows it."""
    assert athlete.post("/api/messages", json={
        "to_athlete": "amara-diallo", "body": "Hello"}).status_code == 404
    assert sponsor.get("/api/messages/can/athlete/amara-diallo").json()["can_message"] is False
    assert sponsor.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is True


def test_a_sponsor_may_message_any_athlete(sponsor):
    assert sponsor.post("/api/messages", json={
        "to_athlete": "kaia-mercer", "body": "We have a campaign"}).status_code == 201


def test_a_sponsor_may_not_message_a_club_they_do_not_back(sponsor):
    """Sponsors reach athletes because that is what they are here for. A club is
    a counterparty, and the relationship has to exist first."""
    refused = sponsor.post("/api/messages", json={"to_club": "meridian-fc", "body": "Hi"})
    assert refused.status_code == 403
    assert refused.json()["detail"] == "cannot_message_this_person"


def test_a_fan_may_message_only_the_athletes_they_subscribe_to(fan, db):
    kaia = _athlete_id(db)
    shut = fan.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Hi"})
    assert shut.status_code == 403, "following is not subscribing"

    fan.post(f"/api/subscriptions/athlete/{kaia}")
    assert fan.post("/api/messages", json={
        "to_athlete": "kaia-mercer", "body": "Hi"}).status_code == 201

    # and only them: the club is claimed, so this is a permission refusal
    # rather than a missing recipient
    assert fan.post("/api/messages", json={
        "to_club": "meridian-fc", "body": "Hi"}).status_code == 403


def test_unsubscribing_keeps_the_thread_but_closes_the_door(fan, db):
    """Reply rights come from the thread, not from the role -- otherwise a
    conversation could be opened that the other side cannot answer. But a fan
    who leaves cannot start a new one."""
    kaia = _athlete_id(db)
    fan.post(f"/api/subscriptions/athlete/{kaia}")
    assert fan.post("/api/messages", json={"to_athlete": "kaia-mercer",
                                           "body": "First"}).status_code == 201
    fan.delete(f"/api/subscriptions/athlete/{kaia}")

    assert fan.post("/api/messages", json={"to_athlete": "kaia-mercer",
                                           "body": "Second"}).status_code == 201
    assert fan.post("/api/messages", json={"to_club": "meridian-fc",
                                           "body": "New"}).status_code == 403


def test_nobody_may_message_themselves(athlete):
    res = athlete.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Hi"})
    assert res.status_code == 403


def test_the_envelope_is_only_offered_where_the_send_would_work(fan, sponsor, db):
    """The button asks the server, so it cannot appear where sending is refused."""
    assert fan.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is False
    fan.post(f"/api/subscriptions/athlete/{_athlete_id(db)}")
    assert fan.get("/api/messages/can/athlete/kaia-mercer").json()["can_message"] is True
    assert sponsor.get("/api/messages/can/club/meridian-fc").json()["can_message"] is False


# ── the thread ──────────────────────────────────────────────────────────────

def test_a_pair_has_one_thread_whoever_opened_it(athlete, sponsor, db):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "From the sponsor"})
    athlete.post("/api/messages", json={"to_user": row(
        db, "SELECT id FROM users WHERE email = 'sponsor@demo.stride'")["id"],
        "body": "From the athlete"})
    threads = athlete.get("/api/inbox").json()
    with_sponsor = [t for t in threads if t["with"]["role"] == "sponsor"]
    assert len(with_sponsor) == 1, "one conversation, not one per direction"

    full = athlete.get(f"/api/inbox/{with_sponsor[0]['id']}").json()
    assert [m["mine"] for m in full["messages"]] == [False, True]


def test_a_thread_you_are_not_in_is_a_404(athlete, sponsor, fan):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Private"})
    thread_id = athlete.get("/api/inbox").json()[0]["id"]
    assert fan.get(f"/api/inbox/{thread_id}").status_code == 404


def test_reading_a_thread_clears_its_unread_count(athlete, sponsor):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Unread"})
    thread = athlete.get("/api/inbox").json()[0]
    assert thread["unread"] == 1
    athlete.get(f"/api/inbox/{thread['id']}")
    assert athlete.get("/api/inbox").json()[0]["unread"] == 0


# ── notifications ───────────────────────────────────────────────────────────

def test_an_offer_notifies_the_athlete(athlete, sponsor, db):
    kaia = _athlete_id(db)
    campaign = row(db, "SELECT c.id FROM campaigns c JOIN sponsor_orgs o ON o.id = c.org_id"
                       " JOIN users u ON u.id = o.user_id WHERE u.email = 'sponsor@demo.stride'")
    # The seed already has an open offer here and a second one is correctly
    # refused, so close it first. The fixture puts the deals table back.
    db.execute("UPDATE deals SET status = 'withdrawn' WHERE campaign_id = ? AND athlete_id = ?",
               (campaign["id"], kaia))
    db.commit()

    before = athlete.get("/api/notifications").json()["unread"]
    sent = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": kaia, "deal_type": "social_post", "amount_eur": 4321,
        "message": "notification probe"})
    assert sent.status_code == 201, sent.text
    after = athlete.get("/api/notifications").json()
    assert after["unread"] == before + 1
    assert after["items"][0]["kind"] == "offer"


def test_a_message_notifies_its_recipient_and_reading_clears_it(athlete, sponsor):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Ping"})
    feed = athlete.get("/api/notifications").json()
    assert feed["unread"] >= 1
    assert feed["items"][0]["kind"] == "message"
    athlete.post("/api/notifications/read")
    assert athlete.get("/api/notifications").json()["unread"] == 0


def test_notifications_are_private_to_their_owner(athlete, sponsor):
    sponsor.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Only for them"})
    res = sponsor.get("/api/notifications")
    assert res.status_code == 200, res.text
    mine = res.json()
    assert all("messaged you" not in i["title"] for i in mine["items"])


# -- clubs, along the relationships they already have -------------------------

def _member(db, slug: str, status: str) -> None:
    club = row(db, "SELECT id FROM clubs WHERE slug = 'meridian-fc'")
    athlete = row(db, "SELECT id FROM athlete_profiles WHERE slug = ?", (slug,))
    db.execute("DELETE FROM club_members WHERE club_id = ? AND athlete_id = ?",
               (club["id"], athlete["id"]))
    db.execute("INSERT INTO club_members (club_id, athlete_id, position, status, joined_at)"
               " VALUES (?, ?, '', ?, '2026-01-01T00:00:00Z')",
               (club["id"], athlete["id"], status))
    db.commit()


def test_a_club_may_message_an_athlete_it_has_invited(db, clubu):
    """The gap this closes: a club that cannot explain the invitation it just
    sent. The invitation already reached them, so this is not new reach."""
    _member(db, "kaia-mercer", "invited")
    assert clubu.post("/api/messages", json={
        "to_athlete": "kaia-mercer", "body": "We would love to have you"}).status_code == 201


def test_a_club_may_message_an_athlete_on_its_roster(db, clubu):
    _member(db, "kaia-mercer", "active")
    assert clubu.post("/api/messages", json={
        "to_athlete": "kaia-mercer", "body": "Training moved to Thursday"}).status_code == 201


def test_a_club_may_not_message_an_athlete_who_declined(db, clubu):
    """Ending the relationship ends new outreach. Somebody who said no should
    not keep receiving pitches about it."""
    _member(db, "kaia-mercer", "declined")
    refused = clubu.post("/api/messages", json={"to_athlete": "kaia-mercer", "body": "Reconsider?"})
    assert refused.status_code == 403


def test_a_club_may_not_message_an_athlete_it_has_no_relationship_with(db, clubu):
    club = row(db, "SELECT id FROM clubs WHERE slug = 'meridian-fc'")
    athlete = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    db.execute("DELETE FROM club_members WHERE club_id = ? AND athlete_id = ?",
               (club["id"], athlete["id"]))
    db.commit()
    assert clubu.post("/api/messages", json={
        "to_athlete": "kaia-mercer", "body": "Hello"}).status_code == 403


def _commitment(db, status: str) -> None:
    package = row(db, "SELECT cp.id FROM club_packages cp JOIN clubs c ON c.id = cp.club_id"
                      " WHERE c.slug = 'meridian-fc' LIMIT 1")
    org = row(db, "SELECT o.id FROM sponsor_orgs o JOIN users u ON u.id = o.user_id"
                  " WHERE u.email = 'sponsor@demo.stride'")
    db.execute("DELETE FROM package_commitments WHERE package_id = ? AND org_id = ?",
               (package["id"], org["id"]))
    db.execute("INSERT INTO package_commitments (package_id, org_id, amount_eur, status,"
               " created_at) VALUES (?, ?, 1000, ?, '2026-01-01T00:00:00Z')",
               (package["id"], org["id"], status))
    db.commit()


def test_a_club_and_the_sponsor_backing_it_can_reach_each_other(db, clubu, sponsor):
    """Money has changed hands. Letting only one of them type first would be
    arbitrary."""
    _commitment(db, "active")
    assert clubu.post("/api/messages", json={
        "to_user": row(db, "SELECT id FROM users WHERE email = 'sponsor@demo.stride'")["id"],
        "body": "Thanks for backing the shirt package"}).status_code == 201
    assert sponsor.get("/api/messages/can/club/meridian-fc").json()["can_message"] is True


def test_a_cancelled_commitment_closes_the_door(db, clubu, sponsor):
    """The thread they already have stays answerable; new ones do not open."""
    _commitment(db, "cancelled")
    sponsor_user = row(db, "SELECT id FROM users WHERE email = 'sponsor@demo.stride'")["id"]
    assert clubu.post("/api/messages", json={
        "to_user": sponsor_user, "body": "Renew?"}).status_code == 403
    assert sponsor.get("/api/messages/can/club/meridian-fc").json()["can_message"] is False
