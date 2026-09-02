"""A request you cannot answer is a dead end.

Every request in this product — a club's invitation, a sponsor's offer, a fan's
wall post — is a person asking somebody for something. A notification that says
so and offers no route to the detail or back to the asker leaves the reader
knowing they have been asked and unable to respond, which is the state the
`actor` column exists to end.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows


def _newest(session, kind: str) -> dict | None:
    for n in session.get("/api/notifications?limit=100").json()["items"]:
        if n["kind"] == kind:
            return n
    return None


def test_an_invitation_names_the_club_and_points_at_the_invitation(clubu, athlete, db):
    """It used to point at `/athlete` — the dashboard — and carry nobody."""
    db.execute("DELETE FROM club_members WHERE athlete_id ="
               " (SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer')")
    db.commit()
    made = clubu.post("/api/club/members",
                      json={"athlete_slug": "kaia-mercer", "position": "Track"})
    assert made.status_code == 201, made.text

    note = _newest(athlete, "invitation")
    assert note is not None
    assert note["link"] == "/athlete/clubs", "the invitation is on My clubs, not the dashboard"
    assert note["actor"] is not None, "a club invited them; the club is the actor"
    assert note["actor"]["role"] == "club"
    assert note["actor"]["can_message"] is True


def test_an_offer_names_the_sponsor(sponsor, athlete, db):
    campaign = row(db, "SELECT c.id FROM campaigns c JOIN sponsor_orgs o ON o.id = c.org_id"
                       " JOIN users u ON u.id = o.user_id WHERE u.email = 'sponsor@demo.stride'")
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    db.execute("DELETE FROM deals WHERE campaign_id = ? AND athlete_id = ? AND status = 'offered'",
               (campaign["id"], kaia["id"]))
    db.commit()

    sent = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": kaia["id"], "deal_type": "social_post",
        "amount_eur": 1234, "message": "A question you can ask about."})
    assert sent.status_code == 201, sent.text

    note = _newest(athlete, "offer")
    assert note["link"] == "/athlete/deals"
    assert note["actor"]["role"] == "sponsor"
    assert note["actor"]["can_message"] is True


def test_a_wall_post_names_the_fan(fan, athlete, db):
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    fan.post(f"/api/follows/{kaia['id']}")
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "Great race."})

    note = _newest(athlete, "fan_post")
    assert note["link"] == "/athletes/kaia-mercer"
    assert note["actor"]["role"] == "fan"


def test_a_subscription_has_somewhere_to_go(fan, athlete, db):
    """This one carried an empty link: the single notification about a person
    paying you was the only one you could not act on."""
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")
    db.execute("DELETE FROM subscriptions WHERE athlete_id = ?", (kaia["id"],))
    db.commit()
    fan.post(f"/api/subscriptions/athlete/{kaia['id']}")

    note = _newest(athlete, "subscriber")
    assert note is not None
    assert note["link"], "a notification with no destination is a dead end"
    assert note["actor"]["role"] == "fan"


def test_the_system_speaking_for_itself_has_no_actor(athlete2):
    """An admission decision is raised by the policy. There is nobody to reply
    to, and inventing one would put a reply control on a machine."""
    for note in athlete2.get("/api/notifications?limit=100").json()["items"]:
        if note["kind"].startswith("admission."):
            assert note["actor"] is None
            return
    pytest.skip("no admission notification on this account")


def test_the_reply_control_is_never_a_refusal_in_waiting(athlete, db):
    """`can_message` has to agree with what sending actually does.

    The envelope is only drawn where the server said a message would be
    accepted; a control whose sole outcome is a 403 is worse than no control.
    """
    notes = [n for n in athlete.get("/api/notifications?limit=100").json()["items"]
             if n["actor"]]
    assert notes, "the tests above raised notifications with actors"

    checked = 0
    for note in notes[:6]:
        actor = note["actor"]
        sent = athlete.post("/api/messages",
                            json={"to_user": actor["id"], "body": "Checking the reply right."})
        if actor["can_message"]:
            assert sent.status_code == 201, \
                f"claimed messageable, got {sent.status_code}: {sent.text}"
        else:
            assert sent.status_code == 403, \
                f"claimed unmessageable, got {sent.status_code}"
        checked += 1
    assert checked


def test_nobody_is_their_own_correspondent(athlete, db):
    """An athlete posting on their own wall notifies nobody, but the general
    rule matters: a notification you caused yourself offers no reply."""
    for note in athlete.get("/api/notifications?limit=100").json()["items"]:
        if note["actor"]:
            me = row(db, "SELECT id FROM users WHERE email = 'athlete@demo.stride'")
            assert note["actor"]["id"] != me["id"]


def test_an_invitation_carries_enough_to_answer_it(clubu, athlete, db):
    """Details, on the surface where the answer is given."""
    db.execute("DELETE FROM club_members WHERE athlete_id ="
               " (SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer')")
    db.commit()
    clubu.post("/api/club/members", json={"athlete_slug": "kaia-mercer", "position": "Track"})

    invitations = athlete.get("/api/athlete/invitations").json()
    assert invitations
    inv = invitations[0]
    for field in ("name", "sport", "country", "region", "bio", "position",
                  "roster_count", "package_count", "player_direct_for_me"):
        assert field in inv, f"missing {field}"
    assert inv["club_user_id"], "the club's user, so the athlete can ask rather than only answer"
    assert inv["roster_count"] >= 0
