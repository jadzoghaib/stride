"""User (fan) surface: discovery, follows, and a following feed."""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_db, optional_user, require_role
from ..db import now_iso, row, rows
from ..matching import fan_ranking
from .athletes import athlete_public

router = APIRouter(prefix="/api", tags=["discover"])


@router.get("/discover")
def discover(interests: str = Query("", description="comma-separated sports/topics"),
             country: str | None = None,
             user: dict | None = Depends(optional_user),
             conn: sqlite3.Connection = Depends(get_db)):
    followed: set[int] = set()
    if user:
        followed = {r["athlete_id"] for r in
                    rows(conn, "SELECT athlete_id FROM follows WHERE user_id = ?", (user["id"],))}
    interest_list = [i for i in (s.strip() for s in interests.split(",")) if i]
    ranked = fan_ranking(conn, interest_list, country, followed)
    out = []
    for r in ranked:
        entry = athlete_public(conn, r)
        entry["affinity"] = r["affinity"]
        entry["reasons"] = r["reasons"]
        entry["following"] = r["id"] in followed
        out.append(entry)
    return out


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
        entry = athlete_public(conn, a)
        if a["creatorlens_creator_id"]:
            history = rows(conn, """
                SELECT computed_at, audience_scale, engagement_quality, growth
                FROM score_snapshots WHERE creator_id = ?
                ORDER BY computed_at DESC, id DESC LIMIT 5""", (a["creatorlens_creator_id"],))
            entry["score_history"] = history[::-1]
        out.append(entry)
    return out
