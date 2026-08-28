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
    "deal_deliverables", "athlete_applications", "club_applications",
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
    base_rate_eur           INTEGER NOT NULL DEFAULT 1000,         -- per engagement, rate card anchor
    status                  TEXT NOT NULL DEFAULT 'listed' CHECK (status IN ('draft','listed','hidden')),
    creatorlens_creator_id  INTEGER,                               -- analytics identity (creators.id)
    created_at              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_athletes_sport ON athlete_profiles(sport);
-- the directory and every matching run filter on status before anything else
CREATE INDEX IF NOT EXISTS idx_athletes_status ON athlete_profiles(status);

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
    budget_eur_min     INTEGER NOT NULL DEFAULT 1000,
    budget_eur_max     INTEGER NOT NULL DEFAULT 10000,
    target_age_buckets TEXT NOT NULL DEFAULT '[]',
    target_genders     TEXT NOT NULL DEFAULT '[]',
    target_countries   TEXT NOT NULL DEFAULT '[]',
    target_topics      TEXT NOT NULL DEFAULT '[]',
    sponsor_target_id  INTEGER,                                    -- creatorlens sponsor_targets.id
    -- a hard retrieval filter, not a weighted term: see matching.candidates().
    -- BOOLEAN rather than INTEGER so the fresh and migrated forms of this column
    -- agree on both backends — SQLite gives it NUMERIC affinity and stores 0/1.
    require_verified_athletes BOOLEAN NOT NULL DEFAULT FALSE,
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
    amount_eur   INTEGER NOT NULL,
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
-- _speed_to_first_offer groups deals by campaign
CREATE INDEX IF NOT EXISTS idx_deals_campaign ON deals(campaign_id);

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

-- Admission. Structured applications are the only cold-start evidence the
-- platform has, so they are stored whole: the decision is reproducible from the
-- row that produced it, and `policy_version` says which rules were in force.
CREATE TABLE IF NOT EXISTS athlete_applications (
    id                INTEGER PRIMARY KEY,
    athlete_id        INTEGER NOT NULL UNIQUE REFERENCES athlete_profiles(id),
    discipline        TEXT NOT NULL DEFAULT '',
    club_name         TEXT NOT NULL DEFAULT '',
    league_name       TEXT NOT NULL DEFAULT '',
    competition_level TEXT NOT NULL DEFAULT '',
    years_competing   INTEGER,
    birth_year        INTEGER,
    proof_url         TEXT NOT NULL DEFAULT '',
    proof_kind        TEXT NOT NULL DEFAULT 'none'
                      CHECK (proof_kind IN ('none','roster','results','licence')),
    proof_status      TEXT NOT NULL DEFAULT 'unverified'
                      CHECK (proof_status IN ('unverified','pending','verified','rejected')),
    -- set when a verified club vouched for them; the pair with `admitted_via` is
    -- what makes de-verifying that club a reversible act rather than a wish
    nominated_by_club INTEGER REFERENCES clubs(id),
    credibility       REAL,
    decision          TEXT NOT NULL DEFAULT 'pending'
                      CHECK (decision IN ('pending','admitted','review','rejected')),
    decision_rule     TEXT NOT NULL DEFAULT '',
    admitted_via      TEXT NOT NULL DEFAULT ''
                      CHECK (admitted_via IN ('','self','club_nomination','manual')),
    policy_version    TEXT NOT NULL DEFAULT '',
    submitted_at      TEXT NOT NULL,
    decided_at        TEXT
);
CREATE INDEX IF NOT EXISTS idx_applications_decision ON athlete_applications(decision);
CREATE INDEX IF NOT EXISTS idx_applications_club ON athlete_applications(nominated_by_club);

CREATE TABLE IF NOT EXISTS club_applications (
    id                  INTEGER PRIMARY KEY,
    club_id             INTEGER NOT NULL UNIQUE REFERENCES clubs(id),
    legal_name          TEXT NOT NULL DEFAULT '',
    registration_id     TEXT NOT NULL DEFAULT '',
    federation_name     TEXT NOT NULL DEFAULT '',
    federation_id       TEXT NOT NULL DEFAULT '',
    founded_year        INTEGER,
    competition_level   TEXT NOT NULL DEFAULT '',
    teams_count         INTEGER,
    -- the roster size the club declares, which is also its nomination budget:
    -- inflating it to mint more nominations makes the inflation itself checkable
    registered_athletes INTEGER NOT NULL DEFAULT 0,
    roster_url          TEXT NOT NULL DEFAULT '',
    proof_kind          TEXT NOT NULL DEFAULT 'none'
                        CHECK (proof_kind IN ('none','roster','results','licence')),
    proof_status        TEXT NOT NULL DEFAULT 'unverified'
                        CHECK (proof_status IN ('unverified','pending','verified','rejected')),
    legitimacy          REAL,
    decision            TEXT NOT NULL DEFAULT 'pending'
                        CHECK (decision IN ('pending','verified','review','rejected')),
    policy_version      TEXT NOT NULL DEFAULT '',
    submitted_at        TEXT NOT NULL,
    decided_at          TEXT
);
CREATE INDEX IF NOT EXISTS idx_club_applications_decision ON club_applications(decision);

