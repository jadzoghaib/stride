"""The fan wall: the one surface on an athlete's page they do not write.

A profile with only broadcast on it is a brochure. The wall is the part where
other people are — and therefore the part that needs a rule about who may
write, because an open write surface on the page of somebody with an audience
is a spam target.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows


@pytest.fixture(autouse=True)
def clean_slate(db):
    def snapshot(table):
        return {r["id"]: dict(r) for r in rows(db, f"SELECT * FROM {table}")}

    def restore(table, saved):
        if saved:
            keep = tuple(saved)
            db.execute(f"DELETE FROM {table} WHERE id NOT IN"
                       f" ({', '.join('?' for _ in keep)})", keep)
        else:
            db.execute(f"DELETE FROM {table}")

    tables = ("fan_posts", "follows", "notifications")
    before = {t: snapshot(t) for t in tables}
    yield
    for table in tables:
        restore(table, before[table])
    db.commit()


def _kaia(db):
    return row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")["id"]


def test_you_have_to_follow_before_you_can_post(fan, db):
    """Low bar, deliberately: charging for the right to say "good race" would be
    a strange thing to sell. But it is a choice somebody made, and can undo."""
    db.execute("DELETE FROM follows WHERE athlete_id = ?", (_kaia(db),))
    db.commit()

    shut = fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "Great run!"})
    assert shut.status_code == 403
    assert shut.json()["detail"] == "follow_first"

    fan.post(f"/api/follows/{_kaia(db)}")
    assert fan.post("/api/athletes/kaia-mercer/wall-posts",
                    json={"body": "Great run!"}).status_code == 201


def test_the_wall_is_public(fan, client, db):
    fan.post(f"/api/follows/{_kaia(db)}")
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "Been following since 2023"})

    seen = client.get("/api/athletes/kaia-mercer/wall-posts").json()
    # The seed puts a couple of posts on this wall, so this asserts its own is
    # there rather than that the wall is exactly one long -- a test that owns
    # the whole list breaks the moment the demo gains a second voice.
    mine = [p for p in seen if p["body"] == "Been following since 2023"]
    assert len(mine) == 1
    assert mine[0]["author"], "a wall post says who wrote it"
    assert all(p["can_remove"] is False for p in seen), "a signed-out reader removes nothing"


def test_an_athlete_can_post_on_their_own_wall_without_following_themselves(athlete):
    assert athlete.post("/api/athletes/kaia-mercer/wall-posts",
                        json={"body": "Thanks all — full report tomorrow."}).status_code == 201


def test_the_athlete_can_remove_anything_on_their_wall(fan, athlete, db):
    """Their name is on the page."""
    fan.post(f"/api/follows/{_kaia(db)}")
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "spam spam spam"})
    post = row(db, "SELECT id FROM fan_posts ORDER BY id DESC LIMIT 1")

    assert athlete.delete(f"/api/wall-posts/{post['id']}").status_code == 200
    assert rows(db, "SELECT id FROM fan_posts WHERE id = ?", (post["id"],)) == []


def test_an_author_can_remove_their_own(fan, db):
    fan.post(f"/api/follows/{_kaia(db)}")
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "wrong athlete, sorry"})
    post = row(db, "SELECT id FROM fan_posts ORDER BY id DESC LIMIT 1")
    assert fan.delete(f"/api/wall-posts/{post['id']}").status_code == 200


def test_a_stranger_removes_nothing_and_is_not_told_it_exists(fan, sponsor, db):
    """404 rather than 403: a post you may not touch should not be confirmed by
    the shape of the refusal."""
    fan.post(f"/api/follows/{_kaia(db)}")
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "mine"})
    post = row(db, "SELECT id FROM fan_posts ORDER BY id DESC LIMIT 1")
    assert sponsor.delete(f"/api/wall-posts/{post['id']}").status_code == 404


def test_a_wall_post_notifies_the_athlete(fan, athlete, db):
    fan.post(f"/api/follows/{_kaia(db)}")
    before = athlete.get("/api/notifications").json()["unread"]
    fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "See you at Montseny"})
    after = athlete.get("/api/notifications").json()
    assert after["unread"] == before + 1
    assert after["items"][0]["kind"] == "fan_post"


def test_an_athlete_posting_on_their_own_wall_does_not_notify_themselves(athlete):
    before = athlete.get("/api/notifications").json()["unread"]
    athlete.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "hello"})
    assert athlete.get("/api/notifications").json()["unread"] == before


def test_an_unknown_athlete_has_no_wall(fan):
    assert fan.get("/api/athletes/nobody-here/wall-posts").status_code == 404
    assert fan.post("/api/athletes/nobody-here/wall-posts",
                    json={"body": "hi"}).status_code == 404


def test_an_empty_post_is_refused(fan, db):
    """Including one that is only spaces: `min_length` counts those, so "   "
    validated and was stored as a blank card on somebody's public page."""
    fan.post(f"/api/follows/{_kaia(db)}")
    assert fan.post("/api/athletes/kaia-mercer/wall-posts",
                    json={"body": ""}).status_code == 422
    blank = fan.post("/api/athletes/kaia-mercer/wall-posts", json={"body": "   "})
    assert blank.status_code == 422
    assert blank.json()["detail"] == "empty_post"
