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

import json
import sqlite3

from creatorlens.analytics.scoring import InsufficientData, compute_scores

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
            return 1.0, f"Rate card ${rate:,} sits inside the ${lo:,}-${hi:,} budget"
        return 0.85, f"Rate card ${rate:,} is under budget - room for a larger package"
    if rate <= hi * 2:
        return 0.4, f"Rate card ${rate:,} exceeds budget - negotiable at reduced scope"
    # A genuine measured zero, not missing data — but it still has to say why,
    # or the decomposition shows an unexplained 0 against a 12% weight.
    return 0.0, f"Rate card ${rate:,} is more than double the ${hi:,} ceiling"


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


def slate(matches: list[dict]) -> list[dict]:
    """The ranked candidate set, compressed for the audit log.

    Offers on their own are a biased sample: they record what a sponsor chose
    without recording what they chose *from*, and nothing recovers later the
    candidates that were never written down. Logging the slate — who was shown,
    at what rank, with which component vector, under which weights — is what
    makes a learned ranker trainable at all, and its evaluation off-policy
    rather than wishful. One row per matching run, and unrecoverable if skipped.
    """
    return [{"rank": i + 1, "athlete_id": m["athlete_id"], "score": m["score"],
             "components": m["components"]} for i, m in enumerate(matches)]


def sponsor_matches(conn: sqlite3.Connection, campaign: dict, limit: int = 20) -> list[dict]:
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
        analytics = None
        if athlete["creatorlens_creator_id"]:
            try:
                analytics = compute_scores(conn, athlete["creatorlens_creator_id"],
                                           target_id=campaign["sponsor_target_id"])
            except InsufficientData:
                analytics = None
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
            athlete["base_rate_usd"], campaign["budget_usd_min"], campaign["budget_usd_max"])
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
            "base_rate_usd": athlete["base_rate_usd"],
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
    return results[:limit]


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
