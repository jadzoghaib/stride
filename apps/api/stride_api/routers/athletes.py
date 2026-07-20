"""Athlete surface: public directory + the athlete's own workspace.

Analytics come straight from the CreatorLens engine — the athlete connects
platforms (mock connectors in this iteration), syncs through the real pipeline,
and sees the same marketability dimensions sponsors see.
"""

from __future__ import annotations

import json
import sqlite3

from creatorlens.actions import ActionRejected, connect_platform, disconnect_platform
from creatorlens.analytics.kpis import creator_kpis
from creatorlens.analytics.scoring import (InsufficientData, _combined_demographics,
                                           latest_score, store_scores)
from creatorlens.events import log_event
from creatorlens.ingestion import sync_account
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, require_role
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api", tags=["athletes"])


def _score_summary(conn, creator_id: int | None) -> dict | None:
    if not creator_id:
        return None
    snap = latest_score(conn, creator_id)
    if snap is None:
        return None
    return {
        "computed_at": snap["computed_at"],
        "dimensions": {k: snap[k] for k in ("audience_scale", "engagement_quality",
                                            "audience_fit", "growth", "consistency")},
        "coverage": snap["coverage"]["platforms"],
    }


def athlete_public(conn, a: dict) -> dict:
    return {
        "id": a["id"], "slug": a["slug"], "display_name": a["display_name"],
        "sport": a["sport"], "country": a["country"], "region": a["region"],
        "bio": a["bio"], "career_highlights": json.loads(a["career_highlights"]),
        "topics": json.loads(a["topics"]), "deal_types": json.loads(a["deal_types"]),
        "base_rate_usd": a["base_rate_usd"], "status": a["status"],
        "claimed": a["user_id"] is not None,
        "score": _score_summary(conn, a["creatorlens_creator_id"]),
    }


# ---- public directory --------------------------------------------------------

@router.get("/athletes")
def list_athletes(sport: str | None = None, country: str | None = None,
                  q: str | None = None, conn: sqlite3.Connection = Depends(get_db)):
    sql, params = "SELECT * FROM athlete_profiles WHERE status = 'listed'", []
    if sport:
        sql += " AND sport = ?"
        params.append(sport)
    if country:
        sql += " AND country = ?"
        params.append(country)
    if q:
        sql += " AND (display_name LIKE ? OR sport LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    return [athlete_public(conn, a) for a in rows(conn, sql + " ORDER BY display_name", tuple(params))]


@router.get("/athletes/facets")
def athlete_facets(conn: sqlite3.Connection = Depends(get_db)):
    return {
        "sports": [r["sport"] for r in rows(conn,
                   "SELECT DISTINCT sport FROM athlete_profiles WHERE status='listed' ORDER BY sport")],
        "countries": [r["country"] for r in rows(conn,
                      "SELECT DISTINCT country FROM athlete_profiles WHERE status='listed' ORDER BY country")],
    }


@router.get("/athletes/{slug}")
def athlete_detail(slug: str, conn: sqlite3.Connection = Depends(get_db)):
    a = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ?", (slug,))
    if a is None:
        raise HTTPException(404, "unknown_athlete")
    out = athlete_public(conn, a)
    if a["creatorlens_creator_id"]:
        out["audience"] = _combined_demographics(
            conn, creator_kpis(conn, a["creatorlens_creator_id"]))["dimensions"]
    # club affiliation is part of the public identity — an empty list means
    # independent, so the UI can say so instead of leaving the question open
    out["clubs"] = rows(conn, """
        SELECT c.name, c.slug, cm.position FROM club_members cm
        JOIN clubs c ON c.id = cm.club_id
        WHERE cm.athlete_id = ? AND cm.status = 'active' AND c.status = 'listed'
        ORDER BY c.name""", (a["id"],))
    return out


# ---- athlete workspace (role: athlete) ---------------------------------------

class ProfileIn(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)
    sport: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=2000)
    career_highlights: list[str] | None = Field(default=None, max_length=12)
    topics: list[str] | None = Field(default=None, max_length=12)
    deal_types: list[str] | None = Field(default=None, max_length=5)
    base_rate_usd: int | None = Field(default=None, ge=0, le=1_000_000)
    status: str | None = None  # draft -> listed


def _own_profile(conn, user) -> dict:
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE user_id = ?", (user["id"],))
    if profile is None:
        raise HTTPException(404, "no_athlete_profile")
    return profile


