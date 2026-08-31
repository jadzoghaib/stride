"""Athlete surface: public directory + the athlete's own workspace.

Analytics come straight from the CreatorLens engine — the athlete connects
platforms (mock connectors in this iteration), syncs through the real pipeline,
and sees the same marketability dimensions sponsors see.
"""

from __future__ import annotations

import json
import sqlite3

from creatorlens.actions import ActionRejected, connect_platform, disconnect_platform
from creatorlens.analytics.kpis import creator_kpis, latest_post_metrics
from creatorlens.analytics.scoring import (InsufficientData, _combined_demographics,
                                           latest_score, store_scores)
from creatorlens.events import log_event
from creatorlens.ingestion import sync_account
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, optional_user, require_role
from ..db import lock_for_update, now_iso, row, rows

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


#: Roles that are here to buy an athlete's audience rather than to enjoy it.
COMMERCIAL_ROLES = ("sponsor", "club", "admin")


def sees_commercials(user: dict | None, athlete: dict | None = None) -> bool:
    """Whether this viewer gets the rate card and the marketability score.

    A rate card is a sponsorship asking price and a marketability score is the
    evidence behind it -- both are sales material aimed at a buyer. A fan is not
    a buyer of the athlete; they are buying a post or a session, and showing
    them "8,500" prices the person instead of the thing on offer. So sponsors,
    clubs and admins see it, and the athlete sees their own.
    """
    if user is None:
        return False
    if user["role"] in COMMERCIAL_ROLES:
        return True
    return athlete is not None and athlete["user_id"] == user["id"]


def social_links(conn, creator_id: int | None) -> list[dict]:
    """Where to find this athlete off Stride.

    What replaced "2 of 3 platforms" on the fan-facing surfaces: coverage is a
    statement about how complete our analytics are, which matters to a sponsor
    and means nothing to a fan. A fan wants the handle.
    """
    if not creator_id:
        return []
    return [{"platform": r["platform"], "handle": r["handle"],
             "url": f"https://{r['platform']}.com/{(r['handle'] or '').lstrip('@')}"}
            for r in rows(conn, "SELECT platform, handle FROM platform_accounts"
                                " WHERE creator_id = ? AND connection_status != 'disconnected'"
                                " ORDER BY platform", (creator_id,))]


def athlete_public(conn, a: dict, *, viewer: dict | None = None,
                   commercial: bool | None = None) -> dict:
    """One athlete, told to whoever is asking.

    `commercial` defaults to what `viewer` earns; pass it explicitly only where
    the caller already knows (the sponsor evidence page, an athlete's own
    workspace).
    """
    if commercial is None:
        commercial = sees_commercials(viewer, a)
    out = {
        "id": a["id"], "slug": a["slug"], "display_name": a["display_name"],
        "sport": a["sport"], "country": a["country"], "region": a["region"],
        "bio": a["bio"], "career_highlights": json.loads(a["career_highlights"]),
        "topics": json.loads(a["topics"]), "deal_types": json.loads(a["deal_types"]),
        "status": a["status"], "claimed": a["user_id"] is not None,
        "socials": social_links(conn, a["creatorlens_creator_id"]),
    }
    if commercial:
        out["base_rate_eur"] = a["base_rate_eur"]
        out["score"] = _score_summary(conn, a["creatorlens_creator_id"])
    return out


# ---- public directory --------------------------------------------------------

DIRECTORY_PAGE = 24


@router.get("/athletes")
def list_athletes(sport: str | None = None, country: str | None = None,
                  q: str | None = None, cursor: str | None = None,
                  limit: int = Query(DIRECTORY_PAGE, ge=1, le=100),
                  user: dict | None = Depends(optional_user),
                  conn: sqlite3.Connection = Depends(get_db)):
    """The public directory, a page at a time.

    This returned every listed athlete and ran a score lookup per row, which is
    fine at two dozen and is the first thing to fall over as supply grows —
    exactly the direction the whole plan is pointed in.

    The cursor is the last `(display_name, id)` seen rather than an offset.
    Offsets skip or repeat rows when the set shifts underneath a reader, and
    this set shifts every time an athlete is admitted or delisted; the ordering
    key does not have that problem. `id` breaks ties so the order is total.
    """
    sql = "SELECT * FROM athlete_profiles WHERE status = 'listed'"
    params: list = []
    if sport:
        sql += " AND sport = ?"
        params.append(sport)
    if country:
        sql += " AND country = ?"
        params.append(country)
    if q:
        sql += " AND (display_name LIKE ? OR sport LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if cursor:
        name, _, raw_id = cursor.rpartition("")
        if not raw_id.isdigit():
            raise HTTPException(422, "bad_cursor")
        sql += " AND (display_name, id) > (?, ?)"
        params += [name, int(raw_id)]

    # one extra row, purely to answer "is there another page" without a count(*)
    found = rows(conn, sql + " ORDER BY display_name, id LIMIT ?", (*params, limit + 1))
    page, more = found[:limit], len(found) > limit
    return {
        "athletes": [athlete_public(conn, a, viewer=user) for a in page],
        "next_cursor": (f"{page[-1]['display_name']}{page[-1]['id']}"
                        if page and more else None),
        "limit": limit,
    }


