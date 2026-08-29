"""Sponsor surface: org, campaigns, matching, offers, and the full analytics
evidence view for any listed athlete (the CreatorLens engine end-to-end)."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from statistics import median

from creatorlens.analytics.kpis import creator_kpis, engagement_rate, latest_post_metrics
from creatorlens.analytics.scoring import (InsufficientData, _combined_demographics,
                                           compute_scores)
from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from creatorlens.actions import create_target

from ..auth import get_db, require_role
from ..db import now_iso, row, rows
from ..matching import (MODEL_VERSION, WEIGHTS, rank_athletes, slate,
                        slate_fingerprint)
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


def _speed_to_first_offer(conn, org_id: int) -> dict:
    """How long a campaign waits before its first offer goes out.

    TEKTA sells "50-70% faster than a traditional agency process". This is the
    same claim measured rather than asserted, from timestamps the schema
    already keeps. Campaigns that have produced nothing are reported alongside
    the median rather than dropped: a median taken only over the campaigns that
    worked is a survivorship figure, and this product does not ship those.
    """
    waits: list[float] = []
    pending = 0
    # One grouped query, not one per campaign: this runs on every workspace load.
    # MIN() over an ISO-8601 TEXT timestamp is chronological because the format
    # is fixed-width and zero-padded.
    for campaign in rows(conn, """
            SELECT c.id, c.created_at, MIN(d.created_at) AS first_offer_at
            FROM campaigns c LEFT JOIN deals d ON d.campaign_id = c.id
            WHERE c.org_id = ?
            GROUP BY c.id, c.created_at""", (org_id,)):
        if not campaign["first_offer_at"]:
            pending += 1
            continue
        delta = _parse_ts(campaign["first_offer_at"]) - _parse_ts(campaign["created_at"])
        waits.append(max(0.0, delta.total_seconds() / 3600))
    return {
        # None, not 0: no campaign has produced an offer, so there is no wait to
        # report — which is a different statement from an instant one.
        "median_hours": round(median(waits), 1) if waits else None,
        "campaigns_measured": len(waits),
        "campaigns_without_offer": pending,
    }


def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


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
        "spend_committed": sum(d["amount_eur"] for d in deals
                               if d["status"] in ("accepted", "completed"))
                           + sum(x["amount_eur"] for x in club_commitments
                                 if x["status"] == "active"),
        "speed": _speed_to_first_offer(conn, org["id"]),
    }


class CampaignIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    objective: str = Field(default="", max_length=500)
    category: str = Field(max_length=60)
    deal_types: list[str] = Field(default=[], max_length=5)
    budget_eur_min: int = Field(ge=0, le=10_000_000, default=1000)
    budget_eur_max: int = Field(ge=0, le=10_000_000, default=10000)
    target_age_buckets: list[str] = Field(default=[], max_length=6)
    target_genders: list[str] = Field(default=[], max_length=3)
    target_countries: list[str] = Field(default=[], max_length=20)
    target_topics: list[str] = Field(default=[], max_length=12)
    # A hard filter, applied in retrieval — see matching.candidates(). Stated as
    # a requirement rather than a preference precisely so no other signal can
    # outweigh it.
    require_verified_athletes: bool = False


@router.post("/campaigns", status_code=201)
def create_campaign(body: CampaignIn, user: dict = Depends(require_role("sponsor")),
                    conn: sqlite3.Connection = Depends(get_db)):
    org = _own_org(conn, user)
    if body.budget_eur_max < body.budget_eur_min:
        raise HTTPException(422, "budget_max_below_min")
    # every campaign brief becomes a CreatorLens sponsor target — audience fit
    # is then computed against THIS campaign, not a generic default
    target = create_target(conn, f"{body.name} target #{org['id']}-{now_iso()}",
                           body.target_age_buckets, body.target_genders,
                           body.target_countries, body.target_topics, actor="user")
    cur = conn.execute(
        "INSERT INTO campaigns (org_id, name, objective, category, deal_types, budget_eur_min,"
        " budget_eur_max, target_age_buckets, target_genders, target_countries, target_topics,"
        " sponsor_target_id, require_verified_athletes, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
        (org["id"], body.name, body.objective, body.category, json.dumps(body.deal_types),
         body.budget_eur_min, body.budget_eur_max, json.dumps(body.target_age_buckets),
         json.dumps(body.target_genders), json.dumps(body.target_countries),
         json.dumps(body.target_topics), target["id"],
         # the bool itself, not int(): Postgres will not implicitly cast an
         # integer into a boolean column, and SQLite stores a bool as 0/1 anyway
         body.require_verified_athletes, now_iso()))
    log_event(conn, "user", "campaign.created", "campaign", cur.lastrowid,
              {"name": body.name, "org_id": org["id"]})
    conn.commit()
    return _campaign_view(row(conn, "SELECT * FROM campaigns WHERE id = ?", (cur.lastrowid,)))


def _projected_reach(conn, creator_id: int | None) -> int | None:
    """Expected reach of one post, taken at OFFER time.

    The athlete's best channel by median reach, not the sum across platforms: a
    single deliverable lands on one feed, and summing would flatter the
    projection that delivery is later judged against.
    """
    if not creator_id:
        return None
    reaches = [k["median_reach"] for k in creator_kpis(conn, creator_id).values()
               if k["median_reach"]]
    return max(reaches) if reaches else None


def _own_campaign(conn, org, campaign_id: int) -> dict:
    c = row(conn, "SELECT * FROM campaigns WHERE id = ? AND org_id = ?", (campaign_id, org["id"]))
    if c is None:
        raise HTTPException(404, "unknown_campaign")
    return c


SHOWN_MATCHES = 20


def _ranked(conn, org, campaign_id: int):
    campaign = _own_campaign(conn, org, campaign_id)
    started = time.perf_counter()
    ranked = rank_athletes(conn, campaign)
    return campaign, ranked, round((time.perf_counter() - started) * 1000, 1)


@router.get("/campaigns/{campaign_id}/matches")
def campaign_matches(campaign_id: int, user: dict = Depends(require_role("sponsor")),
                     conn: sqlite3.Connection = Depends(get_db)):
    """Read the ranking. Deliberately free of side effects.

    This used to write a `matching.ran` row and commit on every call, so a
    sponsor refreshing the page manufactured duplicate training rows for a
    ranker that has not been built yet — quietly biasing the exposure counts of
    whichever campaigns someone happened to reload. Recording an exposure is an
    intent, and an intent belongs on a POST.
    """
    org = _own_org(conn, user)
    campaign, ranked, duration_ms = _ranked(conn, org, campaign_id)
    return {"campaign": _campaign_view(campaign),
            "matches": ranked[:SHOWN_MATCHES],
            "ranked_total": len(ranked),
            "slate_id": slate_fingerprint(ranked),
            "duration_ms": duration_ms}


@router.post("/campaigns/{campaign_id}/matches", status_code=201)
def record_campaign_matches(campaign_id: int, user: dict = Depends(require_role("sponsor")),
                            conn: sqlite3.Connection = Depends(get_db)):
    """Run matching and record the slate that was put in front of the sponsor.

    Idempotent on the slate's own fingerprint rather than a key the client
    invents: re-opening the same ranking is not a second exposure, but a
    ranking that has genuinely changed is, and only the content can tell those
    apart.
    """
    org = _own_org(conn, user)
    campaign, ranked, duration_ms = _ranked(conn, org, campaign_id)
    fingerprint = slate_fingerprint(ranked)

    already = row(conn, "SELECT id FROM events WHERE event_type = 'matching.ran'"
                  " AND object_type = 'campaign' AND object_id = ?"
                  " AND detail_json LIKE ?", (campaign_id, f'%"slate_id": "{fingerprint}"%'))
    if already is None:
        log_event(conn, "user", "matching.ran", "campaign", campaign_id,
                  {"org_id": org["id"], "results": len(ranked), "shown": SHOWN_MATCHES,
                   "model_version": MODEL_VERSION, "weights": WEIGHTS,
                   "slate_id": fingerprint, "duration_ms": duration_ms,
                   "require_verified_athletes": bool(campaign.get("require_verified_athletes")),
                   "slate": slate(ranked, SHOWN_MATCHES)})
        conn.commit()
    return {"campaign": _campaign_view(campaign),
            "matches": ranked[:SHOWN_MATCHES],
            "ranked_total": len(ranked),
            "slate_id": fingerprint,
            "duration_ms": duration_ms,
            "recorded": already is None}


class OfferIn(BaseModel):
    athlete_id: int
    deal_type: str = Field(max_length=40)
    amount_eur: int = Field(gt=0, le=10_000_000)
    message: str = Field(default="", max_length=1000)


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
    projected = _projected_reach(conn, athlete["creatorlens_creator_id"])
    cur = conn.execute(
        "INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_eur, message,"
        " status, created_at, projected_reach) VALUES (?, ?, ?, ?, ?, ?, 'offered', ?, ?)",
        (campaign_id, org["id"], body.athlete_id, body.deal_type, body.amount_eur,
         body.message, now_iso(), projected))
    log_event(conn, "user", "deal.created", "deal", cur.lastrowid,
              {"campaign_id": campaign_id, "athlete_id": body.athlete_id,
               "amount_eur": body.amount_eur, "org_id": org["id"]})
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


@router.get("/deals/{deal_id}/performance")
def deal_performance(deal_id: int, user: dict = Depends(require_role("sponsor")),
                     conn: sqlite3.Connection = Depends(get_db)):
    """What the sponsor actually got: delivered reach and engagement against the
    projection captured when the offer was sent.

    Every figure decomposes to the posts listed in `deliverables` — the same
    rule the marketability scores follow. A number a sponsor cannot open is a
    number they have to take on trust, which is the thing this product exists
    not to ask of them.
    """
    org = _own_org(conn, user)
    deal = row(conn, """
        SELECT d.*, a.display_name AS athlete_name, a.slug AS athlete_slug,
               a.creatorlens_creator_id, c.name AS campaign_name
        FROM deals d JOIN athlete_profiles a ON a.id = d.athlete_id
                     JOIN campaigns c ON c.id = d.campaign_id
        WHERE d.id = ? AND d.org_id = ?""", (deal_id, org["id"]))
    if deal is None:
        raise HTTPException(404, "unknown_deal")

    # `measured` rather than `len(deliverables)`: a post can be attached before
    # its metrics are captured, and summing that as 0 puts the campaign back at
    # "reached nobody" through a different door than the one just closed.
    deliverables, reach, engagements, measured = [], 0, 0.0, 0
    for link in rows(conn, "SELECT * FROM deal_deliverables WHERE deal_id = ? ORDER BY id",
                     (deal_id,)):
        post = row(conn, """
            SELECT p.*, pa.platform FROM posts p
            JOIN platform_accounts pa ON pa.id = p.account_id
            WHERE p.id = ?""", (link["post_id"],))
        if post is None:
            continue
        metric = row(conn, "SELECT * FROM post_metrics WHERE post_id = ?"
                     " ORDER BY captured_at DESC, id DESC LIMIT 1", (post["id"],))
        er = engagement_rate(post["platform"], metric) if metric else None
        post_reach = (metric or {}).get("reach")
        if post_reach is not None:
            measured += 1
            reach += post_reach
            engagements += post_reach * (er or 0)
        deliverables.append({
            "post_id": post["id"], "platform": post["platform"], "title": post["title"],
            "published_at": post["published_at"], "permalink": post["permalink"],
            "reach": post_reach, "engagement_rate": round(er, 5) if er is not None else None,
        })

    amount = deal["amount_eur"]
    projected = deal["projected_reach"]
    return {
        "deal": {k: deal[k] for k in ("id", "status", "deal_type", "amount_eur",
                                      "created_at", "responded_at", "completed_at",
                                      "athlete_name", "athlete_slug", "campaign_name")},
        "deliverables": deliverables,
        # `posts` is a count and is honestly 0. Reach and engagements are
        # measurements, and with nothing attached there is nothing to measure —
        # so they are null, the same rule the cost figures below already follow.
        # Rendering 0 told a sponsor their campaign reached nobody, when the
        # truth is that the athlete has not posted yet.
        "delivered": {"posts": len(deliverables),
                      "reach": reach if measured else None,
                      "engagements": round(engagements) if measured else None},
        "projected": {"reach": projected},
        # None rather than 0 when there is nothing to divide by — an unmeasurable
        # campaign should read as unmeasured, not as free.
        #
        # `deliverables and` matters as much as `projected`. With a projection on
        # file and nothing posted yet, this read -100.0: not "unmeasured" but
        # "delivered a hundred per cent below plan", which is a worse lie than
        # the zero it sat beside — it is an accusation about an athlete who has
        # simply not posted yet.
        "variance_pct": round(100 * (reach - projected) / projected, 1)
                        if projected and measured else None,
        "cost_per_1k_reach": round(amount / (reach / 1000), 2) if reach else None,
        "cost_per_engagement": round(amount / engagements, 2) if engagements >= 1 else None,
    }


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