@router.get("/athlete/workspace")
def workspace(user: dict = Depends(require_role("athlete")),
              conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    creator_id = profile["creatorlens_creator_id"]
    accounts = rows(conn, "SELECT * FROM platform_accounts WHERE creator_id = ?", (creator_id,)) \
        if creator_id else []
    for account in accounts:
        snap = row(conn, "SELECT followers FROM account_snapshots WHERE account_id = ?"
                   " ORDER BY snapshot_date DESC LIMIT 1", (account["id"],))
        account["followers"] = snap["followers"] if snap else None
        account["last_run"] = row(conn, "SELECT status, finished_at, error FROM sync_runs"
                                  " WHERE account_id = ? ORDER BY id DESC LIMIT 1", (account["id"],))
    score = latest_score(conn, creator_id) if creator_id else None
    deals = _deals_for_athlete(conn, profile["id"])
    return {
        "profile": athlete_public(conn, profile),
        "editable": {k: profile[k] for k in ("display_name", "sport", "country", "region",
                                             "bio", "base_rate_usd", "status")}
                    | {"career_highlights": json.loads(profile["career_highlights"]),
                       "topics": json.loads(profile["topics"]),
                       "deal_types": json.loads(profile["deal_types"])},
        "accounts": accounts,
        "analytics": {
            "dimensions": {k: score[k] for k in ("audience_scale", "engagement_quality",
                                                 "audience_fit", "growth", "consistency")},
            "coverage": score["coverage"], "inputs": score["inputs"],
            "computed_at": score["computed_at"], "formula_version": score["formula_version"],
        } if score else None,
        "audience": _combined_demographics(conn, creator_kpis(conn, creator_id))["dimensions"]
                    if creator_id else {},
        "deals": deals,
        "earnings": sum(d["amount_usd"] for d in deals if d["status"] in ("accepted", "completed")),
        "clubs": rows(conn, """
            SELECT c.name, c.slug, cm.position FROM club_members cm
            JOIN clubs c ON c.id = cm.club_id
            WHERE cm.athlete_id = ? AND cm.status = 'active' ORDER BY c.name""", (profile["id"],)),
        "club_backing": rows(conn, """
            SELECT pc.amount_usd, pc.status, pc.created_at, cp.name AS package_name,
                   c.name AS club_name, o.name AS org_name
            FROM package_commitments pc
            JOIN club_packages cp ON cp.id = pc.package_id
            JOIN clubs c ON c.id = cp.club_id
            JOIN sponsor_orgs o ON o.id = pc.org_id
            WHERE cp.athlete_id = ? AND pc.status = 'active'
            ORDER BY pc.created_at DESC""", (profile["id"],)),
    }


@router.put("/athlete/profile")
def update_profile(body: ProfileIn, user: dict = Depends(require_role("athlete")),
                   conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    updates, params = [], []
    for field in ("display_name", "sport", "country", "region", "bio", "base_rate_usd", "status"):
        value = getattr(body, field)
        if value is not None:
            if field == "status" and value not in ("draft", "listed", "hidden"):
                raise HTTPException(422, "invalid_status")
            updates.append(f"{field} = ?")
            params.append(value)
    for field in ("career_highlights", "topics", "deal_types"):
        value = getattr(body, field)
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(json.dumps(value))
    if not updates:
        return {"ok": True}
    params.append(profile["id"])
    conn.execute(f"UPDATE athlete_profiles SET {', '.join(updates)} WHERE id = ?", tuple(params))
    log_event(conn, "user", "athlete.profile_updated", "athlete_profile", profile["id"],
              {"fields": [u.split(" ")[0] for u in updates]})
    conn.commit()
    return {"ok": True}


class ConnectIn(BaseModel):
    platform: str


@router.post("/athlete/platforms/connect")
def connect_account(body: ConnectIn, user: dict = Depends(require_role("athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    try:
        account = connect_platform(conn, profile["creatorlens_creator_id"], body.platform, actor="user")
    except ActionRejected as exc:
        raise HTTPException(409, exc.reason)
    sync = sync_account(conn, account["id"], trigger="manual")
    try:
        store_scores(conn, profile["creatorlens_creator_id"], target_id=1, actor="user")
    except InsufficientData:
        pass
    return {"account": account, "sync": sync}


@router.post("/athlete/platforms/{account_id}/sync")
def resync(account_id: int, user: dict = Depends(require_role("athlete")),
           conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    account = row(conn, "SELECT * FROM platform_accounts WHERE id = ? AND creator_id = ?",
                  (account_id, profile["creatorlens_creator_id"]))
    if account is None:
        raise HTTPException(404, "unknown_account")
    result = sync_account(conn, account_id, trigger="manual")
    try:
        store_scores(conn, profile["creatorlens_creator_id"], target_id=1, actor="user")
    except InsufficientData:
        pass
    return result


@router.post("/athlete/platforms/{account_id}/disconnect")
def disconnect(account_id: int, user: dict = Depends(require_role("athlete")),
               conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    account = row(conn, "SELECT * FROM platform_accounts WHERE id = ? AND creator_id = ?",
                  (account_id, profile["creatorlens_creator_id"]))
    if account is None:
        raise HTTPException(404, "unknown_account")
    try:
        return disconnect_platform(conn, account_id, actor="user")
    except ActionRejected as exc:
        raise HTTPException(409, exc.reason)


# ---- deals (athlete side) ----------------------------------------------------

def _deals_for_athlete(conn, athlete_id: int) -> list[dict]:
    return rows(conn, """
        SELECT d.*, c.name AS campaign_name, c.category, o.name AS org_name
        FROM deals d JOIN campaigns c ON c.id = d.campaign_id
                     JOIN sponsor_orgs o ON o.id = d.org_id
        WHERE d.athlete_id = ? ORDER BY d.created_at DESC, d.id DESC""", (athlete_id,))


class RespondIn(BaseModel):
    action: str  # accept | decline


@router.post("/athlete/deals/{deal_id}/respond")
def respond_to_deal(deal_id: int, body: RespondIn,
                    user: dict = Depends(require_role("athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    deal = row(conn, "SELECT * FROM deals WHERE id = ? AND athlete_id = ?", (deal_id, profile["id"]))
    if deal is None:
        raise HTTPException(404, "unknown_deal")
    if deal["status"] != "offered":
        raise HTTPException(409, "deal_not_open")
    if body.action not in ("accept", "decline"):
        raise HTTPException(422, "invalid_action")
    status = "accepted" if body.action == "accept" else "declined"
    conn.execute("UPDATE deals SET status = ?, responded_at = ? WHERE id = ?",
                 (status, now_iso(), deal_id))
    log_event(conn, "user", f"deal.{status}", "deal", deal_id,
              {"athlete_id": profile["id"], "amount_usd": deal["amount_usd"]})
    conn.commit()
    return row(conn, "SELECT * FROM deals WHERE id = ?", (deal_id,))
