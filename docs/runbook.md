# Stride — Ops Runbook (first draft)

## Endpoints
- `/healthz` — liveness (process up). K8s restarts the pod on failure.
- `/readyz`  — readiness (DB reachable). K8s stops routing on failure.
- `/metrics` — Prometheus text format: `stride_http_requests_total`,
  `stride_http_request_duration_seconds` histogram, `stride_chaos_injected_total`.

## Logs
One JSON line per request on stdout:
`{"ts","level","message":"request","request_id","method","path","status","duration_ms"}`
Correlate any incident by `request_id` (also returned to clients as the
`x-request-id` response header; inbound `X-Request-ID` is honored).

## Failure drill (run it after any infra change)
```
uv run stride serve            # terminal 1
uv run python scripts/failure_drill.py   # terminal 2
```
Expected: baseline single-digit ms → +400ms under latency injection → ~60% 503s under
error injection (chaos counter increments) → /readyz 503 under db_down → reset →
healthy. Verified output lives in the repo history of this doc.

Chaos is admin-only and disabled outside dev (`STRIDE_CHAOS=0` in prod manifests).

## Common incidents
| Symptom | First checks | Likely cause / fix |
|---|---|---|
| 503s spike | `stride_chaos_injected_total` (drill left on?), then error-rate by route in requests_total | chaos not reset → POST /api/admin/chaos/reset |
| /readyz failing | DB file/volume mounted? disk full? | restore volume; pod restart is safe (stateless app) |
| Latency p95 up | duration histogram by route; sync endpoints are the heavy ones | move syncs to a worker (Phase 2+) |
| Auth failures cluster | user.logged_in audit events vs 401 count | token TTL expiry wave or secret rotated without redeploy |
| A score looks wrong | the score's `inputs_json` + `coverage_json` carry the full evidence; audit log has the computing event | recompute after re-sync; check formula_version |

## Backup / restore (draft)
SQLite: copy `data/stride.db` (single file) while the API is stopped, or use
`.backup` via sqlite3 CLI live. Postgres phase: standard pg_dump + PITR.
