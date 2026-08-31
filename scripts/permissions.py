"""Every mutating route, attempted as every role.

    python scripts/permissions.py [base_url]

The guard on a route is a claim, and `require_role(...)` in the source is only
the claim written down. This drives the running server and checks the claim
holds: a role that should not reach an endpoint has to be stopped at the guard,
with 401 or 403, and never get far enough to see 404 or 409 -- because "not
found" from an endpoint you may not call still tells you the endpoint exists
and, worse, means the guard did not run.

Path ids are deliberately absent ones, so a permitted role gets a harmless 404
and nothing in the demo is touched.

Each run signs in as six accounts. The auth rate limiter allows ~6 credential
attempts a minute per IP, so running this back to back with the other scripts
will eventually return 429 on login -- that is the limiter working, not a
failure here. Leave a minute between runs.
"""

from __future__ import annotations

import sys
import time

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
PASSWORD = "stride123"
GONE = 999999          # an id that is not there, on purpose

ACCOUNTS = {
    "anonymous": None,
    "athlete": "athlete@demo.stride",
    "club": "club@demo.stride",
    "sponsor": "sponsor@demo.stride",
    "fan": "fan@demo.stride",
    "admin": "admin@demo.stride",
}

#: (method, path, roles allowed) -- mirrors the `require_role` on each route.
#: A fourth element marks a route where the *permitted* role can still be
#: refused for a reason that is not about authorisation: an unverified club may
#: post to `/club/invite-links` and be told to get verified first. Those routes
#: are checked only in the direction that matters -- that everybody else is
#: still stopped at the guard.
ROUTES: list[tuple] = [
    ("POST", f"/api/athlete/content", ("athlete",)),
    ("POST", f"/api/club/content", ("club",)),
    ("POST", f"/api/content/{GONE}", ("athlete", "club")),
    ("POST", f"/api/content/{GONE}/publish", ("athlete", "club")),
    ("DELETE", f"/api/content/{GONE}", ("athlete", "club")),
    ("POST", f"/api/athlete/application", ("athlete",)),
    ("PUT", f"/api/athlete/profile", ("athlete",)),
    ("POST", f"/api/athlete/platforms/connect", ("athlete",)),
    ("POST", f"/api/athlete/platforms/{GONE}/sync", ("athlete",)),
    ("POST", f"/api/athlete/platforms/{GONE}/disconnect", ("athlete",)),
    ("POST", f"/api/athlete/deals/{GONE}/respond", ("athlete",)),
    ("POST", f"/api/athlete/deals/{GONE}/complete", ("athlete",)),
    ("POST", f"/api/athlete/deals/{GONE}/deliverables", ("athlete",)),
    ("POST", f"/api/athlete/invitations/{GONE}/respond", ("athlete",)),
    ("POST", f"/api/club/application", ("club",)),
    ("PUT", f"/api/club/profile", ("club",)),
    ("POST", f"/api/club/members", ("club",)),
    ("POST", f"/api/club/members/{GONE}/remove", ("club",)),
    ("POST", f"/api/club/packages", ("club",)),
    ("POST", f"/api/club/packages/{GONE}/archive", ("club",)),
    ("POST", f"/api/club/nominations", ("club",)),
    # a link lends the club's verification to an athlete, so only a club issues
    # one and only an athlete spends one
    ("POST", f"/api/club/invite-links", ("club",), "state-gated"),
    ("GET", f"/api/club/invite-links", ("club",)),
    ("POST", f"/api/club/invite-links/{GONE}/revoke", ("club",)),
    ("POST", f"/api/athlete/invite-links/nope/redeem", ("athlete",)),
    ("POST", f"/api/clubs/packages/{GONE}/commit", ("sponsor",)),
    ("POST", f"/api/commitments/{GONE}/cancel", ("sponsor",)),
    ("POST", f"/api/campaigns", ("sponsor",)),
    ("POST", f"/api/campaigns/{GONE}/matches", ("sponsor",)),
    ("POST", f"/api/campaigns/{GONE}/offers", ("sponsor",)),
    ("POST", f"/api/deals/{GONE}/withdraw", ("sponsor",)),
    ("POST", f"/api/follows/{GONE}", ("athlete", "fan", "sponsor")),
    ("DELETE", f"/api/follows/{GONE}", ("athlete", "fan", "sponsor")),
    # subscribing is what opens a paywall, so it has to refuse exactly who
    # following refuses -- a club that could subscribe would be reading paid
    # content it has no relationship to
    ("POST", f"/api/subscriptions/athlete/{GONE}", ("athlete", "fan", "sponsor")),
    ("DELETE", f"/api/subscriptions/athlete/{GONE}", ("athlete", "fan", "sponsor")),
    ("POST", f"/api/subscriptions/club/{GONE}", ("athlete", "fan", "sponsor")),
    ("POST", f"/api/admin/applications/{GONE}/proof", ("admin",)),
    ("POST", f"/api/admin/clubs/{GONE}/proof", ("admin",)),
    ("POST", f"/api/admin/clubs/{GONE}/revoke", ("admin",)),
    ("POST", f"/api/admin/auto-check", ("admin",)),
    ("POST", f"/api/admin/chaos", ("admin",)),
    # reads that expose someone else's data
    ("GET", f"/api/athlete/workspace", ("athlete",)),
    ("GET", f"/api/club/workspace", ("club",)),
    ("GET", f"/api/sponsor/workspace", ("sponsor",)),
    ("GET", f"/api/sponsor/athletes/kaia-mercer/analytics", ("sponsor",)),
    ("GET", f"/api/admin/review-queue", ("admin",)),
    ("GET", f"/api/admin/events", ("admin",)),
    # the outbox holds applicants' names, decisions and email addresses
    ("GET", f"/api/admin/outbox", ("admin",)),
    ("GET", f"/api/admin/rejection-reasons", ("admin",)),
    ("GET", f"/api/athlete/invitations", ("athlete",)),
    ("GET", f"/api/athlete/posts", ("athlete",)),
    # these three have to agree: a role that can read the followed-content feed
    # must be a role that can follow, or the grant buys it an empty list
    ("GET", f"/api/feed/content", ("athlete", "fan", "sponsor")),
    # messaging is open to every signed-in role; *who they may write to* is the
    # rule, and that is enforced inside the endpoint rather than at the guard
    ("GET", f"/api/inbox", ("athlete", "club", "sponsor", "fan", "admin")),
    ("GET", f"/api/inbox/{GONE}", ("athlete", "club", "sponsor", "fan", "admin")),
    ("POST", f"/api/messages", ("athlete", "club", "sponsor", "fan", "admin")),
    ("GET", f"/api/notifications", ("athlete", "club", "sponsor", "fan", "admin")),
    ("POST", f"/api/notifications/read", ("athlete", "club", "sponsor", "fan", "admin")),
    ("GET", f"/api/feed", ("athlete", "fan", "sponsor")),
]

