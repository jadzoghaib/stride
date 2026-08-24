"""Stride persistence layer.

One database holds both the Stride product tables (below) and the CreatorLens
analytics tables — every CreatorLens function takes an explicit connection, so
both layers share one transaction boundary. Two backends, one code path:

  * SQLite (default) — a file at settings.db_path, for the local draft.
  * Postgres — when STRIDE_DATABASE_URL is set (Supabase / RDS / docker). The
    pgconn shim makes psycopg present the same connection surface, and
    schema_pg.sql is the Postgres DDL (dependency-ordered, app-faithful types).

The `events` audit table is CreatorLens's — Stride logs into the same one.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from creatorlens.db import SCHEMA as CREATORLENS_SCHEMA
from creatorlens.db import now_iso  # noqa: F401 — re-exported for the rest of the app

from .config import settings

_PG_SCHEMA = Path(__file__).with_name("schema_pg.sql")

# Every table the app owns, child-first, for a clean Postgres reset.
_ALL_TABLES = (
    "deal_deliverables",
    "package_commitments", "club_packages", "club_members", "clubs",
    "follows", "deals", "campaigns", "sponsor_orgs", "athlete_profiles", "users",
    "events", "score_snapshots", "sponsor_targets", "audience_demographics",
    "account_snapshots", "post_metrics", "posts", "sync_runs", "platform_accounts", "creators",
)


def connect():
    if settings.db_backend == "postgres":
        from .pgconn import PgConnection
        return PgConnection(settings.database_url)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI may run a request's dependency and endpoint
    # on different threadpool threads; connections stay request-scoped.
    conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def row(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def loads_events(events: list[dict]) -> list[dict]:
    import json
    for e in events:
        e["detail"] = json.loads(e.pop("detail_json") or "{}")
    return events


STRIDE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('athlete','sponsor','fan','club','admin')),
    display_name  TEXT NOT NULL,
    auth_id       TEXT UNIQUE,                          -- Supabase auth.users id when wired
    token_version INTEGER NOT NULL DEFAULT 1,           -- bump to revoke all sessions
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS athlete_profiles (
    id                      INTEGER PRIMARY KEY,
    user_id                 INTEGER UNIQUE REFERENCES users(id),   -- null = seeded, unclaimed
    slug                    TEXT NOT NULL UNIQUE,
    display_name            TEXT NOT NULL,
    sport                   TEXT NOT NULL,
    country                 TEXT NOT NULL,
    region                  TEXT NOT NULL,
    bio                     TEXT NOT NULL DEFAULT '',
    career_highlights       TEXT NOT NULL DEFAULT '[]',            -- json list of strings
    topics                  TEXT NOT NULL DEFAULT '[]',            -- json list: audience themes
    deal_types              TEXT NOT NULL DEFAULT '[]',            -- json list of DEAL_TYPES
    base_rate_usd           INTEGER NOT NULL DEFAULT 1000,         -- per engagement, rate card anchor
    status                  TEXT NOT NULL DEFAULT 'listed' CHECK (status IN ('draft','listed','hidden')),
    creatorlens_creator_id  INTEGER,                               -- analytics identity (creators.id)
    created_at              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_athletes_sport ON athlete_profiles(sport);

CREATE TABLE IF NOT EXISTS sponsor_orgs (
    id          INTEGER PRIMARY KEY,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id),
    name        TEXT NOT NULL,
    industry    TEXT NOT NULL,
    regions     TEXT NOT NULL DEFAULT '[]',
    website     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id                 INTEGER PRIMARY KEY,
    org_id             INTEGER NOT NULL REFERENCES sponsor_orgs(id),
    name               TEXT NOT NULL,
    objective          TEXT NOT NULL DEFAULT '',
    category           TEXT NOT NULL,
    deal_types         TEXT NOT NULL DEFAULT '[]',
    budget_usd_min     INTEGER NOT NULL DEFAULT 1000,
    budget_usd_max     INTEGER NOT NULL DEFAULT 10000,
    target_age_buckets TEXT NOT NULL DEFAULT '[]',
    target_genders     TEXT NOT NULL DEFAULT '[]',
    target_countries   TEXT NOT NULL DEFAULT '[]',
    target_topics      TEXT NOT NULL DEFAULT '[]',
    sponsor_target_id  INTEGER,                                    -- creatorlens sponsor_targets.id
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','closed')),
    created_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_org ON campaigns(org_id);

CREATE TABLE IF NOT EXISTS deals (
    id           INTEGER PRIMARY KEY,
    campaign_id  INTEGER NOT NULL REFERENCES campaigns(id),
    org_id       INTEGER NOT NULL REFERENCES sponsor_orgs(id),
    athlete_id   INTEGER NOT NULL REFERENCES athlete_profiles(id),
    deal_type    TEXT NOT NULL,
    amount_usd   INTEGER NOT NULL,
    message      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'offered'
                 CHECK (status IN ('offered','accepted','declined','withdrawn','completed')),
    created_at   TEXT NOT NULL,
    responded_at TEXT,
    completed_at TEXT,
    -- Captured when the OFFER is sent, not at completion: once the athlete's
    -- following moves there is nothing left to measure delivery against.
    projected_reach INTEGER
);
CREATE INDEX IF NOT EXISTS idx_deals_athlete ON deals(athlete_id, status);

-- What actually fulfilled a deal. Everything needed to measure a campaign
-- already exists in posts/post_metrics; this is the missing link between the
-- commercial record and the content.
CREATE TABLE IF NOT EXISTS deal_deliverables (
    id       INTEGER PRIMARY KEY,
    deal_id  INTEGER NOT NULL REFERENCES deals(id),
    post_id  INTEGER NOT NULL REFERENCES posts(id),
    added_at TEXT NOT NULL,
    UNIQUE (deal_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_deliverables_deal ON deal_deliverables(deal_id);
CREATE INDEX IF NOT EXISTS idx_deals_org ON deals(org_id, status);

CREATE TABLE IF NOT EXISTS follows (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    athlete_id INTEGER NOT NULL REFERENCES athlete_profiles(id),
    created_at TEXT NOT NULL,
    UNIQUE (user_id, athlete_id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER UNIQUE REFERENCES users(id),
    slug       TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    sport      TEXT NOT NULL,
    country    TEXT NOT NULL,
    region     TEXT NOT NULL,
    bio        TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'listed' CHECK (status IN ('draft','listed','hidden')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS club_members (
    id         INTEGER PRIMARY KEY,
    club_id    INTEGER NOT NULL REFERENCES clubs(id),
    athlete_id INTEGER NOT NULL REFERENCES athlete_profiles(id),
    position   TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','former')),
    joined_at  TEXT NOT NULL,
    UNIQUE (club_id, athlete_id)
);

CREATE TABLE IF NOT EXISTS club_packages (
    id           INTEGER PRIMARY KEY,
    club_id      INTEGER NOT NULL REFERENCES clubs(id),
    athlete_id   INTEGER REFERENCES athlete_profiles(id),  -- set when package_type='player_direct'
    name         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    package_type TEXT NOT NULL CHECK (package_type IN ('club','player_direct')),
    price_usd    INTEGER NOT NULL,
    perks        TEXT NOT NULL DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_packages_club ON club_packages(club_id, status);

CREATE TABLE IF NOT EXISTS package_commitments (
    id           INTEGER PRIMARY KEY,
    package_id   INTEGER NOT NULL REFERENCES club_packages(id),
    org_id       INTEGER NOT NULL REFERENCES sponsor_orgs(id),
    amount_usd   INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled')),
    created_at   TEXT NOT NULL,
    cancelled_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_commitments_org ON package_commitments(org_id, status);
"""


