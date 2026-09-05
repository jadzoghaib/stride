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


def control(method, path, body=None, tries=8):
    """A chaos *control* call, as opposed to a probe.

    Probes are allowed to fail -- that is what we are observing. Controls are
    not: a control that quietly fails leaves the API sabotaged after the drill
    has printed "recovery verified", which is exactly what happened once.

    But refusals are not all alike. 429 is the rate limiter, and it is
    *transient*: the drill fires ~25 requests, and running it straight after
    the other audits (journey, permissions, propagation, links) starts it with
    an empty bucket. Asserting on that turned a pacing problem into a drill
    that died half way and left a 60% error rate injected -- the same failure
    the assert was added to prevent, through a different door. So a 429 waits
    for the bucket to refill and tries again; anything else is a real refusal
    and ends the drill.
    """
    for attempt in range(tries):
        status, body_out = call(method, path, body)
        if status == 200:
            return body_out
        if status != 429:
            break
        wait = 2 * (attempt + 1)          # the bucket refills at 5/s
        print(f"  (rate limited on {method} {path}; waiting {wait}s)")
        time.sleep(wait)
    raise AssertionError(f"{method} {path} -> {status}: a refused control ends the drill")


def reset_and_verify(tries=12):
    """Reset, then read the state back. `tries` is generous because this also
    runs from the `finally`: an exception raised *here* would leave the failure
    injected, so recovery gets more patience than anything else."""
    control("POST", "/api/admin/chaos/reset", tries=tries)
    state = control("GET", "/api/admin/chaos", tries=tries)
    clean = not state["latency_ms"] and not state["error_rate"] and not state["db_down"]
    assert clean, f"chaos did not reset: {state}"
    return state


def probe(path="/api/athletes", n=6):
    codes, t0 = [], time.perf_counter()
    for _ in range(n):
        codes.append(call("GET", path)[0])
    avg_ms = (time.perf_counter() - t0) / n * 1000
    return codes, avg_ms


print("Signing in as admin...")
status, _ = call("POST", "/api/auth/login", {"email": "admin@demo.stride", "password": "stride123"})
assert status == 200, "admin login failed - is the API running with seeded data?"

# Whatever happens below, the API is handed back clean. The one thing a drill
# must never do is leave the failure it injected running after it exits.
try:
    reset_and_verify()          # a previous run may have died mid-drill
    print("\n[baseline]")
    codes, ms = probe()
    print(f"  {codes} avg {ms:.0f}ms")

    print("\n[drill 1] inject 400ms latency")
    control("POST", "/api/admin/chaos", {"latency_ms": 400})
    codes, ms = probe(n=3)
    print(f"  {codes} avg {ms:.0f}ms  <- latency visible; check /metrics histogram")

    print("\n[drill 2] inject 60% error rate")
    control("POST", "/api/admin/chaos", {"error_rate": 0.6})
    codes, _ = probe(n=8)
    print(f"  {codes}  <- 503s from the chaos layer; stride_chaos_injected_total increments")
    assert 503 in codes, "no 503 in 8 requests at a 60% error rate -- chaos is not injecting"

    print("\n[drill 3] database down")
    control("POST", "/api/admin/chaos", {"db_down": True})
    status, _ = call("GET", "/readyz")
    print(f"  /readyz -> {status}  <- readiness fails; Kubernetes stops routing to this pod")
    assert status == 503, f"/readyz should fail while db_down, got {status}"
finally:
    print("\n[recover] reset chaos")
    state = reset_and_verify()
    status_r, _ = call("GET", "/readyz")
    codes, ms = probe(n=4)
    print(f"  /readyz -> {status_r}; requests {codes} avg {ms:.0f}ms; state {state}")
    # Recovery means the chaos layer is off. `state` above proves that by
    # reading it back, and no probe should now carry the 503 chaos injects.
    # A 429 is not a recovery failure -- it is the rate limiter doing its job
    # on a bucket this drill has just spent, and asserting `all(c == 200)`
    # failed the drill for the one reason that has nothing to do with what it
    # measures.
    assert status_r == 200, f"/readyz should be healthy after reset, got {status_r}"
    assert 503 not in codes, f"chaos still failing requests after reset: {codes}"

print("\nDrill complete: failure observed through probes + metrics, recovery verified by reading the state back.")
