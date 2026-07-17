"""API surface. Every route is a projection of the ontology; every write path
is a governed action that lands in the audit log. Serves the operator console
(web/) at the root.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .. import FORMULA_VERSION, PLATFORMS, __version__
from ..actions import ActionRejected, connect_platform, create_creator, create_target, disconnect_platform
from ..analytics.kpis import WINDOW_DAYS, engagement_rate, latest_post_metrics
from ..analytics.scoring import (
    InsufficientData,
    _combined_demographics,  # noqa: PLC2401 — same-package reuse
    latest_score,
    score_history,
    store_scores,
)
from ..analytics.kpis import creator_kpis
from ..db import connect, init_db, loads, row, rows
from ..ingestion import sync_account
from ..seed import is_seeded, seed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect()
    init_db(conn)
    if not is_seeded(conn):
        seed(conn)
    conn.close()
    yield


app = FastAPI(title="CreatorLens", version=__version__, lifespan=lifespan)


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


class CreatorIn(BaseModel):
    handle: str
    display_name: str
    primary_topic: str


class ConnectIn(BaseModel):
    platform: str
    handle: str | None = None


class RecomputeIn(BaseModel):
    target_id: int | None = 1


class TargetIn(BaseModel):
    name: str
    age_buckets: list[str] = []
    genders: list[str] = []
    countries: list[str] = []
    topics: list[str] = []


def _reject(exc: ActionRejected | InsufficientData):
    raise HTTPException(status_code=409, detail=exc.reason)


def _account_view(conn: sqlite3.Connection, account: dict) -> dict:
    latest_snap = row(conn,
                      "SELECT snapshot_date, followers FROM account_snapshots"
                      " WHERE account_id = ? ORDER BY snapshot_date DESC LIMIT 1",
                      (account["id"],))
    last_run = row(conn,
                   "SELECT id, status, finished_at, posts_fetched, metrics_written, error"
                   " FROM sync_runs WHERE account_id = ? ORDER BY started_at DESC, id DESC LIMIT 1",
                   (account["id"],))
    return {**account, "followers": latest_snap["followers"] if latest_snap else None,
            "last_sync_run": last_run}


@app.get("/api/meta")
def meta(conn: sqlite3.Connection = Depends(get_db)):
    return {
        "version": __version__,
        "formula_version": FORMULA_VERSION,
        "platforms": list(PLATFORMS),
        "window_days": WINDOW_DAYS,
        "counts": {t: row(conn, f"SELECT COUNT(*) AS n FROM {t}")["n"]  # noqa: S608 — fixed table list
                   for t in ("creators", "platform_accounts", "posts", "post_metrics",
                             "account_snapshots", "sync_runs", "score_snapshots", "events")},
    }


@app.get("/api/creators")
def list_creators(conn: sqlite3.Connection = Depends(get_db)):
    out = []
    for creator in rows(conn, "SELECT * FROM creators ORDER BY display_name"):
        accounts = [_account_view(conn, a) for a in
                    rows(conn, "SELECT * FROM platform_accounts WHERE creator_id = ?", (creator["id"],))]
        score = latest_score(conn, creator["id"])
        out.append({
            **creator,
            "accounts": accounts,
            "total_followers": sum(a["followers"] or 0 for a in accounts
                                   if a["connection_status"] == "connected"),
            "latest_score": _score_summary(score),
        })
    return out


def _score_summary(score: dict | None) -> dict | None:
    if score is None:
        return None
    return {k: score[k] for k in ("id", "computed_at", "formula_version", "sponsor_target_id",
                                  "audience_scale", "engagement_quality", "audience_fit",
                                  "growth", "consistency", "coverage")}


@app.post("/api/creators", status_code=201)
def add_creator(body: CreatorIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        return create_creator(conn, body.handle, body.display_name, body.primary_topic, actor="user")
    except ActionRejected as exc:
        _reject(exc)


@app.get("/api/creators/{creator_id}")
def creator_detail(creator_id: int, conn: sqlite3.Connection = Depends(get_db)):
    creator = row(conn, "SELECT * FROM creators WHERE id = ?", (creator_id,))
    if creator is None:
        raise HTTPException(404, "unknown creator")
    accounts = [_account_view(conn, a) for a in
                rows(conn, "SELECT * FROM platform_accounts WHERE creator_id = ?", (creator_id,))]
    score = latest_score(conn, creator_id)
    return {
        **creator,
        "accounts": accounts,
        "total_followers": sum(a["followers"] or 0 for a in accounts
                               if a["connection_status"] == "connected"),
        "latest_score": score,
        "score_history": score_history(conn, creator_id),
    }


@app.get("/api/creators/{creator_id}/posts")
def creator_posts(creator_id: int, limit: int = Query(120, le=500),
                  conn: sqlite3.Connection = Depends(get_db)):
    accounts = rows(conn, "SELECT * FROM platform_accounts WHERE creator_id = ?", (creator_id,))
    posts = []
    for account in accounts:
        for p in latest_post_metrics(conn, account["id"]):
            er = engagement_rate(account["platform"], p)
            posts.append({**p, "platform": account["platform"],
                          "engagement_rate": round(er, 5) if er is not None else None})
    posts.sort(key=lambda p: p["published_at"], reverse=True)
    return posts[:limit]


@app.get("/api/creators/{creator_id}/audience")
def creator_audience(creator_id: int, conn: sqlite3.Connection = Depends(get_db)):
    kpis = creator_kpis(conn, creator_id)
    return _combined_demographics(conn, kpis)


@app.get("/api/creators/{creator_id}/timeline")
def creator_timeline(creator_id: int, limit: int = Query(100, le=500),
                     conn: sqlite3.Connection = Depends(get_db)):
    account_ids = [r["id"] for r in rows(conn,
                   "SELECT id FROM platform_accounts WHERE creator_id = ?", (creator_id,))]
    run_ids = [r["id"] for r in rows(conn,
               f"SELECT id FROM sync_runs WHERE account_id IN ({_ph(account_ids)})", tuple(account_ids))] \
        if account_ids else []
    score_ids = [r["id"] for r in rows(conn,
                 "SELECT id FROM score_snapshots WHERE creator_id = ?", (creator_id,))]

    clauses = ["(object_type = 'creator' AND object_id = ?)"]
    params: list = [creator_id]
    for object_type, ids in (("platform_account", account_ids), ("sync_run", run_ids),
                             ("score_snapshot", score_ids)):
        if ids:
            clauses.append(f"(object_type = '{object_type}' AND object_id IN ({_ph(ids)}))")
            params.extend(ids)
    events = rows(conn,
                  f"SELECT * FROM events WHERE {' OR '.join(clauses)}"
                  " ORDER BY ts DESC, id DESC LIMIT ?",
                  tuple(params) + (limit,))
    return [_event_view(e) for e in events]


def _ph(ids: list[int]) -> str:
    return ",".join("?" * len(ids))


def _event_view(e: dict) -> dict:
    e["detail"] = loads(e.pop("detail_json")) or {}
    return e


@app.post("/api/creators/{creator_id}/connect")
def connect_account(creator_id: int, body: ConnectIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        account = connect_platform(conn, creator_id, body.platform, body.handle, actor="user")
    except ActionRejected as exc:
        _reject(exc)
    sync_result = sync_account(conn, account["id"], trigger="manual")
    return {"account": _account_view(conn, row(conn, "SELECT * FROM platform_accounts WHERE id = ?",
                                               (account["id"],))),
            "sync": sync_result}


@app.post("/api/accounts/{account_id}/disconnect")
def disconnect_account(account_id: int, conn: sqlite3.Connection = Depends(get_db)):
    try:
        return disconnect_platform(conn, account_id, actor="user")
    except ActionRejected as exc:
        _reject(exc)


@app.post("/api/accounts/{account_id}/sync")
def trigger_sync(account_id: int, conn: sqlite3.Connection = Depends(get_db)):
    account = row(conn, "SELECT id FROM platform_accounts WHERE id = ?", (account_id,))
    if account is None:
        raise HTTPException(404, "unknown account")
    result = sync_account(conn, account_id, trigger="manual")
    if result["status"] == "rejected":
        raise HTTPException(409, result["reason"])
    return result


@app.get("/api/accounts/{account_id}/snapshots")
def account_snapshots(account_id: int, days: int = Query(90, le=365),
                      conn: sqlite3.Connection = Depends(get_db)):
    return rows(conn,
                "SELECT snapshot_date, followers, profile_views FROM account_snapshots"
                " WHERE account_id = ? ORDER BY snapshot_date DESC LIMIT ?",
                (account_id, days))[::-1]


@app.post("/api/creators/{creator_id}/recompute")
def recompute(creator_id: int, body: RecomputeIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        result = store_scores(conn, creator_id, target_id=body.target_id, actor="user")
    except InsufficientData as exc:
        _reject(exc)
    except ValueError:
        raise HTTPException(404, "unknown creator")
    return result


@app.get("/api/targets")
def list_targets(conn: sqlite3.Connection = Depends(get_db)):
    out = []
    for t in rows(conn, "SELECT * FROM sponsor_targets ORDER BY id"):
        for field in ("age_buckets", "genders", "countries", "topics"):
            t[field] = json.loads(t[field])
        out.append(t)
    return out


@app.post("/api/targets", status_code=201)
def add_target(body: TargetIn, conn: sqlite3.Connection = Depends(get_db)):
    try:
        return create_target(conn, body.name, body.age_buckets, body.genders,
                             body.countries, body.topics, actor="user")
    except ActionRejected as exc:
        _reject(exc)


@app.get("/api/events")
def list_events(event_type: str | None = None, limit: int = Query(150, le=1000),
                conn: sqlite3.Connection = Depends(get_db)):
    if event_type:
        events = rows(conn, "SELECT * FROM events WHERE event_type = ? ORDER BY ts DESC, id DESC LIMIT ?",
                      (event_type, limit))
    else:
        events = rows(conn, "SELECT * FROM events ORDER BY ts DESC, id DESC LIMIT ?", (limit,))
    return [_event_view(e) for e in events]


WEB_DIR = Path(__file__).resolve().parent.parent / "web"
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="console")
