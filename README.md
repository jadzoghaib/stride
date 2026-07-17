# Stride — athlete monetization & sponsorship platform (first product draft)

Athletes connect platforms and own evidence-based marketability analytics. Sponsors
match campaign briefs against the athlete pool with fully decomposable scoring and run
the deal pipeline. Fans discover and follow. The analytics core is the **CreatorLens
engine** (built first in this project), vendored at `packages/creatorlens` and
integrated end-to-end — not reimplemented.

**First iteration uses simulated athletes and simulated platform data by design** —
through the production ingestion/scoring pipeline, so swapping to live APIs changes
one connector class per platform.

## Run it (two terminals)

```
# 1. API  (uv manages Python; seeds on first run)         http://127.0.0.1:8490
uv run stride serve

# 2. Web  (from apps/web; first time: npm install)         http://localhost:5173
npm run dev
```

Demo accounts — password `stride123`:
`athlete@demo.stride` · `sponsor@demo.stride` · `fan@demo.stride` · `admin@demo.stride`

## Layout

```
apps/web/                React 18 + Vite + TS + Tailwind — landing, auth, athlete
                         workspace, sponsor campaigns/matching/evidence/pipeline,
                         fan discovery/feed, public directory + profiles
apps/api/stride_api/     FastAPI — auth+RBAC, routers per bounded context,
                         matching engine, JSON logs + metrics + probes, chaos layer,
                         simulated seed
packages/creatorlens/    the analytics engine: connectors → ingestion → KPIs →
                         versioned marketability scoring (its own docs inside)
infra/                   Dockerfiles + compose, K8s manifests (probes, HPA, scrape
                         annotations), Supabase/Postgres migration with RLS policies
scripts/failure_drill.py chaos drill: latency / errors / db-down → observe → recover
docs/                    repo-analysis · product · architecture (+ architecture.html,
                         the visual blueprint) · design-system · build-plan · runbook ·
                         costs (staged infra/maintenance cost model + unit economics,
                         for the business plan)
```

## Verification status
- API battery: 48/48 checks (roles, RBAC boundaries, matching decomposition,
  campaign-specific audience fit, offer round-trips, registration, audit, chaos+recovery)
- Web: typecheck clean; sponsor + athlete + public flows exercised in-browser
- Failure drill: baseline 9ms → 414ms injected latency → 503 injection → readiness
  degradation → full recovery

## Containerized

```
docker compose -f infra/docker-compose.yml up --build   # web :8080, api :8490
kubectl apply -f infra/k8s/stride.yaml                  # probes, HPA, scrape annotations
```

See docs/build-plan.md for what comes next (Postgres/Supabase, live connectors,
claim flow, notifications).
