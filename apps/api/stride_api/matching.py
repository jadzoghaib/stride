"""Matching engines.

Sponsor matching (the core): ranks listed athletes against a campaign brief.
It does NOT invent metrics — every analytics component comes from the
CreatorLens engine built alongside this product (packages/creatorlens):
audience fit is recomputed live against the campaign's own sponsor target,
and scale/engagement/growth/consistency come from the same formula set.
Commercial components (budget, deal type, category affinity) are Stride's.

Every match returns its component breakdown and plain-text reasons — a match
score a sponsor can't decompose is a match score they can't trust.

Fan affinity (user mode): lightweight interest/geography ranking for discovery.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3

from creatorlens.analytics.scoring import (InsufficientData, audience_fit, compute_scores,
                                           latest_score)

from .db import rows

MODEL_VERSION = "match-v1"

# An athlete already holding this many unanswered offers is congested: worth
# surfacing, never worth silently down-ranking. Telling a sponsor "four other
# campaigns are waiting on this person" lets them decide; quietly reordering
# their results decides for them.
CONGESTION_AT = 3

# Sponsor-match component weights (documented in docs/architecture.md)
WEIGHTS = {
    "audience_fit": 0.32,      # campaign target vs athlete audience (CreatorLens)
    "engagement_quality": 0.18,
    "audience_scale": 0.14,
    "growth": 0.08,
    "consistency": 0.06,
    "budget_alignment": 0.12,  # rate card vs campaign budget band
    "deal_type_overlap": 0.05, # athlete offers the formats the campaign needs
    "category_affinity": 0.05, # sport/topics vs campaign category
}

# The two groups a component can belong to. Weight is redistributed *within* a
# group, never across one — see _effective_weights.
ANALYTICS_KEYS = ("audience_fit", "engagement_quality", "audience_scale", "growth", "consistency")
COMMERCIAL_KEYS = ("budget_alignment", "deal_type_overlap", "category_affinity")

# Which athlete topics historically convert per sponsor category.
CATEGORY_TOPICS = {
    "Sportswear": ["fitness", "training", "running", "basketball", "football", "lifestyle"],
    "Nutrition": ["fitness", "training", "wellness", "endurance"],
    "Technology": ["esports", "training", "analytics", "lifestyle"],
    "Automotive": ["motorsport", "lifestyle", "travel"],
    "Beverages": ["lifestyle", "fitness", "endurance", "wellness"],
    "Finance": ["career", "lifestyle", "analytics"],
    "Travel": ["travel", "lifestyle", "outdoors", "surfing", "climbing"],
    "Wellness": ["wellness", "fitness", "mindset", "recovery"],
}


def _budget_alignment(rate: int, lo: int, hi: int) -> tuple[float, str | None]:
    if rate <= hi:
        if rate >= lo:
            return 1.0, f"Rate card EUR {rate:,} sits inside the EUR {lo:,}-{hi:,} budget"
        return 0.85, f"Rate card EUR {rate:,} is under budget - room for a larger package"
    if rate <= hi * 2:
        return 0.4, f"Rate card EUR {rate:,} exceeds budget - negotiable at reduced scope"
    # A genuine measured zero, not missing data — but it still has to say why,
    # or the decomposition shows an unexplained 0 against a 12% weight.
    return 0.0, f"Rate card EUR {rate:,} is more than double the EUR {hi:,} ceiling"


def _effective_weights(components: dict[str, float | None]) -> dict[str, float | None]:
    """Weights renormalised over the components that were actually measured.

    A dimension CreatorLens could not compute is `None` here, and stays `None` —
    the engine's rule (missing is not zero) holds all the way to the ranking
    instead of being flattened at this boundary.

    Redistribution is *within a group*: if growth is unmeasured, the other four
    analytics dimensions share its weight. If a whole group is unmeasured its
    weight is forfeited rather than handed to the other group — otherwise an
    athlete with no analytics at all would be scored purely on commercial fit
    and could out-rank an athlete who actually has evidence.
    """
    effective: dict[str, float | None] = {}
    for group in (ANALYTICS_KEYS, COMMERCIAL_KEYS):
        group_weight = sum(WEIGHTS[k] for k in group)
        measured_weight = sum(WEIGHTS[k] for k in group if components.get(k) is not None)
        for key in group:
            effective[key] = (WEIGHTS[key] * group_weight / measured_weight
                              if components.get(key) is not None and measured_weight > 0
                              else None)
    return effective


SNAPSHOT_DIMS = ("audience_scale", "engagement_quality", "growth", "consistency")


def analytics_for(conn: sqlite3.Connection, creator_id: int | None,
                  target_id: int | None) -> dict | None:
    """Four dimensions from the stored snapshot, audience fit recomputed live.

    Scale, engagement quality, growth and consistency describe the athlete and
    not the brief: every campaign that asks gets the same answer, so reading
    them back from `score_snapshots` is not an approximation, it is the same
    number. Rebuilding them from post metrics once per athlete per matching run
    is what made ranking a directory cost O(athletes x posts) — the successor
    docs/architecture.md said would be needed past ~10^3 athletes.

    Audience fit is the exception and stays live, because it is overlap against
    *this* campaign's target and nothing else in the snapshot can answer it.

    With no snapshot there is nothing to reuse, so the full computation runs and
    that athlete is scored on the same formula set as everyone else rather than
    being quietly dropped.
    """
    if not creator_id:
        return None
    snap = latest_score(conn, creator_id)
    if snap is None:
        try:
            return compute_scores(conn, creator_id, target_id=target_id)
        except InsufficientData:
            return None

    fit = audience_fit(conn, creator_id, target_id)
    dims: dict[str, float | None] = {k: snap[k] for k in SNAPSHOT_DIMS}
    dims["audience_fit"] = fit["value"]
    coverage = dict(snap["coverage"])
    coverage["dimensions"] = {**coverage.get("dimensions", {}), "audience_fit": fit["coverage"]}
    return {"dimensions": dims, "coverage": coverage, "source": "snapshot",
            "computed_at": snap["computed_at"], "formula_version": snap["formula_version"]}


def candidates(conn: sqlite3.Connection, campaign: dict) -> list[dict]:
    """Retrieval: hard constraints only, applied before anything is scored.

    Requirements a sponsor states as *must* belong here rather than in the
    weights. A weighted blend is compensatory by construction — a strong
    audience fit would outscore a failed brand-safety or verification check,
    which is the one trade no brand wants made on its behalf. A filter cannot be
    outscored; a 0.05 weight can.
    """
    if campaign.get("require_verified_athletes"):
        return rows(conn, """
            SELECT a.* FROM athlete_profiles a
            JOIN athlete_applications ap ON ap.athlete_id = a.id
            WHERE a.status = 'listed' AND ap.decision = 'admitted'
              AND ap.proof_status = 'verified'
            ORDER BY a.id""")
    return rows(conn, "SELECT * FROM athlete_profiles WHERE status = 'listed' ORDER BY id")


def slate(ranked: list[dict], shown: int) -> list[dict]:
    """The ranked candidate set, compressed for the audit log.

    Offers on their own are a biased sample: they record what a sponsor chose
    without recording what they chose *from*, and nothing recovers later the
    candidates that were never written down.

    Everything ranked is recorded, not only the page the sponsor saw. The
    candidates below the fold are the negatives — a ranker trained on the top
    twenty alone learns to reproduce the current ordering rather than to improve
    it, because it never sees an example of something correctly left out. They
    are stored as id and score only; the component vector is recoverable from
    the score snapshot and is not worth the bytes for a row nobody rendered.
    """
    out = []
    for i, m in enumerate(ranked):
        entry = {"rank": i + 1, "athlete_id": m["athlete_id"], "score": m["score"]}
        if i < shown:
            entry["components"] = m["components"]
        else:
            entry["truncated"] = True
        out.append(entry)
    return out


def slate_fingerprint(ranked: list[dict]) -> str:
    """Identifies a slate by what it contains, so re-viewing one is not a new
    exposure. A client-supplied idempotency key would let a refresh invent a
    fresh one; a fingerprint of the ordering cannot."""
    body = ";".join(f"{m['athlete_id']}:{m['score']}" for m in ranked)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def sponsor_matches(conn: sqlite3.Connection, campaign: dict, limit: int = 20) -> list[dict]:
    """The page a sponsor sees. `rank_athletes` is the whole ordering behind it."""
    return rank_athletes(conn, campaign)[:limit]


def rank_athletes(conn: sqlite3.Connection, campaign: dict) -> list[dict]:
    athletes = candidates(conn, campaign)
    # one grouped read, not one per athlete: this runs on every matching call
    congestion = {r["athlete_id"]: r["n"] for r in rows(
        conn, "SELECT athlete_id, COUNT(*) AS n FROM deals WHERE status = 'offered'"
        " GROUP BY athlete_id")}
    campaign_deal_types = set(json.loads(campaign["deal_types"]))
    category_topics = set(CATEGORY_TOPICS.get(campaign["category"], []))
    results = []

    for athlete in athletes:
        components: dict[str, float | None] = {}
        reasons: list[str] = []
        caveats: list[str] = []

        # ---- analytics components: CreatorLens, live against this campaign's target
        analytics = analytics_for(conn, athlete["creatorlens_creator_id"],
                                  campaign["sponsor_target_id"])
        if analytics:
            dims = analytics["dimensions"]
            cov = analytics["coverage"]["platforms"]
            for key in ANALYTICS_KEYS:
                value = dims.get(key)
                components[key] = (value / 100) if value is not None else None
            unmeasured = [k for k in ANALYTICS_KEYS if components[k] is None]
            if unmeasured:
                caveats.append("Not measured: "
                               + ", ".join(k.replace("_", " ") for k in unmeasured)
                               + " - excluded from the score, remaining analytics weighted up")
            if dims.get("audience_fit") is not None and dims["audience_fit"] >= 60:
                reasons.append(f"Audience fit {dims['audience_fit']:.0f}/100 against this campaign's target")
            if dims.get("engagement_quality") is not None and dims["engagement_quality"] >= 60:
                reasons.append(f"Engagement quality {dims['engagement_quality']:.0f}/100 across {cov['connected']} platform(s)")
            if dims.get("growth") is not None and dims["growth"] >= 65:
                reasons.append("Audience in an active growth phase")
            if cov["connected"] < cov["total"]:
                caveats.append(f"Analytics coverage {cov['connected']} of {cov['total']} platforms"
                               f" - missing {', '.join(cov['missing'])}")
        else:
            for key in ANALYTICS_KEYS:
                components[key] = None
            caveats.append("No connected social analytics - commercial signals only")

        # ---- commercial components: Stride's own
        budget_score, budget_reason = _budget_alignment(
            athlete["base_rate_eur"], campaign["budget_eur_min"], campaign["budget_eur_max"])
        components["budget_alignment"] = budget_score
        if budget_reason and budget_score >= 0.85:
            reasons.append(budget_reason)
        elif budget_reason:
            caveats.append(budget_reason)

        athlete_deal_types = set(json.loads(athlete["deal_types"]))
        overlap = campaign_deal_types & athlete_deal_types
        # a brief that names no formats cannot measure format overlap
        components["deal_type_overlap"] = (len(overlap) / len(campaign_deal_types)
                                           if campaign_deal_types else None)
        if overlap:
            reasons.append("Offers " + ", ".join(sorted(t.replace("_", " ") for t in overlap)))

        athlete_topics = set(json.loads(athlete["topics"]))
        topic_hits = category_topics & athlete_topics
        components["category_affinity"] = min(len(topic_hits) / 2, 1.0)
        if topic_hits:
            reasons.append(f"Content themes match {campaign['category']}: " + ", ".join(sorted(topic_hits)))

        waiting = congestion.get(athlete["id"], 0)
        if waiting >= CONGESTION_AT:
            caveats.append(f"{waiting} offers from other campaigns are already waiting on this"
                           " athlete - expect a slower answer")

        effective = _effective_weights(components)
        score = round(100 * sum(effective[k] * components[k]
                                for k in WEIGHTS if components[k] is not None), 1)
        results.append({
            "athlete_id": athlete["id"],
            "slug": athlete["slug"],
            "display_name": athlete["display_name"],
            "sport": athlete["sport"],
            "country": athlete["country"],
            "base_rate_eur": athlete["base_rate_eur"],
            "score": score,
            # null component = not measured. `weights` is the nominal model;
            # `effective_weights` is what actually produced this score.
            "components": {k: (round(v, 3) if v is not None else None)
                           for k, v in components.items()},
            "weights": WEIGHTS,
            "effective_weights": {k: (round(v, 4) if v is not None else None)
                                  for k, v in effective.items()},
            "reasons": reasons,
            "caveats": caveats,
            "open_offers": waiting,
            "analytics_summary": {
                "dimensions": analytics["dimensions"],
                "coverage": analytics["coverage"]["platforms"],
            } if analytics else None,
        })

    results.sort(key=lambda r: (-r["score"], r["display_name"]))  # ties break A->Z
    return results


def fan_ranking(conn: sqlite3.Connection, interests: list[str], country: str | None,
                followed_ids: set[int], limit: int = 24) -> list[dict]:
    """User-mode discovery: interests + geography + audience momentum, explained."""
    athletes = rows(conn, "SELECT * FROM athlete_profiles WHERE status = 'listed'")
    interest_set = {i.lower().strip() for i in interests}
    out = []
    for a in athletes:
        score = 0.0
        reasons = []
        topics = {t.lower() for t in json.loads(a["topics"])}
        if a["sport"].lower() in interest_set:
            score += 40
            reasons.append(f"Competes in {a['sport']}")
        hits = topics & interest_set
        if hits:
            score += 15 * len(hits)
            reasons.append("Shares your interests: " + ", ".join(sorted(hits)))
        if country and a["country"].lower() == country.lower():
            score += 25
            reasons.append(f"Represents {a['country']}")
        if a["id"] in followed_ids:
            score += 10
        out.append({**a, "affinity": round(score, 1), "reasons": reasons})
    out.sort(key=lambda r: (-r["affinity"], r["display_name"]))  # ties break A->Z
    return out[:limit]