CREATE TABLE IF NOT EXISTS club_packages (
    id           INTEGER PRIMARY KEY,
    club_id      INTEGER NOT NULL REFERENCES clubs(id),
    athlete_id   INTEGER REFERENCES athlete_profiles(id),  -- set when package_type='player_direct'
    name         TEXT NOT NULL,
    description  TEXT NOT NULL DEFAULT '',
    package_type TEXT NOT NULL CHECK (package_type IN ('club','player_direct')),
    price_eur    INTEGER NOT NULL,
    perks        TEXT NOT NULL DEFAULT '[]',
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_packages_club ON club_packages(club_id, status);

CREATE TABLE IF NOT EXISTS package_commitments (
    id           INTEGER PRIMARY KEY,
    package_id   INTEGER NOT NULL REFERENCES club_packages(id),
    org_id       INTEGER NOT NULL REFERENCES sponsor_orgs(id),
    amount_eur   INTEGER NOT NULL,
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
    ("campaigns", "require_verified_athletes", "BOOLEAN NOT NULL DEFAULT FALSE"),
)


# Columns renamed after they had shipped. Same reasoning as the list above and
# the same trap: CREATE TABLE IF NOT EXISTS writes the new name only on a
# database that does not have the table yet, so an existing one keeps the old
# column and every query against the new name fails. Renames are listed rather
# than done by hand because the money columns moved from USD to EUR in one pass
# and a half-migrated database is worse than either currency.
# The old names are assembled rather than written out, because the search and
# replace that performed this migration rewrote this very table on its first
# run and left six no-op renames behind. A list of dead identifiers is exactly
# what a global rename cannot see.
_RENAMED_COLUMNS: tuple[tuple[str, str, str], ...] = tuple(
    (table, new.replace("eur", "usd"), new) for table, new in (
        ("deals", "amount_eur"),
        ("athlete_profiles", "base_rate_eur"),
        ("campaigns", "budget_eur_min"),
        ("campaigns", "budget_eur_max"),
        ("club_packages", "price_eur"),
        ("package_commitments", "amount_eur"),
    )
)


def lock_for_update(conn, table: str, key_column: str, key) -> None:
    """Serialise a check-then-act sequence on one row, on either backend.

    Counting rows and then inserting one is only correct if nothing else does
    the same thing in between. On Postgres that means holding a row lock for the
    rest of the transaction; on SQLite it means starting the write transaction
    *before* the count, because two connections can otherwise both read the old
    total and then write in turn, each believing it was under the limit.

    SQLite's lock is database-wide rather than per row, which is heavier than it
    needs to be and entirely acceptable: this is a rare, human-paced write.
    """
    if settings.db_backend == "postgres":
        conn.execute(f"SELECT 1 FROM {table} WHERE {key_column} = ? FOR UPDATE", (key,))
    elif not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")


def _columns(conn, table: str) -> set[str]:
    if settings.db_backend == "postgres":
        return {r["column_name"] for r in rows(
            conn, "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
            (table,))}
    return {c["name"] for c in rows(conn, f"PRAGMA table_info({table})")}


def _migrate(conn, statement: str, table: str, wanted: str) -> None:
    """Run one schema statement, tolerating a replica that got there first.

    Both checks below are check-then-act, and two API processes starting
    together both read the schema before either has changed it — so both decide
    the migration is needed and the loser crashes on boot. What matters is the
    end state, not which process produced it: if the column is there afterwards,
    the migration succeeded regardless of who ran it.

    The savepoint is what makes that recoverable on Postgres, where a failed
    statement poisons the whole transaction: without it the re-check below would
    itself fail with "current transaction is aborted", and the fix would only
    have worked on the backend that did not need it. Rolling back to the
    savepoint discards the failed statement and nothing else, so the migrations
    that already succeeded in this transaction survive.
    """
    postgres = settings.db_backend == "postgres"
    if postgres:
        conn.execute("SAVEPOINT stride_migrate")
    try:
        conn.execute(statement)
    except Exception:
        if postgres:
            conn.execute("ROLLBACK TO SAVEPOINT stride_migrate")
        if wanted not in _columns(conn, table):
            raise          # a real failure, not a race we already won
    else:
        if postgres:
            conn.execute("RELEASE SAVEPOINT stride_migrate")


def _rename_columns(conn) -> None:
    """Idempotent: only fires where the old name is still there and the new one
    is not, so a fresh database and a re-run are both no-ops."""
    for table, old, new in _RENAMED_COLUMNS:
        present = _columns(conn, table)
        if old in present and new not in present:
            _migrate(conn, f"ALTER TABLE {table} RENAME COLUMN {old} TO {new}", table, new)


def _add_missing_columns(conn) -> None:
    if settings.db_backend == "postgres":
        for table, column, decl in _ADDED_COLUMNS:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {decl}")
        return
    # SQLite has no ADD COLUMN IF NOT EXISTS, so ask first — and ask again if the
    # statement fails, because another process may have added it in between.
    for table, column, decl in _ADDED_COLUMNS:
        if column not in _columns(conn, table):
            _migrate(conn, f"ALTER TABLE {table} ADD COLUMN {column} {decl}", table, column)


def init_db(conn) -> None:
    if settings.db_backend == "postgres":
        conn.executescript(_PG_SCHEMA.read_text(encoding="utf-8"))
    else:
        conn.executescript(CREATORLENS_SCHEMA)  # analytics tables + shared events audit log
        conn.executescript(STRIDE_SCHEMA)
    # rename before adding: both walk the same tables, and a rename that ran
    # second would find the new column already created empty beside the old one
    _rename_columns(conn)
    _add_missing_columns(conn)
    conn.commit()


def drop_all(conn) -> None:
    """Postgres-only teardown for `stride reset` (SQLite just deletes its file)."""
    conn.executescript("".join(f"DROP TABLE IF EXISTS {t} CASCADE;" for t in _ALL_TABLES))
    conn.commit()
