"""Per-platform KPIs over the scoring window — the inputs every dimension cites.

All KPIs derive from the *latest* metric capture per post (older captures remain
in post_metrics as superseded lineage) and from daily account snapshots.
"""

from __future__ import annotations

import sqlite3
import statistics
from datetime import date, datetime, timedelta, timezone

from ..db import rows

WINDOW_DAYS = 90

# engagement-rate numerator per platform (denominator: reach; yt reach == views proxy)
ER_NUMERATOR = {
    "instagram": ("likes", "comments", "shares", "saves"),
    "tiktok": ("likes", "comments", "shares"),
    "youtube": ("likes", "comments"),
}


def _window_start_iso(days: int = WINDOW_DAYS) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")


def latest_post_metrics(conn: sqlite3.Connection, account_id: int, window_days: int = WINDOW_DAYS) -> list[dict]:
    """Posts in the window with each post's most recent metric capture."""
    return rows(
        conn,
        """
        SELECT p.id AS post_id, p.external_id, p.content_type, p.title, p.published_at, p.permalink,
               m.reach, m.impressions, m.likes, m.comments, m.shares, m.saves,
               m.watch_time_s, m.avg_view_duration_s, m.captured_at, m.sync_run_id
        FROM posts p
        JOIN post_metrics m ON m.id = (
            SELECT id FROM post_metrics WHERE post_id = p.id
            ORDER BY captured_at DESC, id DESC LIMIT 1)
        WHERE p.account_id = ? AND p.published_at >= ?
        ORDER BY p.published_at DESC
        """,
        (account_id, _window_start_iso(window_days)),
    )


def engagement_rate(platform: str, post: dict) -> float | None:
    if not post["reach"]:
        return None
    numerator = sum(post[f] or 0 for f in ER_NUMERATOR[platform])
    return numerator / post["reach"]


def _followers_on_or_before(snaps: list[dict], day: str) -> int | None:
    """snaps sorted ascending by snapshot_date; nearest snapshot <= day."""
    best = None
    for s in snaps:
        if s["snapshot_date"] <= day:
            best = s["followers"]
        else:
            break
    return best


def account_kpis(conn: sqlite3.Connection, account: dict) -> dict | None:
    """KPI set for one account, or None when no data exists at all."""
    account_id = account["id"]
    platform = account["platform"]

    posts = latest_post_metrics(conn, account_id)
    snaps = rows(conn,
                 "SELECT snapshot_date, followers FROM account_snapshots"
                 " WHERE account_id = ? ORDER BY snapshot_date",
                 (account_id,))
    if not posts and not snaps:
        return None

    today = date.today()
    window_start = (today - timedelta(days=WINDOW_DAYS)).isoformat()
    snaps_in_window = [s for s in snaps if s["snapshot_date"] >= window_start]

    followers = snaps[-1]["followers"] if snaps else None
    f30 = _followers_on_or_before(snaps, (today - timedelta(days=30)).isoformat())
    f90 = _followers_on_or_before(snaps, (today - timedelta(days=90)).isoformat())
    growth_30d = (followers - f30) / f30 if followers is not None and f30 else None
    growth_90d = (followers - f90) / f90 if followers is not None and f90 else None

    reaches = [p["reach"] for p in posts if p["reach"] is not None]
    ers = [er for p in posts if (er := engagement_rate(platform, p)) is not None]
    durations = [p["avg_view_duration_s"] for p in posts if p["avg_view_duration_s"] is not None]

    reach_cv = None
    if len(reaches) >= 2 and statistics.mean(reaches) > 0:
        reach_cv = statistics.stdev(reaches) / statistics.mean(reaches)

    return {
        "account_id": account_id,
        "platform": platform,
        "handle": account["handle"],
        "followers": followers,
        "growth_30d": round(growth_30d, 4) if growth_30d is not None else None,
        "growth_90d": round(growth_90d, 4) if growth_90d is not None else None,
        "median_reach": int(statistics.median(reaches)) if reaches else None,
        "median_er": round(statistics.median(ers), 5) if ers else None,
        "avg_view_duration_s": round(statistics.mean(durations), 1) if durations else None,
        "posts_in_window": len(posts),
        "cadence_per_week": round(len(posts) / (WINDOW_DAYS / 7), 2),
        "reach_cv": round(reach_cv, 3) if reach_cv is not None else None,
        "snapshot_days": len(snaps_in_window),
        "window_days": WINDOW_DAYS,
    }


def creator_kpis(conn: sqlite3.Connection, creator_id: int) -> dict[str, dict]:
    """KPIs per platform for a creator's *connected* accounts (missing = absent, never zero)."""
    accounts = rows(conn,
                    "SELECT * FROM platform_accounts WHERE creator_id = ? AND connection_status = 'connected'",
                    (creator_id,))
    out: dict[str, dict] = {}
    for account in accounts:
        kpis = account_kpis(conn, account)
        if kpis is not None:
            out[account["platform"]] = kpis
    return out


def latest_demographics(conn: sqlite3.Connection, account_id: int) -> dict[str, dict[str, float]]:
    """The most recent sync run's demographic set, as {dimension: {bucket: share}}."""
    latest = conn.execute(
        "SELECT MAX(sync_run_id) AS run FROM audience_demographics WHERE account_id = ?",
        (account_id,),
    ).fetchone()
    if latest is None or latest["run"] is None:
        return {}
    out: dict[str, dict[str, float]] = {}
    for r in rows(conn,
                  "SELECT dimension, bucket, share FROM audience_demographics"
                  " WHERE account_id = ? AND sync_run_id = ?",
                  (account_id, latest["run"])):
        out.setdefault(r["dimension"], {})[r["bucket"]] = r["share"]
    return out
