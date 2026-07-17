"""SQLite persistence layer. The schema renders docs/ontology.md 1:1.

DB location: ./data/creatorlens.db relative to the working directory,
overridable with the CREATORLENS_DB environment variable.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db_path() -> Path:
    env = os.environ.get("CREATORLENS_DB")
    return Path(env) if env else Path.cwd() / "data" / "creatorlens.db"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI may run a request's dependency and endpoint
    # on different threadpool threads; each connection stays request-scoped, so it
    # is never used by two threads concurrently.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def loads(text: str | None) -> dict | list | None:
    return json.loads(text) if text else None


SCHEMA = """
CREATE TABLE IF NOT EXISTS creators (
    id            INTEGER PRIMARY KEY,
    handle        TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    primary_topic TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_accounts (
    id                INTEGER PRIMARY KEY,
    creator_id        INTEGER NOT NULL REFERENCES creators(id),
    platform          TEXT NOT NULL CHECK (platform IN ('instagram','youtube','tiktok')),
    handle            TEXT NOT NULL,
    external_id       TEXT NOT NULL,
    connection_status TEXT NOT NULL CHECK (connection_status IN ('connected','disconnected','error')),
    source            TEXT NOT NULL DEFAULT 'mock' CHECK (source IN ('mock','live')),
    connected_at      TEXT NOT NULL,
    last_synced_at    TEXT,
    UNIQUE (creator_id, platform)
);

CREATE TABLE IF NOT EXISTS posts (
    id           INTEGER PRIMARY KEY,
    account_id   INTEGER NOT NULL REFERENCES platform_accounts(id),
    external_id  TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title        TEXT NOT NULL,
    published_at TEXT NOT NULL,
    permalink    TEXT NOT NULL,
    UNIQUE (account_id, external_id)
);

CREATE TABLE IF NOT EXISTS post_metrics (
    id                  INTEGER PRIMARY KEY,
    post_id             INTEGER NOT NULL REFERENCES posts(id),
    sync_run_id         INTEGER NOT NULL REFERENCES sync_runs(id),
    captured_at         TEXT NOT NULL,
    reach               INTEGER NOT NULL,
    impressions         INTEGER NOT NULL,
    likes               INTEGER NOT NULL,
    comments            INTEGER NOT NULL,
    shares              INTEGER NOT NULL,
    saves               INTEGER NOT NULL DEFAULT 0,
    watch_time_s        INTEGER,
    avg_view_duration_s REAL
);
CREATE INDEX IF NOT EXISTS idx_post_metrics_post ON post_metrics(post_id, captured_at);

CREATE TABLE IF NOT EXISTS account_snapshots (
    id            INTEGER PRIMARY KEY,
    account_id    INTEGER NOT NULL REFERENCES platform_accounts(id),
    sync_run_id   INTEGER NOT NULL REFERENCES sync_runs(id),
    snapshot_date TEXT NOT NULL,
    followers     INTEGER NOT NULL,
    profile_views INTEGER NOT NULL DEFAULT 0,
    UNIQUE (account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS audience_demographics (
    id          INTEGER PRIMARY KEY,
    account_id  INTEGER NOT NULL REFERENCES platform_accounts(id),
    sync_run_id INTEGER NOT NULL REFERENCES sync_runs(id),
    captured_at TEXT NOT NULL,
    dimension   TEXT NOT NULL CHECK (dimension IN ('age','gender','country')),
    bucket      TEXT NOT NULL,
    share       REAL NOT NULL CHECK (share >= 0 AND share <= 1)
);
CREATE INDEX IF NOT EXISTS idx_demographics_account ON audience_demographics(account_id, sync_run_id);

CREATE TABLE IF NOT EXISTS sync_runs (
    id                INTEGER PRIMARY KEY,
    account_id        INTEGER NOT NULL REFERENCES platform_accounts(id),
    trigger_kind      TEXT NOT NULL CHECK (trigger_kind IN ('seed','manual','scheduled')),
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    status            TEXT NOT NULL CHECK (status IN ('running','succeeded','partial','failed')),
    posts_fetched     INTEGER NOT NULL DEFAULT 0,
    metrics_written   INTEGER NOT NULL DEFAULT 0,
    snapshots_written INTEGER NOT NULL DEFAULT 0,
    error             TEXT
);

CREATE TABLE IF NOT EXISTS sponsor_targets (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    age_buckets TEXT NOT NULL,
    genders     TEXT NOT NULL,
    countries   TEXT NOT NULL,
    topics      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS score_snapshots (
    id                 INTEGER PRIMARY KEY,
    creator_id         INTEGER NOT NULL REFERENCES creators(id),
    sponsor_target_id  INTEGER REFERENCES sponsor_targets(id),
    formula_version    TEXT NOT NULL,
    computed_at        TEXT NOT NULL,
    coverage_json      TEXT NOT NULL,
    audience_scale     REAL,
    engagement_quality REAL,
    audience_fit       REAL,
    growth             REAL,
    consistency        REAL,
    inputs_json        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scores_creator ON score_snapshots(creator_id, computed_at);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    ts          TEXT NOT NULL,
    actor       TEXT NOT NULL CHECK (actor IN ('user','system')),
    event_type  TEXT NOT NULL,
    object_type TEXT,
    object_id   INTEGER,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
