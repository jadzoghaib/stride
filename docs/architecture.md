# Stride — System Architecture (v0.1)

Opinionated first draft: boring, portable, observable. Every choice below names
its production successor.

## Shape

```
apps/web   React 18 + Vite + TS + Tailwind SPA (nginx in prod, /api proxied)
apps/api   FastAPI — auth, RBAC, athletes, sponsors, campaigns, deals, discovery,
           admin/chaos; JSON logs, request IDs, /metrics, /healthz, /readyz
packages/creatorlens   the analytics engine (built first, vendored as a workspace
           package): connectors -> ingestion -> KPIs -> versioned scoring
SQLite     one file, both Stride product tables and CreatorLens analytics tables;
           every CreatorLens function takes an explicit connection -> shared
           transaction boundary today, separate service later if needed
```

## Decisions and their successors

| Decision (now) | Why | Successor (when) |
|---|---|---|
| SQLite | zero-install, one-file draft; schema written portable | Postgres via infra/supabase/migrations (Phase 2, or when >1 API replica) |
| Own JWT auth | full account flows today without external accounts | Supabase Auth; users table already mirrors the profile-on-auth.users pattern, RLS policies written |
| Mock platform connectors | first iteration mandate: simulated data | live IG/YouTube/TikTok connectors behind the same 3-method interface (creatorlens docs/real-api-mapping.md) |
| Matching computed on request | 24 athletes -> milliseconds; always fresh | persisted match snapshots + nightly batch when the pool grows |
| Monolith API | one bounded deployable; routers are already bounded contexts | split ingestion/scoring into a worker when sync volume demands it |
| Hand-rolled metrics | zero deps, scrape-ready | prometheus-client / OpenTelemetry drop into the same middleware |

## Postgres vs NoSQL
Relational core (users, profiles, campaigns, deals) is unambiguously relational —
Postgres. The NoSQL-shaped data (metric captures, audit events, score snapshots with
JSON evidence) is append-only document-ish; it lives comfortably in Postgres JSONB at
this scale. A dedicated store (ClickHouse/Timescale for metrics) is a Phase-4 concern,
adopted only when metric volume hurts — not before.

## Observability (three pillars)
- **Logs**: one JSON line per request (method, path, status, duration_ms, request_id),
  machine-parseable; app events via the same formatter; audit events in the DB.
- **Metrics**: /metrics in Prometheus text format — request counts by route/status,
  latency histogram, chaos-injection counter. K8s manifests carry scrape annotations.
- **Traces**: request_id issued/propagated by middleware (accepts inbound
  X-Request-ID); the correlation key across logs today, OpenTelemetry spans later.

## Reliability & scaling
- Liveness (/healthz) vs readiness (/readyz, checks DB) separated; K8s probes wired.
- Ingestion: per-call retries with stepped delays, per-account failure isolation,
  idempotent upserts (safe redelivery/replay).
- HPA on the API (CPU 70%); web is stateless nginx. SQLite caps API at 1 writer
  replica — the manifest says so explicitly; Postgres removes the cap.
- Failure simulation: chaos layer (latency / error-rate / db_down) + scripts/failure_drill.py;
  drill output proves probe behavior and recovery (docs/runbook.md).

## Tradeoffs accepted
- SQLite single-writer vs. zero-ops draft: accepted, migration path written.
- Session revocation requires token expiry (stateless JWT): accepted for 72h TTL;
  Supabase Auth brings refresh/revoke.
- Matching recompute cost grows linearly with athlete pool: fine to ~10³ athletes,
  then batch + cache.
- Mock connectors mean analytics are simulated end-to-end — but through the real
  pipeline, so the swap to live APIs changes one class per platform, nothing downstream.
