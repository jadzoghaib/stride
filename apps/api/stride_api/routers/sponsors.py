"""Sponsor surface: org, campaigns, matching, offers, and the full analytics
evidence view for any listed athlete (the CreatorLens engine end-to-end)."""

from __future__ import annotations

import json
import sqlite3

from creatorlens.analytics.kpis import creator_kpis, engagement_rate, latest_post_metrics
from creatorlens.analytics.scoring import (InsufficientData, _combined_demographics,
                                           compute_scores)
from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from creatorlens.actions import create_target

from ..auth import get_db, require_role
from ..db import now_iso, row, rows
from ..matching import sponsor_matches
from .athletes import athlete_public

router = APIRouter(prefix="/api", tags=["sponsors"])


def _own_org(conn, user) -> dict:
    org = row(conn, "SELECT * FROM sponsor_orgs WHERE user_id = ?", (user["id"],))
    if org is None:
        raise HTTPException(404, "no_sponsor_org")
    return org


def _campaign_view(c: dict) -> dict:
    out = dict(c)
    for field in ("deal_types", "target_age_buckets", "target_genders",
                  "target_countries", "target_topics"):
        out[field] = json.loads(out[field])
    return out


@router.get("/sponsor/workspace")
def workspace(user: dict = Depends(require_role("sponsor")),
              conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    campaigns = [_campaign_view(c) for c in
                 rows(conn, "SELECT * FROM campaigns WHERE org_id = ? ORDER BY created_at DESC",
                      (org["id"],))]
    deals = rows(conn, """
        SELECT d.*, a.display_name AS athlete_name, a.slug AS athlete_slug,
               a.sport, c.name AS campaign_name
        FROM deals d JOIN athlete_profiles a ON a.id = d.athlete_id
                     JOIN campaigns c ON c.id = d.campaign_id
        WHERE d.org_id = ? ORDER BY d.created_at DESC, d.id DESC""", (org["id"],))
    club_commitments = rows(conn, """
        SELECT pc.*, cp.name AS package_name, cp.package_type,
               c.name AS club_name, c.slug AS club_slug, a.display_name AS athlete_name
        FROM package_commitments pc
        JOIN club_packages cp ON cp.id = pc.package_id
        JOIN clubs c ON c.id = cp.club_id
        LEFT JOIN athlete_profiles a ON a.id = cp.athlete_id
        WHERE pc.org_id = ? ORDER BY pc.created_at DESC""", (org["id"],))
    return {
        "org": {**org, "regions": json.loads(org["regions"])},
        "campaigns": campaigns,
        "deals": deals,
        "club_commitments": club_commitments,
        "spend_committed": sum(d["amount_usd"] for d in deals
                               if d["status"] in ("accepted", "completed"))
                           + sum(x["amount_usd"] for x in club_commitments
                                 if x["status"] == "active"),
    }


class CampaignIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    objective: str = ""
    category: str
    deal_types: list[str] = []
    budget_usd_min: int = Field(ge=0, default=1000)
    budget_usd_max: int = Field(ge=0, default=10000)
    target_age_buckets: list[str] = []
    target_genders: list[str] = []
    target_countries: list[str] = []
    target_topics: list[str] = []


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, user: dict = Depends(require_role("sponsor")),
                    conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    if body.budget_usd_max < body.budget_usd_min:
        raise HTTPException(422, "budget_max_below_min")
    # every campaign brief becomes a CreatorLens sponsor target — audience fit
    # is then computed against THIS campaign, not a generic default
    target = create_target(conn, f"{body.name} target #{org['id']}-{now_iso()}",
                           body.target_age_buckets, body.target_genders,
                           body.target_countries, body.target_topics, actor="user")
    cur = conn.execute(
        "INSERT INTO campaigns (org_id, name, objective, category, deal_types, budget_usd_min,"
        " budget_usd_max, target_age_buckets, target_genders, target_countries, target_topics,"
        " sponsor_target_id, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
        (org["id"], body.name, body.objective, body.category, json.dumps(body.deal_types),
         body.budget_usd_min, body.budget_usd_max, json.dumps(body.target_age_buckets),
         json.dumps(body.target_genders), json.dumps(body.target_countries),
         json.dumps(body.target_topics), target["id"], now_iso()))
    log_event(conn, "user", "campaign.created", "campaign", cur.lastrowid,
              {"name": body.name, "org_id": org["id"]})
    conn.commit()
    return _campaign_view(row(conn, "SELECT * FROM campaigns WHERE id = ?", (cur.lastrowid,)))


def _own_campaign(conn, org, campaign_id: int) -> dict:
    c = row(conn, "SELECT * FROM campaigns WHERE id = ? AND org_id = ?", (campaign_id, org["id"]))
    if c is None:
        raise HTTPException(404, "unknown_campaign")
    return c


@router.get("/campaigns/{campaign_id}/matches")
def campaign_matches(campaign_id: int, user: dict = Depends(require_role("sponsor")),
                     conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    campaign = _own_campaign(conn, org, campaign_id)
    matches = sponsor_matches(conn, campaign)
    log_event(conn, "user", "matching.ran", "campaign", campaign_id,
              {"org_id": org["id"], "results": len(matches)})
    conn.commit()
    return {"campaign": _campaign_view(campaign), "matches": matches}


class OfferIn(BaseModel):
    athlete_id: int
    deal_type: str
    amount_usd: int = Field(gt=0)
    message: str = ""


@router.post("/campaigns/{campaign_id}/offers", status_code=201)
def send_offer(campaign_id: int, body: OfferIn, user: dict = Depends(require_role("sponsor")),
               conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    campaign = _own_campaign(conn, org, campaign_id)
    athlete = row(conn, "SELECT * FROM athlete_profiles WHERE id = ? AND status = 'listed'",
                  (body.athlete_id,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    open_deal = row(conn, "SELECT id FROM deals WHERE campaign_id = ? AND athlete_id = ?"
                    " AND status = 'offered'", (campaign_id, body.athlete_id))
    if open_deal:
        raise HTTPException(409, "offer_already_open")
    cur = conn.execute(
        "INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_usd, message,"
        " status, created_at) VALUES (?, ?, ?, ?, ?, ?, 'offered', ?)",
        (campaign_id, org["id"], body.athlete_id, body.deal_type, body.amount_usd,
         body.message, now_iso()))
    log_event(conn, "user", "deal.created", "deal", cur.lastrowid,
              {"campaign_id": campaign_id, "athlete_id": body.athlete_id,
               "amount_usd": body.amount_usd, "org_id": org["id"]})
    conn.commit()
    return row(conn, "SELECT * FROM deals WHERE id = ?", (cur.lastrowid,))


@router.post("/deals/{deal_id}/withdraw")
def withdraw_offer(deal_id: int, user: dict = Depends(require_role("sponsor")),
                   conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    deal = row(conn, "SELECT * FROM deals WHERE id = ? AND org_id = ?", (deal_id, org["id"]))
    if deal is None:
        raise HTTPException(404, "unknown_deal")
    if deal["status"] != "offered":
        raise HTTPException(409, "deal_not_open")
    conn.execute("UPDATE deals SET status = 'withdrawn', responded_at = ? WHERE id = ?",
                 (now_iso(), deal_id))
    log_event(conn, "user", "deal.withdrawn", "deal", deal_id, {"org_id": org["id"]})
    conn.commit()
    return {"ok": True}


@router.get("/sponsor/athletes/{slug}/analytics")
def athlete_analytics(slug: str, campaign_id: int | None = None,
                      user: dict = Depends(require_role("sponsor")),
                      conn: sqlite3.Connection = Depends(get_db)):
    """Full evidence view: dimensions, per-platform inputs, audience, recent posts.
    Pass campaign_id to score audience fit against that campaign's target."""
    org = _own_org(conn, user)
    athlete = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ?", (slug,))
    if athlete is None or athlete["status"] != "listed":
        raise HTTPException(404, "unknown_athlete")
    creator_id = athlete["creatorlens_creator_id"]
    target_id = None
    if campaign_id:
        target_id = _own_campaign(conn, org, campaign_id)["sponsor_target_id"]
    result: dict = {"athlete": athlete_public(conn, athlete), "analytics": None,
                    "audience": {}, "posts": []}
    if creator_id:
        try:
            result["analytics"] = compute_scores(conn, creator_id, target_id=target_id)
        except InsufficientData as exc:
            result["analytics_unavailable"] = exc.reason
        kpis = creator_kpis(conn, creator_id)
        result["audience"] = _combined_demographics(conn, kpis)["dimensions"]
        posts = []
        for account in rows(conn, "SELECT * FROM platform_accounts WHERE creator_id = ?",
                            (creator_id,)):
            for p in latest_post_metrics(conn, account["id"])[:10]:
                er = engagement_rate(account["platform"], p)
                posts.append({"platform": account["platform"], "title": p["title"],
                              "published_at": p["published_at"], "reach": p["reach"],
                              "engagement_rate": round(er, 5) if er is not None else None})
        posts.sort(key=lambda p: p["published_at"], reverse=True)
        result["posts"] = posts[:15]
    return result