@router.get("/athletes/facets")
def athlete_facets(conn: sqlite3.Connection = Depends(get_db)):
    """Every filter list in the product, derived from what is actually there.

    Two vocabularies live here on purpose, and confusing them is easy:

      * `countries` are **profile** countries, as full names — where the athlete
        competes. This is what the directory filters on.
      * `audience_countries` are **ISO codes**, the buckets audience demographics
        are stored in, and the only thing campaign targeting can be compared
        against. `audience_fit` looks a campaign's target codes up directly in
        the demographics dict, so a name here would silently score zero.

    Everything is derived rather than listed. The campaign form and the fan
    discover page each carried their own hard-coded array, which meant a sponsor
    could not target a country we had athletes in unless somebody had thought of
    it in advance — the first athlete from Zimbabwe would have been invisible to
    targeting while appearing perfectly well in the directory beside them.
    """
    # Commas are excluded, not escaped: `/discover?interests=` is a
    # comma-separated list and the server splits on commas, so a topic
    # containing one could be offered as a filter and then never match itself.
    topics: set[str] = set()
    for r in rows(conn, "SELECT topics FROM athlete_profiles WHERE status='listed'"):
        try:
            topics.update(t for t in json.loads(r["topics"] or "[]") if t and "," not in t)
        except (ValueError, TypeError):
            continue
    return {
        "sports": [r["sport"] for r in rows(conn,
                   "SELECT DISTINCT sport FROM athlete_profiles WHERE status='listed' ORDER BY sport")],
        "countries": [r["country"] for r in rows(conn,
                      "SELECT DISTINCT country FROM athlete_profiles WHERE status='listed' ORDER BY country")],
        # Scoped to what is targetable *now*: the latest capture for each
        # account, on accounts still connected, belonging to listed athletes.
        # Distinct-across-all-history would keep offering a country that a sync
        # dropped or that left with a disconnected account — a target a sponsor
        # can select and never match.
        # `OTHER` is a real demographic bucket and not a place.
        "audience_countries": [r["bucket"] for r in rows(conn, """
            SELECT DISTINCT d.bucket
            FROM audience_demographics d
            JOIN platform_accounts pa ON pa.id = d.account_id
            JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
            WHERE d.dimension = 'country'
              AND d.bucket <> 'OTHER'
              -- `= 'connected'`, matching `demographic_kpis`, which is what
              -- actually scores audience fit. An account in `error` is excluded
              -- from scoring, so publishing its country would offer a target
              -- that can never match. (The deliverables path deliberately uses
              -- `<> 'disconnected'` instead: there the question is whether the
              -- athlete may attach a post they really published, and an expired
              -- token is not a withdrawal of consent.)
              AND pa.connection_status = 'connected'
              AND a.status = 'listed'
              -- by run, not by timestamp: two syncs finishing in the same second
              -- would otherwise both count, and a country the newer one dropped
              -- would stay targetable
              AND d.sync_run_id = (SELECT MAX(x.sync_run_id)
                                   FROM audience_demographics x
                                   WHERE x.account_id = d.account_id
                                     AND x.dimension = 'country')
            ORDER BY d.bucket""")],
        "topics": sorted(topics),
    }