# Columns added to a table that had already shipped. The schema above is
# written with CREATE TABLE IF NOT EXISTS, which is a no-op against a database
# that already has the table — so a column added later never reaches an existing
# one, and the first request to read it fails with "no such column" while a
# fresh database (every test run) passes. Keep this list append-only and
# additive: it is a column backfill, not a migration framework, and anything
# that rewrites or drops data needs a real one.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("deals", "completed_at", "TEXT"),
    ("deals", "projected_reach", "INTEGER"),
)


def _add_missing_columns(conn) -> None:
    if settings.db_backend == "postgres":
        for table, column, decl in _ADDED_COLUMNS:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {decl}")
        return
    # SQLite has no ADD COLUMN IF NOT EXISTS, so ask first.
    for table, column, decl in _ADDED_COLUMNS:
        if column not in {c["name"] for c in rows(conn, f"PRAGMA table_info({table})")}:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def init_db(conn) -> None:
    if settings.db_backend == "postgres":
        conn.executescript(_PG_SCHEMA.read_text(encoding="utf-8"))
    else:
        conn.executescript(CREATORLENS_SCHEMA)  # analytics tables + shared events audit log
        conn.executescript(STRIDE_SCHEMA)
    _add_missing_columns(conn)
    conn.commit()


def drop_all(conn) -> None:
    """Postgres-only teardown for `stride reset` (SQLite just deletes its file)."""
    conn.executescript("".join(f"DROP TABLE IF EXISTS {t} CASCADE;" for t in _ALL_TABLES))
    conn.commit()
