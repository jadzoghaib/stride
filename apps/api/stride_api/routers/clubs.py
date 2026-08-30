"""Club surface: clubs alongside individual athletes.

A club manages a roster of Stride athletes and publishes sponsorship packages.
Two package types:
  club          — sponsor backs the club itself (shirt partner, venue naming, ...)
  player_direct — the club's signature feature: a package routed to ONE roster
                  athlete, so sponsors can support individual players through
                  the club relationship.
Sponsors commit to packages; commitments are the club's revenue line and, for
player_direct, appear in that athlete's workspace as club-routed backing.
"""

from __future__ import annotations

import json
import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_db, require_role
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api", tags=["clubs"])


def _club_public(conn, c: dict) -> dict:
    members = row(conn, "SELECT COUNT(*) AS n FROM club_members WHERE club_id = ? AND status = 'active'",
                  (c["id"],))["n"]
    packages = row(conn, "SELECT COUNT(*) AS n FROM club_packages WHERE club_id = ? AND status = 'active'",
                   (c["id"],))["n"]
    backers = row(conn, """
        SELECT COUNT(DISTINCT pc.org_id) AS n FROM package_commitments pc
        JOIN club_packages cp ON cp.id = pc.package_id
        WHERE cp.club_id = ? AND pc.status = 'active'""", (c["id"],))["n"]
    return {"id": c["id"], "slug": c["slug"], "name": c["name"], "sport": c["sport"],
            "country": c["country"], "region": c["region"], "bio": c["bio"],
            "status": c["status"], "member_count": members, "package_count": packages,
            "backer_count": backers}


def _packages_view(conn, club_id: int, include_archived: bool = False) -> list[dict]:
    sql = """
        SELECT cp.*, a.display_name AS athlete_name, a.slug AS athlete_slug
        FROM club_packages cp LEFT JOIN athlete_profiles a ON a.id = cp.athlete_id
        WHERE cp.club_id = ?"""
    if not include_archived:
        sql += " AND cp.status = 'active'"
    out = []
    for p in rows(conn, sql + " ORDER BY cp.package_type, cp.price_eur DESC", (club_id,)):
        p["perks"] = json.loads(p["perks"])
        p["active_backers"] = row(conn, "SELECT COUNT(*) AS n FROM package_commitments"
                                  " WHERE package_id = ? AND status = 'active'", (p["id"],))["n"]
        out.append(p)
    return out


def _roster_view(conn, club_id: int) -> list[dict]:
    return rows(conn, """
        SELECT cm.id AS membership_id, cm.position, cm.status AS membership_status, cm.joined_at,
               a.id AS athlete_id, a.slug, a.display_name, a.sport, a.country
        FROM club_members cm JOIN athlete_profiles a ON a.id = cm.athlete_id
        -- `invited` too: a club has to see who it has asked and who has not
        -- answered. The two guards that matter -- player-direct packages and
        -- nominations -- both require `active`, so an unanswered invitation
        -- shows up here and counts for nothing.
        WHERE cm.club_id = ? AND cm.status IN ('active', 'invited')
        ORDER BY CASE cm.status WHEN 'active' THEN 0 ELSE 1 END, a.display_name""", (club_id,))


# ---- public directory ----------------------------------------------------------

@router.get("/clubs")
def list_clubs(conn: sqlite3.Connection = Depends(get_db)):
    return [_club_public(conn, c) for c in
            rows(conn, "SELECT * FROM clubs WHERE status = 'listed' ORDER BY name")]


@router.get("/clubs/{slug}")
def club_detail(slug: str, conn: sqlite3.Connection = Depends(get_db)):
    c = row(conn, "SELECT * FROM clubs WHERE slug = ?", (slug,))
    if c is None or c["status"] != "listed":  # draft/hidden clubs are not public
        raise HTTPException(404, "unknown_club")
    return {**_club_public(conn, c),
            "roster": _roster_view(conn, c["id"]),
            "packages": _packages_view(conn, c["id"])}


# ---- club workspace (role: club) -------------------------------------------------

def _own_club(conn, user) -> dict:
    c = row(conn, "SELECT * FROM clubs WHERE user_id = ?", (user["id"],))
    if c is None:
        raise HTTPException(404, "no_club")
    return c


@router.get("/club/workspace")
def workspace(user: dict = Depends(require_role("club")),
              conn: sqlite3.Connection = Depends(get_db)):
    c = _own_club(conn, user)
    commitments = rows(conn, """
        SELECT pc.*, cp.name AS package_name, cp.package_type,
               a.display_name AS athlete_name, o.name AS org_name
        FROM package_commitments pc
        JOIN club_packages cp ON cp.id = pc.package_id
        LEFT JOIN athlete_profiles a ON a.id = cp.athlete_id
        JOIN sponsor_orgs o ON o.id = pc.org_id
        WHERE cp.club_id = ? ORDER BY pc.created_at DESC""", (c["id"],))
    return {
        "club": _club_public(conn, c),
        "editable": {k: c[k] for k in ("name", "sport", "country", "region", "bio", "status")},
        "roster": _roster_view(conn, c["id"]),
        "packages": _packages_view(conn, c["id"], include_archived=True),
        "commitments": commitments,
        "revenue_active": sum(x["amount_eur"] for x in commitments if x["status"] == "active"),
    }


class ClubProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    sport: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    bio: str | None = Field(default=None, max_length=2000)
    status: str | None = None


@router.put("/club/profile")
def update_profile(body: ClubProfileIn, user: dict = Depends(require_role("club")),
                   conn: sqlite3.Connection = Depends(get_db)):
    c = _own_club(conn, user)
    updates, params = [], []
    for field in ("name", "sport", "country", "region", "bio", "status"):
        value = getattr(body, field)
        if value is not None:
            if field == "status" and value not in ("draft", "listed", "hidden"):
                raise HTTPException(422, "invalid_status")
            updates.append(f"{field} = ?")
            params.append(value)
    if updates:
        params.append(c["id"])
        conn.execute(f"UPDATE clubs SET {', '.join(updates)} WHERE id = ?", tuple(params))
        log_event(conn, "user", "club.profile_updated", "club", c["id"],
                  {"fields": [u.split(" ")[0] for u in updates]})
        conn.commit()
    return {"ok": True}


class MemberIn(BaseModel):
    athlete_slug: str = Field(max_length=80)
    position: str = Field(default="", max_length=60)


@router.post("/club/members", status_code=201)
def invite_member(body: MemberIn, user: dict = Depends(require_role("club")),
                  conn: sqlite3.Connection = Depends(get_db)):
    """Invite an athlete to the roster. It is a request, not an addition.

    This used to write `active` directly, which let a club put any listed
    athlete on its roster without asking them. That is not merely impolite:
    **player-direct sponsorship packages are sold against roster membership**,
    so a club could have claimed an athlete and monetised their audience while
    the athlete found out by looking at their own profile.

    The athlete answers at `POST /api/athlete/invitations/{id}/respond`. Until
    they accept, the row is `invited` and counts for nothing.
    """
    c = _own_club(conn, user)
    athlete = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ? AND status = 'listed'",
                  (body.athlete_slug,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    existing = row(conn, "SELECT * FROM club_members WHERE club_id = ? AND athlete_id = ?",
                   (c["id"], athlete["id"]))
    if existing and existing["status"] == "active":
        raise HTTPException(409, "already_on_roster")
    if existing and existing["status"] == "invited":
        raise HTTPException(409, "already_invited")
    if existing:
        # a former member, or one who declined, may be asked again
        conn.execute("UPDATE club_members SET status = 'invited', position = ?, joined_at = ?,"
                     " responded_at = NULL WHERE id = ?",
                     (body.position, now_iso(), existing["id"]))
    else:
        conn.execute("INSERT INTO club_members (club_id, athlete_id, position, status, joined_at)"
                     " VALUES (?, ?, ?, 'invited', ?)",
                     (c["id"], athlete["id"], body.position, now_iso()))
    log_event(conn, "user", "club.member_invited", "club", c["id"],
              {"athlete_id": athlete["id"], "slug": athlete["slug"]})
    conn.commit()
    return {"ok": True, "roster": _roster_view(conn, c["id"])}


@router.post("/club/members/{athlete_id}/remove")
def remove_member(athlete_id: int, user: dict = Depends(require_role("club")),
                  conn: sqlite3.Connection = Depends(get_db)):
    c = _own_club(conn, user)
    member = row(conn, "SELECT * FROM club_members WHERE club_id = ? AND athlete_id = ? AND status = 'active'",
                 (c["id"], athlete_id))
    if member is None:
        raise HTTPException(404, "not_on_roster")
    conn.execute("UPDATE club_members SET status = 'former' WHERE id = ?", (member["id"],))
    # player-direct packages tied to a departing athlete stop being sellable,
    # and open commitments on them end — a sponsor must not keep backing a
    # player who left (real payments would prorate here; see docs/build-plan.md)
    cancelled = rows(conn, """
        SELECT pc.id FROM package_commitments pc
        JOIN club_packages cp ON cp.id = pc.package_id
        WHERE cp.club_id = ? AND cp.athlete_id = ? AND pc.status = 'active'""",
        (c["id"], athlete_id))
    for pc in cancelled:
        conn.execute("UPDATE package_commitments SET status = 'cancelled', cancelled_at = ?"
                     " WHERE id = ?", (now_iso(), pc["id"]))
        log_event(conn, "system", "package.commitment_cancelled", "package_commitment", pc["id"],
                  {"reason": "athlete_left_roster", "club_id": c["id"], "athlete_id": athlete_id})
    conn.execute("UPDATE club_packages SET status = 'archived'"
                 " WHERE club_id = ? AND athlete_id = ? AND status = 'active'", (c["id"], athlete_id))
    log_event(conn, "user", "club.member_removed", "club", c["id"],
              {"athlete_id": athlete_id, "commitments_ended": len(cancelled)})
    conn.commit()
    return {"ok": True, "commitments_ended": len(cancelled)}


class PackageIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=1000)
    package_type: str  # club | player_direct
    price_eur: int = Field(gt=0, le=10_000_000)
    athlete_slug: str | None = Field(default=None, max_length=80)  # required for player_direct
    perks: list[str] = Field(default=[], max_length=10)


