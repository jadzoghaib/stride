"""User (fan) surface: discovery, follows, subscriptions, and the fan wall."""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, optional_user, require_role
from ..db import now_iso, row, rows
from .messaging import notify
from ..matching import fan_ranking
from .athletes import athlete_public

router = APIRouter(prefix="/api", tags=["discover"])


@router.get("/discover")
def discover(interests: str = Query("", description="comma-separated sports/topics"),
             country: str | None = None,
             q: str | None = Query(None, description="name search, athletes and clubs"),
             sport: str | None = None,
             kind: str = Query("all", pattern="^(all|athlete|club)$"),
             user: dict | None = Depends(optional_user),
             conn: sqlite3.Connection = Depends(get_db)):
    """One search across everything a reader can follow.

    Clubs used to live behind their own nav tab, which meant two places to look
    for the same thing and two sets of filters that did not agree. Name, sport,
    country and kind are the four questions a reader actually asks, and they are
    asked once here.
    """
    followed: set[int] = set()
    subscribed: set[int] = set()
    if user:
        followed = {r["athlete_id"] for r in
                    rows(conn, "SELECT athlete_id FROM follows WHERE user_id = ?", (user["id"],))}
        subscribed = {r["athlete_id"] for r in
                      rows(conn, "SELECT athlete_id FROM subscriptions"
                                 " WHERE user_id = ? AND athlete_id IS NOT NULL", (user["id"],))}
    interest_list = [i for i in (s.strip() for s in interests.split(",")) if i]
    ranked = fan_ranking(conn, interest_list, country, followed)
    out = []
    for r in ranked:
        entry = athlete_public(conn, r, viewer=user)
        entry["affinity"] = r["affinity"]
        entry["reasons"] = r["reasons"]
        entry["following"] = r["id"] in followed
        entry["subscribed"] = r["id"] in subscribed
        # Computed from what we already hold rather than asked per row: the rule
        # is role plus subscription plus "is there anybody behind this profile",
        # and all three are in hand.
        entry["can_message"] = bool(r["user_id"]) and user is not None and (
            user["role"] == "athlete"
            or user["role"] == "sponsor"
            or (user["role"] == "fan" and r["id"] in subscribed)) and r["user_id"] != user["id"]
        out.append(entry)

    def matches(name: str, a_sport: str, a_country: str) -> bool:
        if q and q.strip().lower() not in name.lower():
            return False
        if sport and a_sport.lower() != sport.lower():
            return False
        if country and a_country.lower() != country.lower():
            return False
        return True

    athletes = [a for a in out
                if matches(a["display_name"], a["sport"], a["country"])] if kind != "club" else []
    clubs = []
    if kind != "athlete":
        from .clubs import _club_public
        clubs = [_club_public(conn, c) for c in
                 rows(conn, "SELECT * FROM clubs WHERE status = 'listed' ORDER BY name")]
        clubs = [c for c in clubs if matches(c["name"], c["sport"], c["country"])]
    return {"athletes": athletes, "clubs": clubs}


