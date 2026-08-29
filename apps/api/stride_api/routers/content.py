"""Content: what an athlete or a club publishes, and who can see it.

The specification is §4.3 of the business plan. The shape worth keeping in mind
while reading this file is that **the four kinds split into two groups**:

    post, course     unlimited — cost nothing to serve to one more fan
    session, event   scarce    — cost the author a Saturday

That difference is why events carry a time, a place and a capacity, and why they
are the argument for the top tier rather than just another perk.

**Nothing here charges money.** `min_tier` records what a fan would need, and
`locked` says whether they have it — which, with no subscriptions in the product
yet, is "no" for everything above free. That is deliberate: the lock is the
product, and showing it honestly is more useful than a stub that pretends to
sell. When entitlements arrive, `_visible_tier` is the only function that
changes.
"""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, optional_user, require_role
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api", tags=["content"])

KINDS = ("post", "course", "session", "event")
#: Ordered weakest to strongest. A fan sees an item when their tier is at least
#: its `min_tier`, so the comparison is an index into this tuple.
TIERS = ("", "supporter", "insider", "inner_circle")
TIER_LABEL = {
    "": "Free",
    "supporter": "Supporter · €4.99",
    "insider": "Insider · €9.99",
    "inner_circle": "Inner circle · €24.99",
}
LABELS = ("", "sponsored", "highlighted")
#: The kinds that are scarce, and therefore the ones a date and a place belong to.
SCHEDULED = ("session", "event")


class ContentIn(BaseModel):
    kind: str = Field(default="post", max_length=20)
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(default="", max_length=20000)
    min_tier: str = Field(default="", max_length=20)
    label: str = Field(default="", max_length=20)
    sponsor_name: str = Field(default="", max_length=120)
    part_of: int | None = None
    position: int | None = Field(default=None, ge=0, le=999)
    starts_at: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=160)
    capacity: int | None = Field(default=None, ge=1, le=100000)


def _validate(body: ContentIn) -> None:
    if body.kind not in KINDS:
        raise HTTPException(422, "unknown_content_kind")
    if body.min_tier not in TIERS:
        raise HTTPException(422, "unknown_tier")
    if body.label not in LABELS:
        raise HTTPException(422, "unknown_label")
    # A disclosure that does not name the advertiser is not a disclosure. The
    # database enforces this too; doing it here as well is what lets the client
    # say something useful instead of surfacing a constraint violation.
    if body.label == "sponsored" and not body.sponsor_name.strip():
        raise HTTPException(422, "sponsored_needs_sponsor_name")
    if body.kind in SCHEDULED and not body.starts_at.strip():
        raise HTTPException(422, "scheduled_content_needs_a_date")


def _own_athlete(conn, user) -> dict:
    a = row(conn, "SELECT * FROM athlete_profiles WHERE user_id = ?", (user["id"],))
    if a is None:
        raise HTTPException(404, "no_athlete_profile")
    return a


def _own_club(conn, user) -> dict:
    c = row(conn, "SELECT * FROM clubs WHERE user_id = ?", (user["id"],))
    if c is None:
        raise HTTPException(404, "no_club")
    return c


def _view(item: dict, *, locked: bool) -> dict:
    """One item as a reader sees it.

    A locked item keeps everything a fan needs in order to decide whether to
    pay — kind, title, tier, when and where an event is — and loses only the
    body. Hiding the title as well would make the paywall unsellable.
    """
    out = {k: item[k] for k in (
        "id", "kind", "title", "min_tier", "label", "sponsor_name",
        "part_of", "position", "starts_at", "location", "capacity",
        "status", "published_at",
    )}
    out["tier_label"] = TIER_LABEL.get(item["min_tier"], item["min_tier"])
    out["locked"] = locked
    out["body"] = "" if locked else item["body"]
    return out


def _visible_tier(user: dict | None) -> str:
    """The tier the reader has paid for.

    Everyone is on the free tier: there are no subscriptions in the product yet
    (P1 in the build sequence), so nothing above free unlocks for anybody. This
    is the single place that changes when entitlements ship.
    """
    return ""


def _locked(item: dict, viewer_tier: str) -> bool:
    return TIERS.index(item["min_tier"]) > TIERS.index(viewer_tier)


