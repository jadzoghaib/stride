-- Stride — Postgres schema (analytics + product), the runtime target for STRIDE_DATABASE_URL.
-- Behaviourally identical to the SQLite schema: dates/timestamps and JSON payloads are
-- TEXT (the app serialises them as ISO strings / json.dumps), so reads round-trip unchanged.
-- Tables are ordered by dependency (Postgres enforces FK targets at creation time).
-- Idempotent: safe to re-run. Applied automatically by init_db, or paste into the
-- Supabase SQL editor. RLS policies live in infra/supabase/migrations/0001_stride.sql
-- (only meaningful when the app connects per-user; the service connection bypasses them).

-- ── CreatorLens analytics tables ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS creators (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    handle        TEXT NOT NULL UNIQUE,
    display_name  TEXT NOT NULL,
    primary_topic TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_accounts (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    creator_id        BIGINT NOT NULL REFERENCES creators(id),
    platform          TEXT NOT NULL CHECK (platform IN ('instagram','youtube','tiktok')),
    handle            TEXT NOT NULL,
    external_id       TEXT NOT NULL,
    connection_status TEXT NOT NULL CHECK (connection_status IN ('connected','disconnected','error')),
    source            TEXT NOT NULL DEFAULT 'mock' CHECK (source IN ('mock','live')),
    connected_at      TEXT NOT NULL,
    last_synced_at    TEXT,
    UNIQUE (creator_id, platform)
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id        BIGINT NOT NULL REFERENCES platform_accounts(id),
    trigger_kind      TEXT NOT NULL CHECK (trigger_kind IN ('seed','manual','scheduled')),
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    status            TEXT NOT NULL CHECK (status IN ('running','succeeded','partial','failed')),
    posts_fetched     INTEGER NOT NULL DEFAULT 0,
    metrics_written   INTEGER NOT NULL DEFAULT 0,
    snapshots_written INTEGER NOT NULL DEFAULT 0,
    error             TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id   BIGINT NOT NULL REFERENCES platform_accounts(id),
    external_id  TEXT NOT NULL,
    content_type TEXT NOT NULL,
    title        TEXT NOT NULL,
    published_at TEXT NOT NULL,
    permalink    TEXT NOT NULL,
    UNIQUE (account_id, external_id)
);

CREATE TABLE IF NOT EXISTS post_metrics (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    post_id             BIGINT NOT NULL REFERENCES posts(id),
    sync_run_id         BIGINT NOT NULL REFERENCES sync_runs(id),
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
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id    BIGINT NOT NULL REFERENCES platform_accounts(id),
    sync_run_id   BIGINT NOT NULL REFERENCES sync_runs(id),
    snapshot_date TEXT NOT NULL,
    followers     INTEGER NOT NULL,
    profile_views INTEGER NOT NULL DEFAULT 0,
    UNIQUE (account_id, snapshot_date)
);

CREATE TABLE IF NOT EXISTS audience_demographics (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id  BIGINT NOT NULL REFERENCES platform_accounts(id),
    sync_run_id BIGINT NOT NULL REFERENCES sync_runs(id),
    captured_at TEXT NOT NULL,
    dimension   TEXT NOT NULL CHECK (dimension IN ('age','gender','country')),
    bucket      TEXT NOT NULL,
    share       REAL NOT NULL CHECK (share >= 0 AND share <= 1)
);
CREATE INDEX IF NOT EXISTS idx_demographics_account ON audience_demographics(account_id, sync_run_id);

CREATE TABLE IF NOT EXISTS sponsor_targets (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    age_buckets TEXT NOT NULL,
    genders     TEXT NOT NULL,
    countries   TEXT NOT NULL,
    topics      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS score_snapshots (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    creator_id         BIGINT NOT NULL REFERENCES creators(id),
    sponsor_target_id  BIGINT REFERENCES sponsor_targets(id),
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
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts          TEXT NOT NULL,
    actor       TEXT NOT NULL CHECK (actor IN ('user','system')),
    event_type  TEXT NOT NULL,
    object_type TEXT,
    object_id   BIGINT,
    detail_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

-- ── Stride product tables ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('athlete','sponsor','fan','club','admin')),
    display_name  TEXT NOT NULL,
    auth_id       TEXT UNIQUE,
    token_version INTEGER NOT NULL DEFAULT 1,
    status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','suspended')),
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS athlete_profiles (
    id                      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id                 BIGINT UNIQUE REFERENCES users(id),
    slug                    TEXT NOT NULL UNIQUE,
    display_name            TEXT NOT NULL,
    sport                   TEXT NOT NULL,
    country                 TEXT NOT NULL,
    region                  TEXT NOT NULL,
    bio                     TEXT NOT NULL DEFAULT '',
    career_highlights       TEXT NOT NULL DEFAULT '[]',
    topics                  TEXT NOT NULL DEFAULT '[]',
    deal_types              TEXT NOT NULL DEFAULT '[]',
    base_rate_eur           INTEGER NOT NULL DEFAULT 1000,
    status                  TEXT NOT NULL DEFAULT 'listed' CHECK (status IN ('draft','listed','hidden')),
    creatorlens_creator_id  BIGINT,
    created_at              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_athletes_sport ON athlete_profiles(sport);

CREATE TABLE IF NOT EXISTS sponsor_orgs (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT NOT NULL UNIQUE REFERENCES users(id),
    name        TEXT NOT NULL,
    industry    TEXT NOT NULL,
    regions     TEXT NOT NULL DEFAULT '[]',
    website     TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    org_id             BIGINT NOT NULL REFERENCES sponsor_orgs(id),
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
    sponsor_target_id  BIGINT,
    -- a hard retrieval filter, not a weighted term: see matching.candidates()
    require_verified_athletes BOOLEAN NOT NULL DEFAULT FALSE,
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('draft','active','closed')),
    created_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_campaigns_org ON campaigns(org_id);

CREATE TABLE IF NOT EXISTS deals (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id  BIGINT NOT NULL REFERENCES campaigns(id),
    org_id       BIGINT NOT NULL REFERENCES sponsor_orgs(id),
    athlete_id   BIGINT NOT NULL REFERENCES athlete_profiles(id),
    deal_type    TEXT NOT NULL,
    amount_eur   INTEGER NOT NULL,
    message      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'offered'
                 CHECK (status IN ('offered','accepted','declined','withdrawn','completed')),
    created_at   TEXT NOT NULL,
    responded_at TEXT,
    completed_at TEXT,
    projected_reach INTEGER
);

CREATE TABLE IF NOT EXISTS deal_deliverables (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deal_id  BIGINT NOT NULL REFERENCES deals(id),
    post_id  BIGINT NOT NULL REFERENCES posts(id),
    added_at TEXT NOT NULL,
    UNIQUE (deal_id, post_id)
);
CREATE INDEX IF NOT EXISTS idx_deals_athlete ON deals(athlete_id, status);
CREATE INDEX IF NOT EXISTS idx_deals_org ON deals(org_id, status);

CREATE TABLE IF NOT EXISTS follows (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id),
    athlete_id BIGINT NOT NULL REFERENCES athlete_profiles(id),
    created_at TEXT NOT NULL,
    UNIQUE (user_id, athlete_id)
);

CREATE TABLE IF NOT EXISTS clubs (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id    BIGINT UNIQUE REFERENCES users(id),
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
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    club_id    BIGINT NOT NULL REFERENCES clubs(id),
    athlete_id BIGINT NOT NULL REFERENCES athlete_profiles(id),
    position   TEXT NOT NULL DEFAULT '',
    status     TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','former')),
    joined_at  TEXT NOT NULL,
    UNIQUE (club_id, athlete_id)
);

-- Admission. Applications are stored whole so a decision is reproducible from
-- the row that produced it, with `policy_version` naming the rules in force.
CREATE TABLE IF NOT EXISTS athlete_applications (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    athlete_id        BIGINT NOT NULL UNIQUE REFERENCES athlete_profiles(id),
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
    nominated_by_club BIGINT REFERENCES clubs(id),
    credibility       DOUBLE PRECISION,
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
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    club_id             BIGINT NOT NULL UNIQUE REFERENCES clubs(id),
    legal_name          TEXT NOT NULL DEFAULT '',
    registration_id     TEXT NOT NULL DEFAULT '',
    federation_name     TEXT NOT NULL DEFAULT '',
    federation_id       TEXT NOT NULL DEFAULT '',
    founded_year        INTEGER,
    competition_level   TEXT NOT NULL DEFAULT '',
    teams_count         INTEGER,
    -- the roster size the club declares, which is also its nomination budget:
    -- inflating it to mint nominations makes the inflation itself checkable
    registered_athletes INTEGER NOT NULL DEFAULT 0,
    roster_url          TEXT NOT NULL DEFAULT '',
    proof_kind          TEXT NOT NULL DEFAULT 'none'
                        CHECK (proof_kind IN ('none','roster','results','licence')),
    proof_status        TEXT NOT NULL DEFAULT 'unverified'
                        CHECK (proof_status IN ('unverified','pending','verified','rejected')),
    legitimacy          DOUBLE PRECISION,
    decision            TEXT NOT NULL DEFAULT 'pending'
                        CHECK (decision IN ('pending','verified','review','rejected')),
    policy_version      TEXT NOT NULL DEFAULT '',
    submitted_at        TEXT NOT NULL,
    decided_at          TEXT
);

CREATE TABLE IF NOT EXISTS club_packages (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    club_id      BIGINT NOT NULL REFERENCES clubs(id),
    athlete_id   BIGINT REFERENCES athlete_profiles(id),
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
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    package_id   BIGINT NOT NULL REFERENCES club_packages(id),
    org_id       BIGINT NOT NULL REFERENCES sponsor_orgs(id),
    amount_eur   INTEGER NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled')),
    created_at   TEXT NOT NULL,
    cancelled_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_commitments_org ON package_commitments(org_id, status);