@router.get("/athletes/{slug}")
def athlete_detail(slug: str, user: dict | None = Depends(optional_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    a = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ?", (slug,))
    if a is None:
        raise HTTPException(404, "unknown_athlete")
    out = athlete_public(conn, a, viewer=user)
    # Audience demographics are the same sales material as the score: a
    # breakdown of who this athlete reaches is what a sponsor is buying, and a
    # fan has no use for their own age bracket as a percentage.
    if a["creatorlens_creator_id"] and sees_commercials(user, a):
        out["audience"] = _combined_demographics(
            conn, creator_kpis(conn, a["creatorlens_creator_id"]))["dimensions"]
    # Whether this reader already follows or subscribes, so the profile can show
    # the state rather than a guess that flickers after the first click.
    if user:
        out["following"] = row(conn, "SELECT id FROM follows WHERE user_id = ? AND athlete_id = ?",
                               (user["id"], a["id"])) is not None
        out["subscribed"] = row(conn, "SELECT id FROM subscriptions"
                                      " WHERE user_id = ? AND athlete_id = ?",
                                (user["id"], a["id"])) is not None
    # club affiliation is part of the public identity — an empty list means
    # independent, so the UI can say so instead of leaving the question open
    out["clubs"] = rows(conn, """
        SELECT c.name, c.slug, cm.position FROM club_members cm
        JOIN clubs c ON c.id = cm.club_id
        WHERE cm.athlete_id = ? AND cm.status = 'active' AND c.status = 'listed'
        ORDER BY c.name""", (a["id"],))
    return out


@router.get("/athletes/{slug}/news")
def public_news(slug: str, limit: int = Query(20, ge=1, le=60),
                conn: sqlite3.Connection = Depends(get_db)):
    """What this athlete has been posting on their own platforms.

    The wall would otherwise stay empty until an athlete publishes something in
    Stride, which is the cold start every creator platform dies of: a profile
    with nothing on it gives a fan no reason to come back, so nobody follows, so
    the athlete has no reason to publish. These rows already exist -- they are
    what the marketability score is computed from -- and they are public posts
    with public permalinks, so a profile is worth opening on day one.

    No metrics. Reach and engagement are the athlete's own analytics and the
    sponsor's evidence; a fan gets the post, not the numbers behind it.

    `!= 'disconnected'` mirrors `own_posts`. Disconnecting a platform withdraws
    the consent its data was collected under, and a public wall is precisely
    the place that has to honour it -- the rows stay so scores remain
    reproducible, but they stop being shown.
    """
    athlete = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ?", (slug,))
    if athlete is None:
        raise HTTPException(404, "unknown_athlete")
    creator_id = athlete["creatorlens_creator_id"]
    if not creator_id:
        return []
    out = []
    for account in rows(conn, "SELECT * FROM platform_accounts"
                        " WHERE creator_id = ? AND connection_status != 'disconnected'",
                        (creator_id,)):
        for post in rows(conn, "SELECT title, published_at, permalink, content_type"
                               " FROM posts WHERE account_id = ?"
                               " ORDER BY published_at DESC LIMIT ?", (account["id"], limit)):
            out.append({"platform": account["platform"], "title": post["title"],
                        "published_at": post["published_at"], "permalink": post["permalink"],
                        "content_type": post["content_type"]})
    out.sort(key=lambda p: p["published_at"], reverse=True)
    return out[:limit]


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
    base_rate_eur: int | None = Field(default=None, ge=0, le=1_000_000)
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
        "profile": athlete_public(conn, profile, commercial=True),
        "editable": {k: profile[k] for k in ("display_name", "sport", "country", "region",
                                             "bio", "base_rate_eur", "status")}
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
        "earnings": sum(d["amount_eur"] for d in deals if d["status"] in ("accepted", "completed")),
        "clubs": rows(conn, """
            SELECT c.name, c.slug, cm.position FROM club_members cm
            JOIN clubs c ON c.id = cm.club_id
            WHERE cm.athlete_id = ? AND cm.status = 'active' ORDER BY c.name""", (profile["id"],)),
        "club_backing": rows(conn, """
            SELECT pc.amount_eur, pc.status, pc.created_at, cp.name AS package_name,
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
    for field in ("display_name", "sport", "country", "region", "bio", "base_rate_eur", "status"):
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
    # Consent is the lawful basis for every platform metric Stride ingests
    # (GDPR Art. 6(1)(a)), so it is a required field of the request rather than
    # an assumption made by the server. The client shows the scopes first.
    consent: bool = False
    policy_version: str = Field(default="", max_length=32)


@router.post("/athlete/platforms/connect")
def connect_account(body: ConnectIn, user: dict = Depends(require_role("athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    if not body.consent:
        raise HTTPException(422, "consent_required")
    try:
        account = connect_platform(conn, profile["creatorlens_creator_id"], body.platform, actor="user")
    except ActionRejected as exc:
        raise HTTPException(409, exc.reason)
    # The consent record IS the audit event: who, what, when, under which
    # version of the policy — the four things a supervisory authority asks for.
    log_event(conn, "user", "consent.platform_granted", "platform_account", account["id"],
              {"platform": body.platform, "athlete_id": profile["id"],
               "policy_version": body.policy_version,
               "scopes": ["profile_metrics", "post_metrics", "aggregate_demographics"]})
    conn.commit()
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
        result = disconnect_platform(conn, account_id, actor="user")
    except ActionRejected as exc:
        raise HTTPException(409, exc.reason)
    # Withdrawal is logged as deliberately as the grant (Art. 7(3)) — a consent
    # trail that records only the yes is not a trail.
    log_event(conn, "user", "consent.platform_withdrawn", "platform_account", account_id,
              {"platform": account["platform"], "athlete_id": profile["id"]})
    conn.commit()
    return result


# ---- deals (athlete side) ----------------------------------------------------

def _deals_for_athlete(conn, athlete_id: int) -> list[dict]:
    deals = rows(conn, """
        SELECT d.*, c.name AS campaign_name, c.category, o.name AS org_name
        FROM deals d JOIN campaigns c ON c.id = d.campaign_id
                     JOIN sponsor_orgs o ON o.id = d.org_id
        WHERE d.athlete_id = ? ORDER BY d.created_at DESC, d.id DESC""", (athlete_id,))
    # What is already attached, so the athlete is never offered a post they have
    # submitted before. One grouped query rather than one per deal.
    attached: dict[int, list[int]] = {}
    for link in rows(conn, """
            SELECT dd.deal_id, dd.post_id FROM deal_deliverables dd
            JOIN deals d ON d.id = dd.deal_id
            WHERE d.athlete_id = ? ORDER BY dd.id""", (athlete_id,)):
        attached.setdefault(link["deal_id"], []).append(link["post_id"])
    for deal in deals:
        deal["deliverable_post_ids"] = attached.get(deal["id"], [])
    return deals


class RespondIn(BaseModel):
    action: str  # accept | decline


@router.get("/athlete/posts")
def own_posts(user: dict = Depends(require_role("athlete")),
              conn: sqlite3.Connection = Depends(get_db)):
    """The athlete's recent posts, for attaching to a deal as a deliverable."""
    profile = _own_profile(conn, user)
    creator_id = profile["creatorlens_creator_id"]
    if not creator_id:
        return []
    out = []
    # Not disconnected. Disconnecting a platform withdraws the consent the data
    # was collected under; the rows stay because scores have to remain
    # reproducible, but continuing to offer those posts for attachment would let
    # an athlete sell a permission they have already taken back.
    #
    # `!= 'disconnected'` rather than `= 'connected'`: sync.py sets 'error' when
    # a refresh fails, and an expired token is an operational problem, not a
    # withdrawal. Excluding it would block a real athlete from attaching a real
    # post for a reason that has nothing to do with their consent.
    for account in rows(conn, "SELECT * FROM platform_accounts"
                        " WHERE creator_id = ? AND connection_status != 'disconnected'",
                        (creator_id,)):
        for post in latest_post_metrics(conn, account["id"])[:15]:
            out.append({"post_id": post["post_id"], "platform": account["platform"],
                        "title": post["title"], "published_at": post["published_at"],
                        "reach": post["reach"]})
    out.sort(key=lambda p: p["published_at"], reverse=True)
    return out[:40]


class DeliverableIn(BaseModel):
    post_id: int


@router.post("/athlete/deals/{deal_id}/deliverables", status_code=201)
def add_deliverable(deal_id: int, body: DeliverableIn,
                    user: dict = Depends(require_role("athlete")),
                    conn: sqlite3.Connection = Depends(get_db)):
    """Attach the post that fulfilled a deal.

    Guarded twice over: the deal must be the athlete's, and so must the post —
    otherwise an athlete could attribute someone else's reach to their own
    campaign, which would poison the one dataset sponsors are meant to trust.
    """
    profile = _own_profile(conn, user)
    # Reading the status and inserting against it is the same check-then-act race
    # as the nomination budget: `complete` can commit in between, and the
    # deliverable then lands on a deal that has finished — precisely what the
    # status check below exists to prevent. Holding the deal row for the rest of
    # the transaction makes the check and the insert one decision; `complete`
    # takes the same row lock by updating it, so the two serialise either way
    # round, on either backend.
    lock_for_update(conn, "deals", "id", deal_id)
    deal = row(conn, "SELECT * FROM deals WHERE id = ? AND athlete_id = ?",
               (deal_id, profile["id"]))
    if deal is None:
        raise HTTPException(404, "unknown_deal")
    if deal["status"] != "accepted":
        # Not `completed` either. The sponsor has already read that report, and
        # attaching another post afterwards silently moves reach, engagement and
        # cost-per-engagement on a figure they have acted on. Re-opening a closed
        # deal should be a deliberate act, not a side effect of an attach.
        raise HTTPException(409, "deal_not_accepted")

    post = row(conn, """
        SELECT p.id FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        WHERE p.id = ? AND pa.creator_id = ? AND pa.connection_status != 'disconnected'""",
        (body.post_id, profile["creatorlens_creator_id"]))
    if post is None:
        raise HTTPException(404, "unknown_post")

    existing = row(conn, "SELECT id FROM deal_deliverables WHERE deal_id = ? AND post_id = ?",
                   (deal_id, body.post_id))
    if existing:
        raise HTTPException(409, "already_attached")

    conn.execute("INSERT INTO deal_deliverables (deal_id, post_id, added_at) VALUES (?, ?, ?)",
                 (deal_id, body.post_id, now_iso()))
    log_event(conn, "user", "deal.deliverable_added", "deal", deal_id,
              {"post_id": body.post_id, "athlete_id": profile["id"]})
    conn.commit()
    return {"ok": True, "deal_id": deal_id, "post_id": body.post_id}


@router.post("/athlete/deals/{deal_id}/complete")
def complete_deal(deal_id: int, user: dict = Depends(require_role("athlete")),
                  conn: sqlite3.Connection = Depends(get_db)):
    """Mark a deal delivered. Requires at least one deliverable, so a completed
    deal always has something a sponsor can inspect."""
    profile = _own_profile(conn, user)
    deal = row(conn, "SELECT * FROM deals WHERE id = ? AND athlete_id = ?",
               (deal_id, profile["id"]))
    if deal is None:
        raise HTTPException(404, "unknown_deal")
    if deal["status"] != "accepted":
        raise HTTPException(409, "deal_not_accepted")
    count = row(conn, "SELECT COUNT(*) AS n FROM deal_deliverables WHERE deal_id = ?",
                (deal_id,))["n"]
    if not count:
        raise HTTPException(409, "no_deliverables")

    conn.execute("UPDATE deals SET status = 'completed', completed_at = ? WHERE id = ?",
                 (now_iso(), deal_id))
    log_event(conn, "user", "deal.completed", "deal", deal_id,
              {"athlete_id": profile["id"], "deliverables": count,
               "amount_eur": deal["amount_eur"]})
    conn.commit()
    return row(conn, "SELECT * FROM deals WHERE id = ?", (deal_id,))


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
              {"athlete_id": profile["id"], "amount_eur": deal["amount_eur"]})
    conn.commit()
    return row(conn, "SELECT * FROM deals WHERE id = ?", (deal_id,))


# ── club invitations ────────────────────────────────────────────────────────

@router.get("/athlete/invitations")
def my_invitations(user: dict = Depends(require_role("athlete")),
                   conn: sqlite3.Connection = Depends(get_db)):
    """Clubs that have asked this athlete to join their roster.

    A club used to be able to add anyone straight to its roster, which mattered
    because player-direct sponsorship packages are sold against membership — so
    a club could claim an athlete and monetise their audience while the athlete
    found out by looking at their own profile. Now it asks, and this is where
    the asking arrives.
    """
    profile = _own_profile(conn, user)
    return rows(conn, """
        SELECT cm.id AS invitation_id, cm.position, cm.joined_at AS invited_at,
               c.id AS club_id, c.slug, c.name, c.sport, c.country
        FROM club_members cm JOIN clubs c ON c.id = cm.club_id
        WHERE cm.athlete_id = ? AND cm.status = 'invited'
        ORDER BY cm.joined_at DESC""", (profile["id"],))


class InvitationResponse(BaseModel):
    action: str = Field(pattern="^(accept|decline)$")


@router.post("/athlete/invitations/{invitation_id}/respond")
def respond_to_invitation(invitation_id: int, body: InvitationResponse,
                          user: dict = Depends(require_role("athlete")),
                          conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_profile(conn, user)
    invite = row(conn, "SELECT * FROM club_members WHERE id = ? AND athlete_id = ?",
                 (invitation_id, profile["id"]))
    if invite is None:
        raise HTTPException(404, "unknown_invitation")
    if invite["status"] != "invited":
        raise HTTPException(409, "invitation_already_answered")
    status = "active" if body.action == "accept" else "declined"
    conn.execute("UPDATE club_members SET status = ?, responded_at = ? WHERE id = ?",
                 (status, now_iso(), invite["id"]))
    log_event(conn, "user", f"club.invitation_{body.action}ed", "club", invite["club_id"],
              {"athlete_id": profile["id"]})
    conn.commit()
    return {"ok": True, "status": status}
