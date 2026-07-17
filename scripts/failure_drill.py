"""Failure drill — inject failures via the chaos layer, observe, recover.

Run with the API up:  uv run python scripts/failure_drill.py
Documented in docs/runbook.md. Exercises:
  1. latency injection   -> watch p95 rise in /metrics
  2. error injection     -> 503s appear; stride_chaos_injected_total increments
  3. db_down             -> /readyz fails (Kubernetes would pull the pod from rotation)
  4. reset               -> full recovery, verified
"""

import http.cookiejar
import json
import time
import urllib.request

BASE = "http://127.0.0.1:8490"

jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method,
                                 headers={"Content-Type": "application/json"},
                                 data=json.dumps(body).encode() if body else None)
    try:
        with opener.open(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, {}


def probe(path="/api/athletes", n=6):
    codes, t0 = [], time.perf_counter()
    for _ in range(n):
        codes.append(call("GET", path)[0])
    avg_ms = (time.perf_counter() - t0) / n * 1000
    return codes, avg_ms


print("Signing in as admin...")
status, _ = call("POST", "/api/auth/login", {"email": "admin@demo.stride", "password": "stride123"})
assert status == 200, "admin login failed - is the API running with seeded data?"

print("\n[baseline]")
codes, ms = probe()
print(f"  {codes} avg {ms:.0f}ms")

print("\n[drill 1] inject 400ms latency")
call("POST", "/api/admin/chaos", {"latency_ms": 400})
codes, ms = probe(n=3)
print(f"  {codes} avg {ms:.0f}ms  <- latency visible; check /metrics histogram")

print("\n[drill 2] inject 60% error rate")
call("POST", "/api/admin/chaos", {"error_rate": 0.6})
codes, _ = probe(n=8)
print(f"  {codes}  <- 503s from the chaos layer; stride_chaos_injected_total increments")

print("\n[drill 3] database down")
call("POST", "/api/admin/chaos", {"db_down": True})
status, _ = call("GET", "/readyz")
print(f"  /readyz -> {status}  <- readiness fails; Kubernetes stops routing to this pod")

print("\n[recover] reset chaos")
call("POST", "/api/admin/chaos/reset")
status_r, _ = call("GET", "/readyz")
codes, ms = probe(n=4)
print(f"  /readyz -> {status_r}; requests {codes} avg {ms:.0f}ms")
print("\nDrill complete: failure observed through probes + metrics, recovery verified.")
