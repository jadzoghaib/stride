# Stride — Build Plan & Phasing

## Phase 1 — this draft (BUILT and verified)
- Auth (register/login/logout, 3 roles + admin), JWT cookie sessions, RBAC on every route
- Athlete: workspace dashboard (marketability + evidence, platforms, audience),
  profile editor with visibility control, deal inbox with accept/decline
- Sponsor: org workspace, campaign briefs (→ CreatorLens targets), explainable
  matching, full analytics evidence per athlete, offers + pipeline with withdraw
- Fan: explained discovery, follows, following feed with score trajectories
- Public: landing, directory with facets, public athlete profiles
- Analytics: CreatorLens engine integrated end-to-end (connect → sync → score)
- Simulated data: 24 athletes / 42 synced accounts / 3 orgs / 3 campaigns / deals
  in every lifecycle state / demo accounts (stride123)
- Ops: JSON logs, request IDs, Prometheus /metrics, /healthz + /readyz, audit log,
  chaos layer + failure drill, Dockerfiles + compose, K8s manifests, Supabase
  migration with RLS

## Phase 2 — productionize the platform (build next, in order)
1. Postgres migration (run infra/supabase/migrations; swap connection layer)
2. Supabase Auth adoption (email verification, password reset, refresh tokens);
   RLS policies already written
3. Live Instagram connector first (best documented), then YouTube, then TikTok —
   one class each behind the existing interface; encrypted token storage
4. Athlete claim flow (verify + claim an unclaimed seeded/imported profile)
5. Deal lifecycle completion: mark-complete + deliverables checklist; notifications
   (email on offer/response)

## Phase 3 — depth
Messaging thread per deal; campaign shortlists and saved searches; match-snapshot
persistence (recommendation provenance over time); athlete content posts + fan feed
upgrade; org teams (multi-user sponsors); public score-trend pages.

## Phase 4 — scale & intelligence
Metrics store (Timescale/ClickHouse) when volume hurts; learned matching layer
(predicted campaign lift) trained on deal outcomes — the current transparent formula
remains the explainable baseline; payments/escrow; OpenTelemetry tracing;
multi-region read replicas.

## Assumptions made (flag if wrong)
- One role per account is acceptable for v0.1.
- Dark-only UI is acceptable for v0.1 (light theme is a token swap later).
- Simulated athletes may be fictional names (no real-person likenesses).
- English-only UI for now; USD-only rates.
- The 8 matching weights are a sane starting point — they are constants in
  matching.py, expected to be tuned (and eventually learned) against outcomes.