# ── the author's own library ────────────────────────────────────────────────

def _library(conn, *, athlete_id=None, club_id=None) -> list[dict]:
    where, params = ("athlete_id = ?", (athlete_id,)) if athlete_id else ("club_id = ?", (club_id,))
    items = rows(conn, f"SELECT * FROM content_items WHERE {where}"
                       " ORDER BY COALESCE(published_at, created_at) DESC, id DESC", params)
    # The author always sees their own bodies, published or not.
    return [_view(i, locked=False) for i in items]


@router.get("/athlete/content")
def athlete_content(user: dict = Depends(require_role("athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    return _library(conn, athlete_id=_own_athlete(conn, user)["id"])


@router.post("/athlete/content", status_code=201)
def create_athlete_content(body: ContentIn, user: dict = Depends(require_role("athlete")),
                           conn: sqlite3.Connection = Depends(get_db)):
    _validate(body)
    athlete = _own_athlete(conn, user)
    item_id = _insert(conn, body, athlete_id=athlete["id"])
    log_event(conn, "user", "content.created", "athlete", athlete["id"],
              {"content_id": item_id, "kind": body.kind, "min_tier": body.min_tier})
    conn.commit()
    return _view(row(conn, "SELECT * FROM content_items WHERE id = ?", (item_id,)), locked=False)


@router.get("/club/content")
def club_content(user: dict = Depends(require_role("club")),
                 conn: sqlite3.Connection = Depends(get_db)):
    return _library(conn, club_id=_own_club(conn, user)["id"])


@router.post("/club/content", status_code=201)
def create_club_content(body: ContentIn, user: dict = Depends(require_role("club")),
                        conn: sqlite3.Connection = Depends(get_db)):
    _validate(body)
    club = _own_club(conn, user)
    item_id = _insert(conn, body, club_id=club["id"])
    log_event(conn, "user", "content.created", "club", club["id"],
              {"content_id": item_id, "kind": body.kind, "min_tier": body.min_tier})
    conn.commit()
    return _view(row(conn, "SELECT * FROM content_items WHERE id = ?", (item_id,)), locked=False)


def _insert(conn, body: ContentIn, *, athlete_id=None, club_id=None) -> int:
    if body.part_of is not None:
        parent = row(conn, "SELECT * FROM content_items WHERE id = ?", (body.part_of,))
        # A part may only join a course, and only one of the author's own —
        # otherwise a course becomes a way to hang content off somebody else.
        if parent is None or parent["kind"] != "course":
            raise HTTPException(422, "part_of_must_be_a_course")
        if (athlete_id and parent["athlete_id"] != athlete_id) or \
           (club_id and parent["club_id"] != club_id):
            raise HTTPException(403, "not_your_course")
    cur = conn.execute(
        "INSERT INTO content_items (athlete_id, club_id, kind, title, body, min_tier, label,"
        " sponsor_name, part_of, position, starts_at, location, capacity, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (athlete_id, club_id, body.kind, body.title, body.body, body.min_tier, body.label,
         body.sponsor_name, body.part_of, body.position, body.starts_at or None,
         body.location, body.capacity, now_iso()))
    return cur.lastrowid


def _owned(conn, item_id: int, user: dict) -> dict:
    item = row(conn, "SELECT * FROM content_items WHERE id = ?", (item_id,))
    if item is None:
        raise HTTPException(404, "unknown_content")
    if user["role"] == "athlete":
        mine = row(conn, "SELECT id FROM athlete_profiles WHERE user_id = ?", (user["id"],))
        if not mine or item["athlete_id"] != mine["id"]:
            raise HTTPException(404, "unknown_content")
    else:
        mine = row(conn, "SELECT id FROM clubs WHERE user_id = ?", (user["id"],))
        if not mine or item["club_id"] != mine["id"]:
            raise HTTPException(404, "unknown_content")
    return item


@router.post("/content/{item_id}")
def update_content(item_id: int, body: ContentIn,
                   user: dict = Depends(require_role("athlete", "club")),
                   conn: sqlite3.Connection = Depends(get_db)):
    _validate(body)
    item = _owned(conn, item_id, user)
    conn.execute(
        "UPDATE content_items SET kind = ?, title = ?, body = ?, min_tier = ?, label = ?,"
        " sponsor_name = ?, position = ?, starts_at = ?, location = ?, capacity = ?"
        " WHERE id = ?",
        (body.kind, body.title, body.body, body.min_tier, body.label, body.sponsor_name,
         body.position, body.starts_at or None, body.location, body.capacity, item["id"]))
    conn.commit()
    return _view(row(conn, "SELECT * FROM content_items WHERE id = ?", (item["id"],)), locked=False)


@router.post("/content/{item_id}/publish")
def publish_content(item_id: int, user: dict = Depends(require_role("athlete", "club")),
                    conn: sqlite3.Connection = Depends(get_db)):
    item = _owned(conn, item_id, user)
    if item["status"] == "published":
        raise HTTPException(409, "already_published")
    conn.execute("UPDATE content_items SET status = 'published', published_at = ? WHERE id = ?",
                 (now_iso(), item["id"]))
    log_event(conn, "user", "content.published", "content", item["id"],
              {"kind": item["kind"], "min_tier": item["min_tier"]})
    conn.commit()
    return _view(row(conn, "SELECT * FROM content_items WHERE id = ?", (item["id"],)), locked=False)


@router.delete("/content/{item_id}")
def delete_content(item_id: int, user: dict = Depends(require_role("athlete", "club")),
                   conn: sqlite3.Connection = Depends(get_db)):
    item = _owned(conn, item_id, user)
    # A course with parts would leave them orphaned, pointing at nothing.
    if rows(conn, "SELECT id FROM content_items WHERE part_of = ?", (item["id"],)):
        raise HTTPException(409, "course_has_parts")
    conn.execute("DELETE FROM content_items WHERE id = ?", (item["id"],))
    log_event(conn, "user", "content.deleted", "content", item["id"], {"kind": item["kind"]})
    conn.commit()
    return {"ok": True}


# ── what a reader sees ──────────────────────────────────────────────────────

@router.get("/athletes/{slug}/content")
def public_athlete_content(slug: str, user: dict | None = Depends(optional_user),
                           conn: sqlite3.Connection = Depends(get_db)):
    athlete = row(conn, "SELECT id FROM athlete_profiles WHERE slug = ?", (slug,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    return _published(conn, "athlete_id = ?", (athlete["id"],), user)


@router.get("/clubs/{slug}/content")
def public_club_content(slug: str, user: dict | None = Depends(optional_user),
                        conn: sqlite3.Connection = Depends(get_db)):
    club = row(conn, "SELECT id FROM clubs WHERE slug = ?", (slug,))
    if club is None:
        raise HTTPException(404, "unknown_club")
    return _published(conn, "club_id = ?", (club["id"],), user)


def _published(conn, where: str, params: tuple, user: dict | None) -> list[dict]:
    tier = _visible_tier(user)
    items = rows(conn, f"SELECT * FROM content_items WHERE {where} AND status = 'published'"
                       " ORDER BY published_at DESC, id DESC", params)
    return [_view(i, locked=_locked(i, tier)) for i in items]


@router.get("/feed/content")
def followed_content(limit: int = Query(40, ge=1, le=200),
                     user: dict = Depends(require_role("fan", "sponsor", "athlete", "club")),
                     conn: sqlite3.Connection = Depends(get_db)):
    """Everything published by the athletes this reader follows.

    The free layer of §4.3: this is what a fan opens the app for between paid
    drops, and it costs almost nothing to build because the rows already exist.
    """
    tier = _visible_tier(user)
    items = rows(conn, """
        SELECT c.*, a.display_name AS author, a.slug AS author_slug
        FROM content_items c
        JOIN athlete_profiles a ON a.id = c.athlete_id
        JOIN follows f ON f.athlete_id = a.id
        WHERE f.user_id = ? AND c.status = 'published'
        ORDER BY c.published_at DESC, c.id DESC
        LIMIT ?""", (user["id"], limit))
    out = []
    for i in items:
        entry = _view(i, locked=_locked(i, tier))
        entry["author"] = i["author"]
        entry["author_slug"] = i["author_slug"]
        out.append(entry)
    return out
