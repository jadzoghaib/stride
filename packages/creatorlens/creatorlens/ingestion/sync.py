"""Ingestion pipeline — implements docs/workflows.md `accounts/sync-one`.

Validated at the boundary, retried per external call, idempotent by upsert key,
audited via SyncRun + Event. One account's failure never blocks the others.
"""

from __future__ import annotations

import sqlite3
import time

from ..connectors import get_connector
from ..db import now_iso, row
from ..events import log_event

RETRY_DELAYS = (0.5, 1.0, 2.0)  # stepped delays between the 3 attempts


class SyncFetchError(Exception):
    def __init__(self, label: str, cause: Exception):
        super().__init__(f"{label}: {cause}")
        self.label = label
        self.cause = cause


def _with_retries(label: str, fn):
    last: Exception | None = None
    for attempt in range(len(RETRY_DELAYS)):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 — boundary: anything the connector raises
            last = exc
            if attempt < len(RETRY_DELAYS) - 1:
                time.sleep(RETRY_DELAYS[attempt])
    raise SyncFetchError(label, last)


def sync_account(conn: sqlite3.Connection, account_id: int, trigger: str = "manual") -> dict:
    account = row(conn, "SELECT * FROM platform_accounts WHERE id = ?", (account_id,))
    if account is None:
        raise ValueError(f"unknown account id {account_id}")

    # Validate at the boundary: rejects take an explicit branch, logged.
    if account["connection_status"] != "connected":
        log_event(conn, "system", "sync.failed", "platform_account", account_id,
                  {"reason": "not_connected", "trigger": trigger})
        conn.commit()
        return {"status": "rejected", "reason": "not_connected", "account_id": account_id}

    cur = conn.execute(
        "INSERT INTO sync_runs (account_id, trigger_kind, started_at, status) VALUES (?, ?, ?, 'running')",
        (account_id, trigger, now_iso()),
    )
    run_id = cur.lastrowid
    log_event(conn, "system", "sync.started", "sync_run", run_id,
              {"account_id": account_id, "platform": account["platform"],
               "handle": account["handle"], "trigger": trigger})

    connector = get_connector(account["platform"], account["source"])
    handle = account["handle"]
    errors: list[str] = []
    skipped_invalid = 0
    posts_fetched = metrics_written = snapshots_written = 0

    # 1. account snapshots — upsert on (account_id, snapshot_date)
    try:
        snaps = _with_retries("account_snapshots", lambda: connector.fetch_account_snapshots(handle))
        for s in snaps:
            if s.followers < 0 or s.profile_views < 0 or not s.snapshot_date:
                skipped_invalid += 1
                continue
            conn.execute(
                "INSERT INTO account_snapshots (account_id, sync_run_id, snapshot_date, followers, profile_views)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(account_id, snapshot_date) DO UPDATE SET"
                " followers = excluded.followers, profile_views = excluded.profile_views,"
                " sync_run_id = excluded.sync_run_id",
                (account_id, run_id, s.snapshot_date, s.followers, s.profile_views),
            )
            snapshots_written += 1
    except SyncFetchError as exc:
        errors.append(str(exc))

    # 2. posts — upsert on (account_id, external_id); metrics append with provenance
    try:
        posts = _with_retries("posts", lambda: connector.fetch_posts(handle))
        posts_fetched = len(posts)
        captured_at = now_iso()
        for p in posts:
            m = p.metrics
            if not p.external_id or m is None or min(m.reach, m.impressions, m.likes, m.comments, m.shares, m.saves) < 0:
                skipped_invalid += 1
                continue
            conn.execute(
                "INSERT INTO posts (account_id, external_id, content_type, title, published_at, permalink)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(account_id, external_id) DO UPDATE SET"
                " title = excluded.title, permalink = excluded.permalink",
                (account_id, p.external_id, p.content_type, p.title, p.published_at, p.permalink),
            )
            post_id = row(conn, "SELECT id FROM posts WHERE account_id = ? AND external_id = ?",
                          (account_id, p.external_id))["id"]
            conn.execute(
                "INSERT INTO post_metrics (post_id, sync_run_id, captured_at, reach, impressions,"
                " likes, comments, shares, saves, watch_time_s, avg_view_duration_s)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (post_id, run_id, captured_at, m.reach, m.impressions, m.likes, m.comments,
                 m.shares, m.saves, m.watch_time_s, m.avg_view_duration_s),
            )
            metrics_written += 1
    except SyncFetchError as exc:
        errors.append(str(exc))

    # 3. demographics — full set per run; the latest run's set is current
    try:
        demos = _with_retries("demographics", lambda: connector.fetch_demographics(handle))
        captured_at = now_iso()
        for d in demos:
            if not (0.0 <= d.share <= 1.0) or d.dimension not in ("age", "gender", "country"):
                skipped_invalid += 1
                continue
            conn.execute(
                "INSERT INTO audience_demographics (account_id, sync_run_id, captured_at, dimension, bucket, share)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (account_id, run_id, captured_at, d.dimension, d.bucket, d.share),
            )
    except SyncFetchError as exc:
        errors.append(str(exc))

    # close the run
    if len(errors) == 3:
        status = "failed"
    elif errors:
        status = "partial"
    else:
        status = "succeeded"
    error_text = "; ".join(errors) if errors else None
    if skipped_invalid and status == "succeeded":
        error_text = f"{skipped_invalid} invalid row(s) skipped"

    conn.execute(
        "UPDATE sync_runs SET finished_at = ?, status = ?, posts_fetched = ?,"
        " metrics_written = ?, snapshots_written = ?, error = ? WHERE id = ?",
        (now_iso(), status, posts_fetched, metrics_written, snapshots_written, error_text, run_id),
    )
    if status == "failed":
        conn.execute("UPDATE platform_accounts SET connection_status = 'error' WHERE id = ?", (account_id,))
        log_event(conn, "system", "sync.failed", "sync_run", run_id,
                  {"account_id": account_id, "error": error_text})
    else:
        conn.execute(
            "UPDATE platform_accounts SET last_synced_at = ?, connection_status = 'connected' WHERE id = ?",
            (now_iso(), account_id),
        )
        log_event(conn, "system", "sync.finished", "sync_run", run_id,
                  {"account_id": account_id, "status": status, "posts_fetched": posts_fetched,
                   "metrics_written": metrics_written, "snapshots_written": snapshots_written,
                   "error": error_text})
    conn.commit()
    return {
        "status": status, "sync_run_id": run_id, "account_id": account_id,
        "posts_fetched": posts_fetched, "metrics_written": metrics_written,
        "snapshots_written": snapshots_written, "error": error_text,
    }


def sync_all(conn: sqlite3.Connection, trigger: str = "scheduled") -> list[dict]:
    """`accounts/sync-all`: per-account isolation — one failure never blocks the rest."""
    results = []
    accounts = conn.execute(
        "SELECT id FROM platform_accounts WHERE connection_status = 'connected' ORDER BY id"
    ).fetchall()
    for acc in accounts:
        try:
            results.append(sync_account(conn, acc["id"], trigger))
        except Exception as exc:  # noqa: BLE001
            results.append({"status": "failed", "account_id": acc["id"], "error": str(exc)})
    return results
