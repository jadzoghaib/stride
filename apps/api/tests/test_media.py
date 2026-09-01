"""Uploading a picture, and everything the endpoint refuses.

An upload endpoint is a place a stranger writes bytes to your disk and later
asks you to serve them back. The tests worth having are the refusals.
"""

from __future__ import annotations

import pytest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


@pytest.fixture(autouse=True)
def _media_dir(tmp_path, monkeypatch):
    """A directory per test, so nothing written here survives into the next."""
    from stride_api.config import settings
    monkeypatch.setattr(settings, "media_dir", tmp_path / "media")
    yield


def test_an_athlete_can_upload_a_picture_and_read_it_back(athlete, client):
    made = athlete.post("/api/media", files={"file": ("shot.png", PNG, "image/png")})
    assert made.status_code == 201, made.text
    body = made.json()
    assert body["media_kind"] == "image"
    assert body["media_url"].startswith("/api/media/")

    # public: this is what a post's picture points at
    served = client.get(body["media_url"])
    assert served.status_code == 200
    assert served.content == PNG


def test_the_client_never_names_the_file(athlete):
    """A stored name is ours, not theirs. Otherwise an upload proposes the path
    it is written to, and `.js` from our own origin is a script we host."""
    made = athlete.post("/api/media", files={
        "file": ("../../evil.js", PNG, "image/png")}).json()
    assert "evil" not in made["media_url"]
    assert ".." not in made["media_url"]
    assert made["media_url"].endswith(".png")


def test_the_bytes_have_to_match_the_declared_type(athlete):
    """A whitelist of content types is a promise from whoever is uploading.
    Sniffing the header checks it -- this is an HTML file wearing image/png."""
    res = athlete.post("/api/media", files={
        "file": ("x.png", b"<html><script>alert(1)</script></html>", "image/png")})
    assert res.status_code == 422
    assert res.json()["detail"] == "content_does_not_match_its_type"


def test_an_unsupported_type_is_refused(athlete):
    res = athlete.post("/api/media", files={"file": ("x.svg", b"<svg/>", "image/svg+xml")})
    assert res.status_code == 422
    assert res.json()["detail"] == "unsupported_media_type"


def test_an_empty_file_is_refused(athlete):
    res = athlete.post("/api/media", files={"file": ("x.png", b"", "image/png")})
    assert res.status_code == 422


def test_a_file_over_the_ceiling_is_refused(athlete, monkeypatch):
    from stride_api.config import settings
    monkeypatch.setattr(settings, "max_upload_bytes", 1024)
    res = athlete.post("/api/media", files={
        "file": ("big.jpg", JPEG + b"\x00" * 4096, "image/jpeg")})
    assert res.status_code == 413


def test_only_authors_upload(client, fan, sponsor, athlete, clubu):
    """Fans and sponsors have nothing to publish, so they have no reason to be
    able to write files to our disk."""
    for who in (fan, sponsor):
        assert who.post("/api/media",
                        files={"file": ("x.png", PNG, "image/png")}).status_code == 403
    assert client.post("/api/media",
                       files={"file": ("x.png", PNG, "image/png")}).status_code == 401
    for who in (athlete, clubu):
        assert who.post("/api/media",
                        files={"file": ("x.png", PNG, "image/png")}).status_code == 201


def test_a_crafted_path_cannot_walk_out_of_the_media_directory(client):
    """Matched against the shape we generate rather than sanitised: a list of
    things to strip is only ever as good as the list."""
    for name in ("../../../etc/passwd", "..%2f..%2fsecret", "not-a-token.png",
                 "short.png", "x" * 20 + ".exe"):
        assert client.get(f"/api/media/{name}").status_code in (404, 400)


def test_a_post_can_carry_an_uploaded_picture(athlete, client):
    """The whole point: the upload becomes a post's media, end to end."""
    uploaded = athlete.post("/api/media", files={"file": ("s.jpg", JPEG, "image/jpeg")}).json()
    made = athlete.post("/api/athlete/content", json={
        "kind": "post", "title": "From my camera roll", "body": "Race morning.",
        "media_url": uploaded["media_url"], "media_kind": uploaded["media_kind"]})
    assert made.status_code == 201, made.text
    athlete.post(f"/api/content/{made.json()['id']}/publish")

    seen = {i["title"]: i for i in client.get("/api/athletes/kaia-mercer/content").json()}
    assert seen["From my camera roll"]["media_url"] == uploaded["media_url"]
    assert client.get(uploaded["media_url"]).status_code == 200