sessions: dict[str, httpx.Client] = {}
for role, email in ACCOUNTS.items():
    c = httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True)
    if email:
        r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, f"login {email}: {r.status_code}"
    sessions[role] = c

REFUSED = {401, 403}


def attempt(session: httpx.Client, method: str, path: str) -> int:
    """One request, retried past the rate limiter.

    The sweep is now large enough to exhaust the general bucket -- 348 requests
    against a burst of 300 -- and it drains faster on a fast machine, so this
    passed locally and failed in CI. A 429 says nothing about authorisation, so
    waiting for the refill and asking again measures the thing this script is
    for. Giving up returns the 429 and it is reported, rather than being taken
    for a pass.
    """
    for attempt_number in range(6):
        res = session.request(method, path, json={})
        if res.status_code != 429:
            return res.status_code
        time.sleep(1.5 * (attempt_number + 1))
    return 429
findings: list[str] = []
checked = 0

print(f"{'ROUTE':<52} " + " ".join(f"{r[:6]:>6}" for r in ACCOUNTS))
print("-" * 100)
for method, path, allowed, *flags in ROUTES:
    state_gated = "state-gated" in flags
    cells = []
    for role, _ in ACCOUNTS.items():
        code = attempt(sessions[role], method, path)
        checked += 1
        permitted = role in allowed
        if permitted:
            leaked = code in REFUSED and not state_gated
            if leaked:
                findings.append(f"{method} {path}: {role} is allowed but got {code}")
        else:
            leaked = code not in REFUSED
            if leaked:
                findings.append(f"{method} {path}: {role} is NOT allowed but got {code}")
        cells.append(("!" if leaked else " ") + str(code))
    print(f"{method + ' ' + path:<52} " + " ".join(f"{c:>6}" for c in cells))

print("\n" + "-" * 100)
print(f"{checked} role/route combinations checked")
if findings:
    print(f"\n{len(findings)} FINDINGS:")
    for f in findings:
        print("  -", f)
else:
    print("every route refused every role it should refuse, and admitted every role it should admit.")
raise SystemExit(1 if findings else 0)
