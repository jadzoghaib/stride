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
    base_rate_eur          integer not null default 1000,
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
    budget_eur_min     integer not null default 1000,
    budget_eur_max     integer not null default 10000,
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
    amount_eur   integer not null,
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

-- ── Upgrades for databases created before the changes below ─────────────────
-- `create table if not exists` above is a no-op against a database that already
-- has the table, so nothing above this line reaches an existing Supabase
-- project. Everything here is written to be idempotent and safe to re-run: it
-- is the same rename-then-add sequence apps/api/stride_api/db.py performs on
-- start-up, kept in step with it by hand because Supabase applies this file
-- rather than importing that module.
--
-- Table SHAPES are owned by apps/api/stride_api/schema_pg.sql. What lives here
-- is the upgrade path and the row-level security that goes with it.

-- money moved from USD to EUR
do $$
declare
  r record;
begin
  for r in
    select * from (values
      ('deals','amount_usd','amount_eur'),
      ('athlete_profiles','base_rate_usd','base_rate_eur'),
      ('campaigns','budget_usd_min','budget_eur_min'),
      ('campaigns','budget_usd_max','budget_eur_max'),
      ('club_packages','price_usd','price_eur'),
      ('package_commitments','amount_usd','amount_eur')
    ) as t(tbl, old_col, new_col)
  loop
    if exists (select 1 from information_schema.columns
                where table_name = r.tbl and column_name = r.old_col)
       and not exists (select 1 from information_schema.columns
                        where table_name = r.tbl and column_name = r.new_col)
    then
      execute format('alter table %I rename column %I to %I', r.tbl, r.old_col, r.new_col);
    end if;
  end loop;
end $$;

-- columns added to tables that had already shipped
alter table deals     add column if not exists completed_at              text;
alter table deals     add column if not exists projected_reach           integer;
alter table campaigns add column if not exists require_verified_athletes boolean not null default false;

-- Row-level security for the tables added since this file was written.
--
-- Wrapped in a guard because `alter table if exists` protects the enable but
-- NOT the policy statements below it: `drop policy if exists x on missing_table`
-- raises rather than skipping, so on a database that predates these tables the
-- whole migration failed at this point instead of no-opping past it.
--
-- The policies are `for select` only, deliberately. An applicant owning their
-- row does not mean they may write every column of it: `decision`,
-- `proof_status`, `credibility` and `admitted_via` are the reviewer's, and a
-- `for all` policy handed the applicant UPDATE and DELETE on all of them —
-- self-admission, one statement long, the moment the app connects per-user
-- rather than through the service role. Writes stay server-mediated, where the
-- admission policy can actually be applied.
do $$
begin
  if to_regclass('public.athlete_applications') is not null then
    alter table athlete_applications enable row level security;
    drop policy if exists application_owner on athlete_applications;
    drop policy if exists application_owner_read on athlete_applications;
    create policy application_owner_read on athlete_applications
      for select using (athlete_id in (select id from athlete_profiles
                                        where user_id = current_app_user_id()));
  end if;

  if to_regclass('public.club_applications') is not null then
    alter table club_applications enable row level security;
    drop policy if exists club_application_owner on club_applications;
    drop policy if exists club_application_owner_read on club_applications;
    create policy club_application_owner_read on club_applications
      for select using (club_id in (select id from clubs
                                     where user_id = current_app_user_id()));
  end if;

  if to_regclass('public.deal_deliverables') is not null then
    alter table deal_deliverables enable row level security;
    drop policy if exists deliverable_parties on deal_deliverables;
    create policy deliverable_parties on deal_deliverables
      for select using (
        deal_id in (
          select d.id from deals d
          where d.org_id in (select id from sponsor_orgs
                              where user_id = current_app_user_id())
             or d.athlete_id in (select id from athlete_profiles
                                  where user_id = current_app_user_id())
        )
      );
  end if;
end $$;