@router.post("/club/packages", status_code=201)
def create_package(body: PackageIn, user: dict = Depends(require_role("club")),
                   conn: sqlite3.Connection = Depends(get_db)):
    c = _own_club(conn, user)
    if body.package_type not in ("club", "player_direct"):
        raise HTTPException(422, "invalid_package_type")
    athlete_id = None
    if body.package_type == "player_direct":
        if not body.athlete_slug:
            raise HTTPException(422, "player_direct_requires_athlete")
        member = row(conn, """
            SELECT a.id FROM club_members cm JOIN athlete_profiles a ON a.id = cm.athlete_id
            WHERE cm.club_id = ? AND a.slug = ? AND cm.status = 'active'""",
            (c["id"], body.athlete_slug))
        if member is None:
            raise HTTPException(409, "athlete_not_on_roster")
        athlete_id = member["id"]
    cur = conn.execute(
        "INSERT INTO club_packages (club_id, athlete_id, name, description, package_type,"
        " price_eur, perks, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (c["id"], athlete_id, body.name, body.description, body.package_type,
         body.price_eur, json.dumps(body.perks), now_iso()))
    log_event(conn, "user", "club.package_created", "club_package", cur.lastrowid,
              {"club_id": c["id"], "type": body.package_type, "price_eur": body.price_eur})
    conn.commit()
    return _packages_view(conn, c["id"], include_archived=True)


@router.post("/club/packages/{package_id}/archive")
def archive_package(package_id: int, user: dict = Depends(require_role("club")),
                    conn: sqlite3.Connection = Depends(get_db)):
    c = _own_club(conn, user)
    p = row(conn, "SELECT * FROM club_packages WHERE id = ? AND club_id = ?", (package_id, c["id"]))
    if p is None:
        raise HTTPException(404, "unknown_package")
    conn.execute("UPDATE club_packages SET status = 'archived' WHERE id = ?", (package_id,))
    log_event(conn, "user", "club.package_archived", "club_package", package_id, {"club_id": c["id"]})
    conn.commit()
    return {"ok": True}


# ---- sponsor side: back a package -----------------------------------------------

@router.post("/clubs/packages/{package_id}/commit", status_code=201)
def commit_to_package(package_id: int, user: dict = Depends(require_role("sponsor")),
                      conn: sqlite3.Connection = Depends(get_db)):
    org = row(conn, "SELECT * FROM sponsor_orgs WHERE user_id = ?", (user["id"],))
    if org is None:
        raise HTTPException(404, "no_sponsor_org")
    p = row(conn, """
        SELECT cp.* FROM club_packages cp JOIN clubs c ON c.id = cp.club_id
        WHERE cp.id = ? AND cp.status = 'active' AND c.status = 'listed'""", (package_id,))
    if p is None:
        raise HTTPException(404, "unknown_package")
    open_commit = row(conn, "SELECT id FROM package_commitments"
                      " WHERE package_id = ? AND org_id = ? AND status = 'active'",
                      (package_id, org["id"]))
    if open_commit:
        raise HTTPException(409, "already_backing_package")
    cur = conn.execute(
        "INSERT INTO package_commitments (package_id, org_id, amount_eur, created_at)"
        " VALUES (?, ?, ?, ?)", (package_id, org["id"], p["price_eur"], now_iso()))
    log_event(conn, "user", "package.committed", "package_commitment", cur.lastrowid,
              {"package_id": package_id, "org_id": org["id"], "amount_eur": p["price_eur"],
               "athlete_id": p["athlete_id"]})
    conn.commit()
    return row(conn, "SELECT * FROM package_commitments WHERE id = ?", (cur.lastrowid,))


@router.post("/commitments/{commitment_id}/cancel")
def cancel_commitment(commitment_id: int, user: dict = Depends(require_role("sponsor")),
                      conn: sqlite3.Connection = Depends(get_db)):
    org = row(conn, "SELECT * FROM sponsor_orgs WHERE user_id = ?", (user["id"],))
    pc = row(conn, "SELECT * FROM package_commitments WHERE id = ? AND org_id = ?",
             (commitment_id, org["id"] if org else -1))
    if pc is None:
        raise HTTPException(404, "unknown_commitment")
    if pc["status"] != "active":
        raise HTTPException(409, "not_active")
    conn.execute("UPDATE package_commitments SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                 (now_iso(), commitment_id))
    log_event(conn, "user", "package.commitment_cancelled", "package_commitment", commitment_id,
              {"org_id": org["id"]})
    conn.commit()
    return {"ok": True}