@router.post("/follows/{athlete_id}", status_code=201)
def follow(athlete_id: int, user: dict = Depends(require_role("fan", "sponsor", "athlete")),
           conn: sqlite3.Connection = Depends(get_db)):
    athlete = row(conn, "SELECT id FROM athlete_profiles WHERE id = ? AND status = 'listed'",
                  (athlete_id,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    conn.execute("INSERT OR IGNORE INTO follows (user_id, athlete_id, created_at) VALUES (?, ?, ?)",
                 (user["id"], athlete_id, now_iso()))
    log_event(conn, "user", "athlete.followed", "athlete_profile", athlete_id,
              {"user_id": user["id"]})
    conn.commit()
    return {"ok": True}


@router.delete("/follows/{athlete_id}")
def unfollow(athlete_id: int, user: dict = Depends(require_role("fan", "sponsor", "athlete")),
             conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("DELETE FROM follows WHERE user_id = ? AND athlete_id = ?",
                 (user["id"], athlete_id))
    conn.commit()
    return {"ok": True}


@router.get("/feed")
def feed(user: dict = Depends(require_role("fan", "sponsor", "athlete")),
         conn: sqlite3.Connection = Depends(get_db)):
    """Followed athletes with their freshest signals: latest score movement and
    recent platform activity. Content posts are a later phase (docs/build-plan)."""
    athletes = rows(conn, """
        SELECT a.* FROM follows f JOIN athlete_profiles a ON a.id = f.athlete_id
        WHERE f.user_id = ? ORDER BY f.created_at DESC""", (user["id"],))
    out = []
    for a in athletes:
        entry = athlete_public(conn, a, viewer=user)
        if a["creatorlens_creator_id"]:
            history = rows(conn, """
                SELECT computed_at, audience_scale, engagement_quality, growth
                FROM score_snapshots WHERE creator_id = ?
                ORDER BY computed_at DESC, id DESC LIMIT 5""", (a["creatorlens_creator_id"],))
            entry["score_history"] = history[::-1]
        out.append(entry)
    return out


# ── follow vs subscribe ─────────────────────────────────────────
#
# Two different relationships, and conflating them was the reason every locked
# item stayed locked for everybody forever:
#
#   follow      the free layer -- their posts marked "everyone", and the news
#               from their own platforms. Costs nothing, asks nothing.
#   subscribe   the paid layer -- posts the author marked "subscribers only".
#
# There is no payments stack, so subscribing here is free and immediate. That is
# a demo decision, not a pricing one: what it buys is the ability to *show* the
# locked state resolving, which a paywall that never opens cannot.


def _subject(conn, kind: str, subject_id: int) -> dict:
    table, label = ("athlete_profiles", "unknown_athlete") if kind == "athlete"         else ("clubs", "unknown_club")
    found = row(conn, f"SELECT id FROM {table} WHERE id = ? AND status = 'listed'", (subject_id,))
    if found is None:
        raise HTTPException(404, label)
    return found


@router.post("/subscriptions/{kind}/{subject_id}", status_code=201)
def subscribe(kind: str, subject_id: int,
              user: dict = Depends(require_role("fan", "sponsor", "athlete")),
              conn: sqlite3.Connection = Depends(get_db)):
    if kind not in ("athlete", "club"):
        raise HTTPException(404, "unknown_subject")
    _subject(conn, kind, subject_id)
    column = "athlete_id" if kind == "athlete" else "club_id"
    conn.execute(f"INSERT OR IGNORE INTO subscriptions (user_id, {column}, created_at)"
                 " VALUES (?, ?, ?)", (user["id"], subject_id, now_iso()))
    table = "athlete_profiles" if kind == "athlete" else "clubs"
    owner = row(conn, f"SELECT user_id FROM {table} WHERE id = ?", (subject_id,))
    if owner and owner["user_id"]:
        notify(conn, owner["user_id"], "subscriber",
               f"{user['display_name']} subscribed to you",
               "They can now open everything you mark subscribers-only.", "")
    log_event(conn, "user", "subscription.started", kind, subject_id, {"user_id": user["id"]})
    conn.commit()
    return {"ok": True}


@router.delete("/subscriptions/{kind}/{subject_id}")
def unsubscribe(kind: str, subject_id: int,
                user: dict = Depends(require_role("fan", "sponsor", "athlete")),
                conn: sqlite3.Connection = Depends(get_db)):
    if kind not in ("athlete", "club"):
        raise HTTPException(404, "unknown_subject")
    column = "athlete_id" if kind == "athlete" else "club_id"
    conn.execute(f"DELETE FROM subscriptions WHERE user_id = ? AND {column} = ?",
                 (user["id"], subject_id))
    log_event(conn, "user", "subscription.ended", kind, subject_id, {"user_id": user["id"]})
    conn.commit()
    return {"ok": True}


# -- the fan wall ------------------------------------------------------------
#
# The one surface on an athlete's page that the athlete does not write. It is
# the reference product's fourth tab, and the argument for it is that a profile
# with only broadcast on it is a brochure -- people come back for the part where
# other people are.
#
# **You have to follow them to post.** Same reasoning as the direct-message
# rule: an open write surface on the page of somebody with an audience is a
# spam target, and following is a deliberate act that can be taken back. It is
# a much lower bar than subscribing on purpose -- charging for the right to say
# "good race" would be a strange product -- but it is not nothing.
#
# The athlete can remove anything on their own wall. Their name is on the page.


class FanPostIn(BaseModel):
    body: str = Field(min_length=1, max_length=500)


@router.get("/athletes/{slug}/wall-posts")
def fan_wall(slug: str, limit: int = Query(50, ge=1, le=200),
             user: dict | None = Depends(optional_user),
             conn: sqlite3.Connection = Depends(get_db)):
    """Public: the wall is the point, so a visitor sees it before signing in."""
    athlete = row(conn, "SELECT id, user_id FROM athlete_profiles WHERE slug = ?", (slug,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    posts = rows(conn, """
        SELECT f.*, u.display_name, u.role FROM fan_posts f
        JOIN users u ON u.id = f.user_id
        WHERE f.athlete_id = ? ORDER BY f.id DESC LIMIT ?""", (athlete["id"], limit))
    viewer = user["id"] if user else None
    owns_wall = viewer is not None and viewer == athlete["user_id"]
    return [{"id": p["id"], "body": p["body"], "at": p["created_at"],
             "author": p["display_name"], "role": p["role"],
             # the server decides who may remove a row, so the control cannot
             # appear where the delete would be refused
             "can_remove": owns_wall or p["user_id"] == viewer}
            for p in posts]


@router.post("/athletes/{slug}/wall-posts", status_code=201)
def post_to_wall(slug: str, body: FanPostIn,
                 user: dict = Depends(require_role("fan", "sponsor", "athlete")),
                 conn: sqlite3.Connection = Depends(get_db)):
    athlete = row(conn, "SELECT id, user_id FROM athlete_profiles WHERE slug = ?"
                        " AND status = 'listed'", (slug,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    # `min_length` counts spaces, so "   " passed validation and was stored as
    # an empty row -- a blank card on somebody's public page.
    if not body.body.strip():
        raise HTTPException(422, "empty_post")
    # An athlete always has the run of their own wall; everybody else follows
    # first. Requiring a subscription instead would make saying "good race" a
    # paid feature, which is the wrong thing to charge for.
    if athlete["user_id"] != user["id"]:
        follows = row(conn, "SELECT id FROM follows WHERE user_id = ? AND athlete_id = ?",
                      (user["id"], athlete["id"]))
        if follows is None:
            raise HTTPException(403, "follow_first")

    conn.execute("INSERT INTO fan_posts (athlete_id, user_id, body, created_at)"
                 " VALUES (?, ?, ?, ?)", (athlete["id"], user["id"], body.body.strip(), now_iso()))
    if athlete["user_id"] and athlete["user_id"] != user["id"]:
        notify(conn, athlete["user_id"], "fan_post",
               f"{user['display_name']} posted on your wall", body.body.strip()[:140],
               f"/athletes/{slug}")
    log_event(conn, "user", "fan_wall.posted", "athlete", athlete["id"], {"user_id": user["id"]})
    conn.commit()
    return {"ok": True}


@router.delete("/wall-posts/{post_id}")
def remove_fan_post(post_id: int,
                    user: dict = Depends(require_role("fan", "sponsor", "athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    """Removable by whoever wrote it, and by the athlete whose page it is on.

    404 rather than 403 for anybody else: a post you may not touch should not
    be confirmed to exist by the shape of the refusal.
    """
    post = row(conn, "SELECT * FROM fan_posts WHERE id = ?", (post_id,))
    if post is None:
        raise HTTPException(404, "unknown_post")
    athlete = row(conn, "SELECT user_id FROM athlete_profiles WHERE id = ?", (post["athlete_id"],))
    if post["user_id"] != user["id"] and (athlete or {}).get("user_id") != user["id"]:
        raise HTTPException(404, "unknown_post")
    conn.execute("DELETE FROM fan_posts WHERE id = ?", (post_id,))
    log_event(conn, "user", "fan_wall.removed", "athlete", post["athlete_id"],
              {"post_id": post_id, "by": user["id"]})
    conn.commit()
    return {"ok": True}
