"""An athlete's own cover and profile picture.

The interesting part is not the upload — `test_media.py` covers that — but what
the profile will accept as a *reference* to one. These two fields are rendered
on a public page, so a value here is a request every visitor's browser makes.
"""

from __future__ import annotations

import pytest

from stride_api.db import row

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _media_dir(tmp_path, monkeypatch):
    from stride_api.config import settings
    monkeypatch.setattr(settings, "media_dir", tmp_path / "media")
    yield


@pytest.fixture(autouse=True)
def _clean(db):
    yield
    db.execute("UPDATE athlete_profiles SET avatar_url = '', cover_url = ''"
               " WHERE slug = 'kaia-mercer'")
    db.commit()


def _upload(athlete) -> str:
    made = athlete.post("/api/media", files={"file": ("me.png", PNG, "image/png")})
    assert made.status_code == 201, made.text
    return made.json()["media_url"]


def test_an_athlete_sets_their_own_picture_and_cover(athlete, client):
    url = _upload(athlete)
    assert athlete.put("/api/athlete/profile",
                       json={"avatar_url": url, "cover_url": url}).status_code == 200

    seen = client.get("/api/athletes/kaia-mercer").json()
    assert seen["avatar_url"] == url
    assert seen["cover_url"] == url
    # and a visitor can actually load it
    assert client.get(url).status_code == 200


def test_the_photo_fields_only_accept_our_own_media(athlete):
    """A profile picture is fetched by every visitor's browser. Accepting a
    foreign URL would turn each profile view into a request to a server of the
    athlete's choosing, carrying the reader's IP and referrer — an open
    tracking pixel with a face on it."""
    for bad in ("https://evil.example/pixel.png",
                "//evil.example/pixel.png",
                "http://localhost:9/x.png",
                "javascript:alert(1)",
                "data:image/png;base64,iVBORw0KGgo=",
                "/api/media/../../etc/passwd",
                "/api/media/short.png",
                "/api/media/abcdefghij0123456789.svg",
                "/etc/passwd"):
        refused = athlete.put("/api/athlete/profile", json={"avatar_url": bad})
        assert refused.status_code == 422, f"accepted {bad!r}"
        assert refused.json()["detail"] == "not_a_media_path"


def test_the_refusal_does_not_quietly_keep_the_old_value(athlete, client):
    """A rejected write must leave the field as it was, not half-applied."""
    url = _upload(athlete)
    athlete.put("/api/athlete/profile", json={"avatar_url": url})
    athlete.put("/api/athlete/profile",
                json={"avatar_url": "https://evil.example/x.png", "bio": "changed"})

    seen = client.get("/api/athletes/kaia-mercer").json()
    assert seen["avatar_url"] == url, "the good value survived the refused one"
    assert seen["bio"] != "changed", "nothing in a refused request is applied"


def test_empty_goes_back_to_the_drawn_art(athlete, client):
    """Removing a photograph is a real state, not a missing one: the client
    draws a cover and an avatar from the name, so a profile without pictures is
    finished rather than blank."""
    url = _upload(athlete)
    athlete.put("/api/athlete/profile", json={"avatar_url": url, "cover_url": url})
    assert athlete.put("/api/athlete/profile",
                       json={"avatar_url": "", "cover_url": ""}).status_code == 200

    seen = client.get("/api/athletes/kaia-mercer").json()
    assert seen["avatar_url"] == ""
    assert seen["cover_url"] == ""


def test_photos_are_public_but_only_the_owner_sets_them(athlete, fan, sponsor, client, db):
    url = _upload(athlete)
    athlete.put("/api/athlete/profile", json={"avatar_url": url})

    # anybody may see them — they are part of a public page
    assert client.get("/api/athletes/kaia-mercer").json()["avatar_url"] == url

    # and nobody else may set them: the route is the athlete's own profile
    for who in (fan, sponsor):
        assert who.put("/api/athlete/profile", json={"avatar_url": url}).status_code == 403


def test_an_unclaimed_profile_keeps_the_drawn_art(client, db):
    """Most seeded athletes have no account behind them, so nobody has uploaded
    anything. The field is empty rather than absent, so the client always has
    something defined to branch on."""
    unclaimed = row(db, "SELECT slug FROM athlete_profiles"
                        " WHERE user_id IS NULL AND status = 'listed' LIMIT 1")
    seen = client.get(f"/api/athletes/{unclaimed['slug']}").json()
    assert seen["avatar_url"] == ""
    assert seen["cover_url"] == ""
