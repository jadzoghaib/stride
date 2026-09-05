"""Does every link in this repository go somewhere?

    python scripts/links.py                       # offline checks only
    python scripts/links.py --api http://127.0.0.1:8490
    python scripts/links.py --api http://127.0.0.1:8490 --external

Three questions a click-through answers slowly and a parse answers exhaustively:

  1. does every `<Link to=...>` and `navigate(...)` reach a declared route?
  2. does every `api.*('/api/...')` call hit a route the server actually serves?
  3. is every external URL we cite still reachable?

Only (1) works offline. (2) needs the API running, because the truth it checks
against is the live OpenAPI document rather than a copy of it. (3) is opt-in
because it leaves the machine, and a citation is worth re-checking on a
schedule rather than on every commit.

A note on false positives, since this script earned its scepticism the hard
way. An early version reported 34 missing endpoints and one dead link; every
single one was this file's fault, not the product's. Two shapes did it:

    `/${role === 'club' ? 'clubs' : 'athletes'}/${slug}`   one template, two routes
    `/api/sponsor/athletes/${slug}/analytics${q}`          a hole that is a query string

So a template is expanded into every path it can denote, and a call is only
reported missing when *none* of those paths resolves. Reporting a defect that
isn't one is worse than reporting nothing: it trains the reader to skim.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[1]
WEB = ROOT / "apps/web/src"

VERB = {"get": "GET", "post": "POST", "put": "PUT", "del": "DELETE", "upload": "POST"}

LINK = (
    r'\bto="(/[^"]*)"',
    r"\bto=\{`(/[^`]*)`\}",
    r"\bto=\{'(/[^']*)'\}",
    r"navigate\(\s*`(/[^`]*)`",
    r"navigate\(\s*'(/[^']*)'",
)
CALL = (r"api\.(get|post|put|del|upload)\s*(?:<[^>]*>)?\s*"
        r"\(\s*([`'\"])((?:/api|/healthz)[^`'\"]*)\2")

TERNARY = re.compile(r"\$\{[^}]*\?\s*'([^']*)'\s*:\s*'([^']*)'\s*\}")
TRAILING_HOLE = re.compile(r"(?<=[^/{])\$\{[^}]*\}$")
HOLE = re.compile(r"\$\{[^}]*\}|\{[^}]*\}|:[A-Za-z_][A-Za-z0-9_]*")


def expand(path: str) -> set[str]:
    """Every real path one template can denote.

    A ternary of string literals inside a hole is two paths, not one. And a
    hole glued to the end of a segment rather than following a "/" is a query
    suffix, so the path without it is also real.
    """
    out = {path}
    if (t := TERNARY.search(path)):
        out = {path[: t.start()] + lit + path[t.end():] for lit in t.groups()}
    return out | {TRAILING_HOLE.sub("", p) for p in out}


def norm(path: str) -> str:
    """A comparable shape: every hole and :param becomes '*'."""
    return HOLE.sub("*", path).split("?")[0].split("#")[0].rstrip("/") or "/"


def matches(path: str, known: set[str]) -> bool:
    """Same segment count, and every segment either equal or a wildcard."""
    if path in known:
        return True
    parts = path.split("/")
    return any(
        len(k.split("/")) == len(parts)
        and all(a == "*" or a == b for a, b in zip(k.split("/"), parts))
        for k in known
    )


def sources() -> list[pathlib.Path]:
    return sorted(WEB.rglob("*.tsx")) + sorted(WEB.rglob("*.ts"))


def check_links() -> list[str]:
    app = (WEB / "App.tsx").read_text(encoding="utf-8")
    routes = {norm(m) for m in re.findall(r'<Route\s+path="([^"]+)"', app)}

    sites: dict[str, set[str]] = {}
    for f in sources():
        text = f.read_text(encoding="utf-8")
        for pattern in LINK:
            for raw in re.findall(pattern, text):
                sites.setdefault(raw, set()).add(f.relative_to(ROOT).as_posix())

    bad = []
    for raw, where in sorted(sites.items()):
        if not any(matches(norm(v), routes) for v in expand(raw)):
            bad.append(f"DEAD LINK  {raw}  in {', '.join(sorted(where))}")
    print(f"  {len(routes)} routes declared, {len(sites)} distinct internal links")
    return bad


def check_calls(api_base: str) -> list[str]:
    with urllib.request.urlopen(f"{api_base}/openapi.json", timeout=30) as r:
        spec = json.load(r)
    served = {(m.upper(), norm(p)) for p, ops in spec["paths"].items() for m in ops}

    sites: dict[tuple[str, str], set[str]] = {}
    for f in sources():
        for verb, _q, path in re.findall(CALL, f.read_text(encoding="utf-8")):
            sites.setdefault((VERB[verb], path), set()).add(f.relative_to(ROOT).as_posix())

    bad = []
    for (verb, raw), where in sorted(sites.items()):
        known = {p for v, p in served if v == verb}
        if not any(matches(norm(v), known) for v in expand(raw)):
            bad.append(f"NO SUCH ROUTE  {verb} {raw}  in {', '.join(sorted(where))}")
    print(f"  {len(served)} routes served, {len(sites)} distinct client calls")
    return bad


# Placeholders are unreachable on purpose: RFC 2606 reserves them so that
# documentation cannot accidentally name a real host. Reaching for them would
# be the bug.
RESERVED = re.compile(r"(^|\.)(example\.(com|org|net)|example|invalid|test|localhost)$")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    " (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/pdf,*/*"}


def check_external() -> list[str]:
    import concurrent.futures as cf

    urls: dict[str, set[str]] = {}
    for f in (ROOT / "business-plan").rglob("*"):
        if f.suffix not in (".md", ".py"):
            continue
        for u in re.findall(r"https?://[^\s\"'`)<>\\]+", f.read_text(encoding="utf-8")):
            u = u.rstrip(".,;")
            if not RESERVED.search(u.split("/")[2].split(":")[0]):
                urls.setdefault(u, set()).add(f.relative_to(ROOT).as_posix())

    def reach(u: str):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(u, headers=UA), timeout=60) as r:
                return u, r.status
        except urllib.error.HTTPError as e:
            return u, e.code
        except Exception as e:  # any failure to reach it is the finding
            return u, type(e).__name__

    with cf.ThreadPoolExecutor(8) as ex:
        results = list(ex.map(reach, urls))

    bad = [f"UNREACHABLE ({s})  {u}  cited in {', '.join(sorted(urls[u]))}"
           for u, s in sorted(results, key=lambda r: str(r[1])) if s != 200]
    print(f"  {len(results)} external citations reached")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", help="base URL of a running API, e.g. http://127.0.0.1:8490")
    ap.add_argument("--external", action="store_true", help="also reach cited URLs")
    args = ap.parse_args()

    failures = check_links()
    if args.api:
        failures += check_calls(args.api)
    else:
        print("  (skipping API calls: pass --api to check them)")
    if args.external:
        failures += check_external()
    else:
        print("  (skipping external citations: pass --external to reach them)")

    if failures:
        print(f"\n{len(failures)} broken:")
        for f in failures:
            print("  -", f)
        return 1
    print("\nevery link checked resolves to something that exists.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
