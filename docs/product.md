# Stride — Product Definition (v0.1)

Athlete monetization and sponsorship platform. Three account types, one shared
source of truth: evidence-based marketability analytics (the CreatorLens engine).

## User types
| Role | Who | Core value |
|---|---|---|
| Athlete | any athlete/creator, not just Olympians | own your analytics, publish a rate card, receive and manage offers |
| Sponsor | brand / agency org | find the right athletes for a specific campaign with explainable matching; run the deal pipeline |
| Fan (user) | supporter | discover and follow athletes, watch their trajectory |
| Admin | platform operator | audit log, chaos/resilience controls |

## Core workflows

**Athlete flow**: register (role: athlete) → draft profile created + analytics identity
provisioned → complete profile (sport, bio, highlights, topics, deal formats, rate)
→ connect platforms (mock connectors this iteration) → sync → marketability dimensions
+ audience demographics appear → set status to `listed` → appear in matching →
receive offers → accept/decline → earnings tracked.

**Sponsor flow**: register (role: sponsor) → org created → create campaign brief
(category, formats, budget range, target ages/genders/countries/themes) → brief becomes
a CreatorLens sponsor target → run matching → ranked athletes, each with component
breakdown, reasons, caveats, coverage → inspect full analytics evidence (per-platform
KPIs, audience vs target, recent posts) → send offer → track pipeline
(offered/accepted/declined/withdrawn/completed) → withdraw open offers.

**User flow**: register (role: fan) → pick interests → explained discovery ranking →
follow athletes → following feed with score trajectory sparklines → public athlete
profiles (marketability summary + audience, no commercial internals).

**Matching flow** (sponsor side, the core): campaign target → per athlete: CreatorLens
`compute_scores` live against that target (audience fit, engagement quality, scale,
growth, consistency) + commercial components (budget alignment vs rate card, deal-format
overlap, category-topic affinity) → weighted sum → ranked list where every score
decomposes and partial analytics coverage is labeled, never hidden.

**Analytics flow**: connect platform → ingestion pipeline (validated, retried,
idempotent, audited SyncRuns) → normalized metrics (posts, snapshots, demographics with
provenance) → versioned scoring formulas → score snapshots carrying inputs + coverage →
rendered identically to athlete (own dashboard) and sponsor (evidence view).

**Onboarding flow**: role chosen at registration; role-specific fields inline
(athlete: sport/country; sponsor: org/industry); athlete lands on dashboard with
clear next actions (connect platforms, complete profile, go listed).

## Authentication & account model
Email + password (PBKDF2) → JWT in an httpOnly cookie. One role per account (v0.1;
multi-role is a later concern). RBAC enforced per route (`require_role`), mirrored by
Postgres RLS policies for the Supabase path (infra/supabase/migrations). Sessions are
stateless; every auth event lands in the audit log.

## Non-goals in v0.1 (deliberate)
Real athlete data, live platform OAuth, payments/escrow, messaging threads, content
posts, multi-user orgs, mobile layout polish. See build-plan.md.
