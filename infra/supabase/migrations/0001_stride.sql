-- Stride schema for Postgres/Supabase — the Phase-2 persistence target.
-- Mirrors apps/api/stride_api/db.py 1:1, plus row-level security policies
-- that encode the same RBAC the FastAPI layer enforces with require_role().
-- With Supabase Auth, `users` becomes a profile table keyed on auth.users(id)
-- and auth.uid() drives the policies below.

create table if not exists users (
    id            bigint generated always as identity primary key,
    auth_id       uuid unique,                          -- -> auth.users(id) on Supabase
    email         text not null unique,
    password_hash text,                                 -- null once Supabase Auth owns credentials
    role          text not null check (role in ('athlete','sponsor','fan','admin')),
    display_name  text not null,
    status        text not null default 'active' check (status in ('active','suspended')),
    created_at    timestamptz not null default now()
);

create table if not exists athlete_profiles (
    id                     bigint generated always as identity primary key,
    user_id                bigint unique references users(id),
    slug                   text not null unique,
    display_name           text not null,
    sport                  text not null,
    country                text not null,
    region                 text not null,
    bio                    text not null default '',
    career_highlights      jsonb not null default '[]',
    topics                 jsonb not null default '[]',
    deal_types             jsonb not null default '[]',
    base_rate_usd          integer not null default 1000,
    status                 text not null default 'listed' check (status in ('draft','listed','hidden')),
    creatorlens_creator_id bigint,
    created_at             timestamptz not null default now()
);
create index if not exists idx_athletes_sport on athlete_profiles(sport);

create table if not exists sponsor_orgs (
    id         bigint generated always as identity primary key,
    user_id    bigint not null unique references users(id),
    name       text not null,
    industry   text not null,
    regions    jsonb not null default '[]',
    website    text not null default '',
    created_at timestamptz not null default now()
);

create table if not exists campaigns (
    id                 bigint generated always as identity primary key,
    org_id             bigint not null references sponsor_orgs(id),
    name               text not null,
    objective          text not null default '',
    category           text not null,
    deal_types         jsonb not null default '[]',
    budget_usd_min     integer not null default 1000,
    budget_usd_max     integer not null default 10000,
    target_age_buckets jsonb not null default '[]',
    target_genders     jsonb not null default '[]',
    target_countries   jsonb not null default '[]',
    target_topics      jsonb not null default '[]',
    sponsor_target_id  bigint,
    status             text not null default 'active' check (status in ('draft','active','closed')),
    created_at         timestamptz not null default now()
);

create table if not exists deals (
    id           bigint generated always as identity primary key,
    campaign_id  bigint not null references campaigns(id),
    org_id       bigint not null references sponsor_orgs(id),
    athlete_id   bigint not null references athlete_profiles(id),
    deal_type    text not null,
    amount_usd   integer not null,
    message      text not null default '',
    status       text not null default 'offered'
                 check (status in ('offered','accepted','declined','withdrawn','completed')),
    created_at   timestamptz not null default now(),
    responded_at timestamptz
);
create index if not exists idx_deals_athlete on deals(athlete_id, status);
create index if not exists idx_deals_org on deals(org_id, status);

create table if not exists follows (
    id         bigint generated always as identity primary key,
    user_id    bigint not null references users(id),
    athlete_id bigint not null references athlete_profiles(id),
    created_at timestamptz not null default now(),
    unique (user_id, athlete_id)
);

-- ── Row-level security (Supabase pattern) ───────────────────────────────────
-- helper: current app user id from the Supabase JWT
create or replace function current_app_user_id() returns bigint
language sql stable as
$$ select id from users where auth_id = auth.uid() $$;

alter table athlete_profiles enable row level security;
alter table sponsor_orgs     enable row level security;
alter table campaigns        enable row level security;
alter table deals            enable row level security;
alter table follows          enable row level security;

-- listed athlete profiles are public; owners see and edit their own row
create policy athlete_public_read on athlete_profiles
  for select using (status = 'listed' or user_id = current_app_user_id());
create policy athlete_own_write on athlete_profiles
  for update using (user_id = current_app_user_id());

-- orgs and campaigns are private to their owner
create policy org_owner on sponsor_orgs
  for all using (user_id = current_app_user_id());
create policy campaign_owner on campaigns
  for all using (org_id in (select id from sponsor_orgs where user_id = current_app_user_id()));

-- a deal is visible to the sponsoring org and the offered athlete
create policy deal_parties on deals
  for select using (
    org_id in (select id from sponsor_orgs where user_id = current_app_user_id())
    or athlete_id in (select id from athlete_profiles where user_id = current_app_user_id()));
create policy deal_sponsor_insert on deals
  for insert with check (
    org_id in (select id from sponsor_orgs where user_id = current_app_user_id()));
create policy deal_parties_update on deals
  for update using (
    org_id in (select id from sponsor_orgs where user_id = current_app_user_id())
    or athlete_id in (select id from athlete_profiles where user_id = current_app_user_id()));

-- follows belong to the follower
create policy follows_owner on follows
  for all using (user_id = current_app_user_id());

-- CreatorLens analytics tables migrate with their own script (same shapes as
-- packages/creatorlens/creatorlens/db.py); athlete-owned accounts follow the
-- athlete_profiles ownership chain.
