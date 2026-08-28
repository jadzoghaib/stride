"""Marketability scoring — implements docs/scoring.md, formula_version 0.1.

Five transparent dimensions, 0-100. Missing platform = missing value, never zero.
Every snapshot stores its inputs (evidence) and coverage (confidence per dimension).
"""

from __future__ import annotations

import json
import math
import sqlite3

from .. import FORMULA_VERSION, PLATFORMS
from ..db import loads, now_iso, row, rows
from ..events import log_event
from .kpis import creator_kpis, latest_demographics

BENCHMARK_ER = {"instagram": 0.012, "tiktok": 0.045, "youtube": 0.035}
WATCH_NORM_S = {"youtube": 180.0, "tiktok": 30.0}
CADENCE_NORM = {"instagram": 3.0, "tiktok": 4.0, "youtube": 1.0}


class InsufficientData(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def logband(x: float, lo: float, hi: float) -> float:
    if x is None or x <= 0:
        return 0.0
    return clamp((math.log10(x) - lo) / (hi - lo))


def _confidence(points: int) -> str:
    return "high" if points >= 30 else "medium" if points >= 10 else "low"


def _weights(values: dict[str, float]) -> dict[str, float]:
    total = sum(values.values())
    if total <= 0:
        n = len(values)
        return {k: 1.0 / n for k in values}
    return {k: v / total for k, v in values.items()}


def compute_scores(conn: sqlite3.Connection, creator_id: int, target_id: int | None = None) -> dict:
    creator = row(conn, "SELECT * FROM creators WHERE id = ?", (creator_id,))
    if creator is None:
        raise ValueError(f"unknown creator id {creator_id}")

    kpis = creator_kpis(conn, creator_id)
    if not kpis:
        raise InsufficientData("no_connected_data")

    dims: dict[str, float | None] = {}
    coverage: dict = {
        "platforms": {
            "connected": len(kpis),
            "total": len(PLATFORMS),
            "list": sorted(kpis.keys()),
            "missing": sorted(set(PLATFORMS) - set(kpis.keys())),
        },
        "dimensions": {},
    }
    intermediate: dict = {}

    # --- 1. Audience Scale: additive totals, log-banded --------------------
    followers_known = {p: k["followers"] for p, k in kpis.items() if k["followers"]}
    reach_known = {p: k["median_reach"] for p, k in kpis.items() if k["median_reach"]}
    total_followers = sum(followers_known.values())
    total_reach = sum(reach_known.values())
    snapshot_days = sum(k["snapshot_days"] for k in kpis.values())
    total_posts = sum(k["posts_in_window"] for k in kpis.values())
    if total_followers or total_reach:
        f_comp = logband(total_followers, 2, 7)
        r_comp = logband(total_reach, 2, 6.5)
        dims["audience_scale"] = round(100 * (0.6 * f_comp + 0.4 * r_comp), 1)
        intermediate["audience_scale"] = {
            "total_followers": total_followers, "total_median_reach": total_reach,
            "followers_component": round(f_comp, 3), "reach_component": round(r_comp, 3),
        }
        coverage["dimensions"]["audience_scale"] = {
            "confidence": _confidence(snapshot_days), "data_points": snapshot_days, "unit": "snapshot_days"}
    else:
        dims["audience_scale"] = None
        coverage["dimensions"]["audience_scale"] = {"confidence": None, "reason": "no_followers_or_reach"}

    # --- 2. Engagement Quality: benchmarked ER (+watch), reach-weighted ----
    eq_parts = {}
    for p, k in kpis.items():
        if k["median_er"] is None:
            continue
        er_score = 100 * clamp(k["median_er"] / (2 * BENCHMARK_ER[p]))
        watch_score = None
        if p in WATCH_NORM_S and k["avg_view_duration_s"] is not None:
            watch_score = 100 * min(k["avg_view_duration_s"] / WATCH_NORM_S[p], 1.0)
            eq = 0.7 * er_score + 0.3 * watch_score
        else:
            eq = er_score
        eq_parts[p] = {"er_score": round(er_score, 1),
                       "watch_score": round(watch_score, 1) if watch_score is not None else None,
                       "eq": round(eq, 1)}
    if eq_parts:
        w = _weights({p: (kpis[p]["median_reach"] or 1) for p in eq_parts})
        dims["engagement_quality"] = round(sum(w[p] * eq_parts[p]["eq"] for p in eq_parts), 1)
        for p in eq_parts:
            eq_parts[p]["weight"] = round(w[p], 3)
        intermediate["engagement_quality"] = eq_parts
        coverage["dimensions"]["engagement_quality"] = {
            "confidence": _confidence(total_posts), "data_points": total_posts, "unit": "posts"}
    else:
        dims["engagement_quality"] = None
        coverage["dimensions"]["engagement_quality"] = {"confidence": None, "reason": "no_posts"}

    # --- 3. Audience Fit: demographic overlap vs sponsor target ------------
    # Computed by the shared helper below rather than inline, so a match that
    # reuses a stored snapshot for the other four dimensions is running exactly
    # this arithmetic for the one dimension it must recompute. Two copies of a
    # score is how the number in the UI and the number in the model drift apart.
    fit = audience_fit(conn, creator_id, target_id, kpis=kpis, creator=creator)
    dims["audience_fit"] = fit["value"]
    coverage["dimensions"]["audience_fit"] = fit["coverage"]
    if fit["intermediate"] is not None:
        intermediate["audience_fit"] = fit["intermediate"]

    # --- 4. Growth: monthly-ized blend, follower-weighted ------------------
    growth_parts = {}
    for p, k in kpis.items():
        if k["growth_30d"] is None and k["growth_90d"] is None:
            continue
        g30 = k["growth_30d"] if k["growth_30d"] is not None else (k["growth_90d"] or 0) / 3
        g90m = (k["growth_90d"] / 3) if k["growth_90d"] is not None else g30
        rate = 0.6 * g30 + 0.4 * g90m
        growth_parts[p] = {"monthly_rate": round(rate, 4),
                           "score": round(100 * clamp((rate + 0.02) / 0.12), 1)}
    if growth_parts:
        w = _weights({p: (kpis[p]["followers"] or 1) for p in growth_parts})
        dims["growth"] = round(sum(w[p] * growth_parts[p]["score"] for p in growth_parts), 1)
        for p in growth_parts:
            growth_parts[p]["weight"] = round(w[p], 3)
        intermediate["growth"] = growth_parts
        coverage["dimensions"]["growth"] = {
            "confidence": _confidence(snapshot_days), "data_points": snapshot_days, "unit": "snapshot_days"}
    else:
        dims["growth"] = None
        coverage["dimensions"]["growth"] = {"confidence": None, "reason": "insufficient_snapshots"}

    # --- 5. Consistency: cadence vs norm + reach stability, reach-weighted -
    cons_parts = {}
    for p, k in kpis.items():
        if k["posts_in_window"] == 0:
            continue
        cadence_score = 100 * min(k["cadence_per_week"] / CADENCE_NORM[p], 1.0)
        stability = 100 * clamp(1 - ((k["reach_cv"] or 0.3) - 0.3) / 1.2)
        cons_parts[p] = {"cadence_score": round(cadence_score, 1),
                         "stability_score": round(stability, 1),
                         "consistency": round(0.5 * cadence_score + 0.5 * stability, 1)}
    if cons_parts:
        w = _weights({p: (kpis[p]["median_reach"] or 1) for p in cons_parts})
        dims["consistency"] = round(sum(w[p] * cons_parts[p]["consistency"] for p in cons_parts), 1)
        for p in cons_parts:
            cons_parts[p]["weight"] = round(w[p], 3)
        intermediate["consistency"] = cons_parts
        coverage["dimensions"]["consistency"] = {
            "confidence": _confidence(total_posts), "data_points": total_posts, "unit": "posts"}
    else:
        dims["consistency"] = None
        coverage["dimensions"]["consistency"] = {"confidence": None, "reason": "no_posts"}

    return {
        "creator_id": creator_id,
        "sponsor_target_id": target_id,
        "formula_version": FORMULA_VERSION,
        "dimensions": dims,
        "coverage": coverage,
        "inputs": {"platform_kpis": kpis, "intermediate": intermediate,
                   "audience": _combined_demographics(conn, kpis)["dimensions"]},
    }


def demographic_kpis(conn: sqlite3.Connection, creator_id: int) -> dict[str, dict]:
    """The cheap half of `creator_kpis`: which accounts, and how big each is.

    Audience fit needs follower weights and demographic shares. It does NOT need
    the per-post metrics the other four dimensions are built from, and those are
    the expensive part — a correlated lookup per post, per account, per athlete,
    on every matching run. Building only what fit uses is what makes ranking a
    directory affordable.
    """
    out: dict[str, dict] = {}
    for account in rows(conn, "SELECT id, platform FROM platform_accounts"
                        " WHERE creator_id = ? AND connection_status = 'connected'",
                        (creator_id,)):
        snap = row(conn, "SELECT followers FROM account_snapshots WHERE account_id = ?"
                   " ORDER BY snapshot_date DESC LIMIT 1", (account["id"],))
        out[account["platform"]] = {"account_id": account["id"],
                                    "followers": snap["followers"] if snap else None}
    return out


def audience_fit(conn: sqlite3.Connection, creator_id: int, target_id: int | None,
                 kpis: dict[str, dict] | None = None, creator: dict | None = None) -> dict:
    """The one dimension a campaign brief can change.

    Scale, engagement quality, growth and consistency describe the athlete and
    not the brief, so a stored snapshot answers for them however many campaigns
    ask. Fit is the exception: it is overlap against *this* target, so it has to
    be recomputed per campaign — and it is the cheap one.

    Returns `value`, its `coverage` entry and the `intermediate` working, so a
    caller can render the same decomposition either way. `value` is None rather
    than zero when there is no target or no demographics; unmeasured is not a
    measured nought, and every consumer of this depends on the difference.
    """
    if creator is None:
        creator = row(conn, "SELECT * FROM creators WHERE id = ?", (creator_id,))
    if kpis is None:
        kpis = demographic_kpis(conn, creator_id)
    target = (row(conn, "SELECT * FROM sponsor_targets WHERE id = ?", (target_id,))
              if target_id else None)
    if target is None:
        return {"value": None, "intermediate": None,
                "coverage": {"confidence": None, "reason": "no_target"}}
    combined = _combined_demographics(conn, kpis)
    if not combined["dimensions"]:
        return {"value": None, "intermediate": None,
                "coverage": {"confidence": None, "reason": "no_demographics"}}

    demo = combined["dimensions"]
    age_overlap = sum(demo.get("age", {}).get(b, 0.0) for b in json.loads(target["age_buckets"]))
    geo_overlap = sum(demo.get("country", {}).get(c, 0.0) for c in json.loads(target["countries"]))
    target_genders = json.loads(target["genders"])
    gender_overlap = (sum(demo.get("gender", {}).get(g, 0.0) for g in target_genders)
                      if target_genders else 1.0)
    topic_match = 1.0 if creator["primary_topic"] in json.loads(target["topics"]) else 0.3
    value = 100 * (0.35 * age_overlap + 0.30 * geo_overlap
                   + 0.15 * gender_overlap + 0.20 * topic_match)
    n_with, n_data = combined["platforms_with_demos"], len(kpis)
    return {
        "value": round(value, 1),
        "intermediate": {
            "target": target["name"], "age_overlap": round(age_overlap, 3),
            "geo_overlap": round(geo_overlap, 3), "gender_overlap": round(gender_overlap, 3),
            "topic_match": topic_match,
        },
        "coverage": {"confidence": "high" if n_with == n_data else "medium",
                     "data_points": n_with, "unit": "platforms_with_demographics"},
    }


def _combined_demographics(conn: sqlite3.Connection, kpis: dict[str, dict]) -> dict:
    """Aggregate each account's latest demographic set, weighted by followers."""
    sets = {}
    weights = {}
    for p, k in kpis.items():
        demo = latest_demographics(conn, k["account_id"])
        if demo:
            sets[p] = demo
            weights[p] = k["followers"] or 1
    if not sets:
        return {"dimensions": {}, "platforms_with_demos": 0}
    w = _weights(weights)
    combined: dict[str, dict[str, float]] = {}
    for p, demo in sets.items():
        for dim, buckets in demo.items():
            for bucket, share in buckets.items():
                combined.setdefault(dim, {})
                combined[dim][bucket] = combined[dim].get(bucket, 0.0) + share * w[p]
    combined = {dim: {b: round(s, 4) for b, s in sorted(buckets.items(), key=lambda x: -x[1])}
                for dim, buckets in combined.items()}
    return {"dimensions": combined, "platforms_with_demos": len(sets)}


def store_scores(conn: sqlite3.Connection, creator_id: int, target_id: int | None = None,
                 actor: str = "user") -> dict:
    """`creators/recompute-scores`: compute, append snapshot, log event."""
    result = compute_scores(conn, creator_id, target_id)
    d = result["dimensions"]
    cur = conn.execute(
        "INSERT INTO score_snapshots (creator_id, sponsor_target_id, formula_version, computed_at,"
        " coverage_json, audience_scale, engagement_quality, audience_fit, growth, consistency, inputs_json)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (creator_id, result["sponsor_target_id"], result["formula_version"], now_iso(),
         json.dumps(result["coverage"]), d["audience_scale"], d["engagement_quality"],
         d["audience_fit"], d["growth"], d["consistency"], json.dumps(result["inputs"])),
    )
    snapshot_id = cur.lastrowid
    log_event(conn, actor, "scores.computed", "score_snapshot", snapshot_id,
              {"creator_id": creator_id, "dimensions": d,
               "coverage": result["coverage"]["platforms"],
               "formula_version": result["formula_version"]})
    conn.commit()
    result["score_snapshot_id"] = snapshot_id
    return result


def latest_score(conn: sqlite3.Connection, creator_id: int) -> dict | None:
    snap = row(conn,
               "SELECT * FROM score_snapshots WHERE creator_id = ?"
               " ORDER BY computed_at DESC, id DESC LIMIT 1",
               (creator_id,))
    if snap is None:
        return None
    snap["coverage"] = loads(snap.pop("coverage_json"))
    snap["inputs"] = loads(snap.pop("inputs_json"))
    return snap


def score_history(conn: sqlite3.Connection, creator_id: int) -> list[dict]:
    return rows(conn,
                "SELECT id, computed_at, formula_version, sponsor_target_id,"
                " audience_scale, engagement_quality, audience_fit, growth, consistency"
                " FROM score_snapshots WHERE creator_id = ? ORDER BY computed_at DESC, id DESC",
                (creator_id,))
