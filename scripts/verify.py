"""Run everything, in the right order, and say what held.

    python scripts/verify.py                              # the standard pass
    python scripts/verify.py --api http://127.0.0.1:8490  # explicit API base
    python scripts/verify.py --postgres <DSN>             # also run the suite on Postgres
    python scripts/verify.py --external                   # also reach cited URLs
    python scripts/verify.py --quick                      # skip build + drill + workbook

Nine checks live in this repository and each takes a different argument, needs
a different thing running, and prints a different shape of output. Running them
by hand means remembering all of that, and the order matters more than it
looks: the audits fire hundreds of requests, the API's rate limiter allows a
burst of 300 refilling at 5/s, and running them back to back drains it. That is
not hypothetical -- it left a drill dead half way with a 60% error rate still
injected, which is worse than not having run it.

So this script paces the API-dependent phases: after each one it waits for the
bucket to refill before starting the next. A phase that needs something which
is not running is reported as skipped, not failed, because "the API was down"
and "the product is broken" are different sentences.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

OK, FAIL, SKIP = "ok", "FAIL", "skip"


class Phase:
    def __init__(self, name: str, detail: str = ""):
        self.name, self.detail, self.status, self.seconds = name, detail, SKIP, 0.0


def api_healthy(base: str, timeout: float = 3) -> bool:
    try:
        with urllib.request.urlopen(f"{base}/healthz", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def wait_for_budget(base: str, need: int = 3, cap: int = 90) -> None:
    """Wait until the rate limiter will let a burst through again.

    Reads `need` consecutive unthrottled responses rather than sleeping a
    fixed time: the bucket refills at a known rate, but how much the previous
    phase spent is not knowable from here.
    """
    clean, waited = 0, 0
    while clean < need and waited < cap:
        try:
            with urllib.request.urlopen(f"{base}/api/athletes", timeout=5) as r:
                clean = clean + 1 if r.status == 200 else 0
        except urllib.error.HTTPError as e:
            clean = 0 if e.code == 429 else clean + 1
        except Exception:
            return
        if clean < need:
            time.sleep(2)
            waited += 2
    if waited:
        print(f"    (waited {waited}s for the rate limiter)")


def run(phase: Phase, cmd: list[str], cwd: Path = ROOT, env: dict | None = None,
        want: str | None = None) -> Phase:
    print(f"  {phase.name} ...", flush=True)
    started = time.perf_counter()
    full_env = {**os.environ, **(env or {})}
    proc = subprocess.run(cmd, cwd=cwd, env=full_env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    phase.seconds = time.perf_counter() - started
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = [l for l in out.splitlines() if l.strip()]
    phase.detail = tail[-1][:100] if tail else ""
    if want and want not in out:
        phase.status = FAIL
        phase.detail = f"expected {want!r} in the output; last line: {phase.detail}"
    else:
        phase.status = OK if proc.returncode == 0 else FAIL
    if phase.status == FAIL:
        print("\n".join(tail[-12:]))
    return phase


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://127.0.0.1:8490")
    ap.add_argument("--postgres", metavar="DSN", help="also run the API suite against this DSN")
    ap.add_argument("--external", action="store_true", help="also reach every cited URL")
    ap.add_argument("--quick", action="store_true", help="skip the build, the drill and the workbook")
    args = ap.parse_args()

    api = args.api.rstrip("/")
    up = api_healthy(api)
    phases: list[Phase] = []

    print(f"\nStride verification · API {api} {'is up' if up else 'is NOT running'}\n")

    # ── things that need nothing running ─────────────────────────────────────
    phases.append(run(Phase("pytest (sqlite)"), [PY, "-m", "pytest", "-q"], cwd=ROOT / "apps/api"))
    if args.postgres:
        phases.append(run(Phase("pytest (postgres)"), [PY, "-m", "pytest", "-q"],
                          cwd=ROOT / "apps/api",
                          env={"STRIDE_TEST_DATABASE_URL": args.postgres}))
    phases.append(run(Phase("design tokens"), [PY, "scripts/design_audit.py"]))
    if not args.quick:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        phases.append(run(Phase("tsc + vite build"), [npm, "run", "build"], cwd=ROOT / "apps/web"))

    # ── things that drive a running API, paced ───────────────────────────────
    api_phases = [
        (Phase("journey (product rules)"), [PY, "scripts/journey.py", api], "0 failed"),
        (Phase("permissions (role x route)"), [PY, "scripts/permissions.py", api], "every route refused"),
        (Phase("propagation (cross-role)"), [PY, "scripts/propagation.py", api], "0 failed"),
        (Phase("links"), [PY, "scripts/links.py", "--api", api]
         + (["--external"] if args.external else []), None),
    ]
    if not args.quick:
        api_phases += [
            (Phase("failure drill"), [PY, "scripts/failure_drill.py", api], "Drill complete"),
            (Phase("admission stress"), [PY, "scripts/admission_stress.py", api], None),
        ]
    for phase, cmd, want in api_phases:
        if not up:
            phase.detail = "API not running"
            phases.append(phase)
            continue
        wait_for_budget(api)
        phases.append(run(phase, cmd, want=want))

    # ── the business plan holds itself to its own model ──────────────────────
    phases.append(run(Phase("doc consistency"), [PY, "scripts/doc_consistency.py"]))
    if not args.quick:
        phases.append(run(Phase("workbook formulas"), [PY, "scripts/verify_workbook.py"]))

    print("\n" + "─" * 78)
    width = max(len(p.name) for p in phases)
    for p in phases:
        mark = {OK: "ok  ", FAIL: "FAIL", SKIP: "skip"}[p.status]
        print(f"  {mark} {p.name:<{width}}  {p.seconds:5.1f}s  {p.detail[:60]}")
    failed = [p for p in phases if p.status == FAIL]
    skipped = [p for p in phases if p.status == SKIP]
    print("─" * 78)
    print(f"  {len(phases) - len(failed) - len(skipped)} passed, {len(failed)} failed, "
          f"{len(skipped)} skipped, {sum(p.seconds for p in phases):.0f}s total")
    if skipped and not up:
        print(f"\n  Start the API to run the {len(skipped)} skipped checks:")
        print("    cd apps/api && python -m uvicorn stride_api.main:app --port 8490")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
