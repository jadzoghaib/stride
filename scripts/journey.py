"""End-to-end journey against a running server.

    python scripts/journey.py [base_url]

The test suite drives the app through `TestClient`, which is the app object in
the same process. This drives the thing that is actually listening: real
uvicorn, the real database file, and — if pointed at the Vite port — the dev
proxy too. That difference is where "all tests pass but the demo is broken"
lives, and it is the only way to catch it.

Every assertion here is a **product rule**, not an implementation detail. They
are the invariants that were each broken once and are meant to stay closed:

    1  unmeasured is null, never zero
    2  nothing verifies itself
    3  a rejected proof is sticky
    4  disconnecting withdraws what it supplied
    5  a finished report does not move
    6  a roster needs the athlete's consent
    7  a locked item withholds the body and nothing else
    8  every score decomposes
    9  the applicant sees the bar they are judged against
   10  a listing that predates the gate survives insufficiency
   11  the age gate cannot be bought past
   12  filters follow the data

It puts back everything it moves, so it can be run repeatedly against the same
demo database. That matters more than it sounds: the first version left the
athlete delisted and the roster invitation standing, so a second run failed on
the first one's leftovers and read like three product regressions.
"""

from __future__ import annotations

import sqlite3
import sys

import httpx

# Windows consoles default to cp1252, which cannot encode the rule separators or
# the middots in these labels. The output is the deliverable here, so make it
# survive the terminal it is printed to.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5181"
PASSWORD = "stride123"

passed: list[str] = []
failed: list[str] = []


def check(rule: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(rule)
    mark = "  ok  " if ok else "  FAIL"
    print(f"{mark}  {rule}{('  — ' + detail) if detail and not ok else ''}")


def session(email: str | None = None) -> httpx.Client:
    c = httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True)
    if email:
        r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:120]}"
    return c


def local_db() -> sqlite3.Connection | None:
    """The demo database, when this run is pointed at a local server.

    Two things here cannot go through the API: withdrawing a platform connection
    is something the platform does, not something the product exposes, and the
    run has to put back what it changed or the *second* run fails on the first
    one's leftovers. A journey that only passes once is barely a test.

    The path comes from the app's own settings rather than from a guess, because
    guessing it is how this script spent an afternoon reporting a broken consent
    rule while inspecting a different database than the server was writing to.
    """
    try:
        from stride_api.config import Settings
    except ModuleNotFoundError:
        return None
    path = Settings().db_path
    if not path.exists():
        return None
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m" if sys.stdout.isatty() else f"\n{title}")


# ── public surfaces ─────────────────────────────────────────────────────────
section("Public")
pub = session()

health = pub.get("/healthz")
check("the server is up", health.status_code == 200, health.text[:80])

directory = pub.get("/api/athletes").json()
check("the directory lists athletes", len(directory["athletes"]) > 0)

hit = pub.get("/api/athletes", params={"q": "Marcus"}).json()["athletes"]
check("directory search matches a full name",
      len(hit) == 1 and hit[0]["display_name"] == "Marcus Oyelaran",
      f"got {[a['display_name'] for a in hit]}")

facets = pub.get("/api/athletes/facets").json()
check("filters are derived from data, not hard-coded",
      all(k in facets for k in ("sports", "countries", "audience_countries", "topics"))
      and len(facets["audience_countries"]) > 0)
check("profile countries and audience codes are kept apart",
      any(len(c) > 3 for c in facets["countries"])
      and all(len(c) <= 3 for c in facets["audience_countries"]),
      f"{facets['countries'][:2]} vs {facets['audience_countries'][:3]}")

detail = pub.get("/api/athletes/kaia-mercer").json()
check("a public profile carries the handles, not the sales material",
      bool(detail.get("socials"))
      and "score" not in detail and "base_rate_eur" not in detail and "audience" not in detail,
      str([k for k in ("score", "base_rate_eur", "audience") if k in detail]))


# ── athlete ─────────────────────────────────────────────────────────────────
section("Athlete")
ath = session("athlete@demo.stride")

db = local_db()
before_state: dict = {}
if db:
    profile = dict(db.execute(
        "SELECT id, status FROM athlete_profiles WHERE slug = 'kaia-mercer'").fetchone())
    application = db.execute(
        "SELECT * FROM athlete_applications WHERE athlete_id = ?", (profile["id"],)).fetchone()
    before_state = {
        "profile": profile,
        "application": dict(application) if application else None,
        "member_ids": [r["id"] for r in db.execute("SELECT id, status FROM club_members")],
        "member_status": {r["id"]: r["status"]
                          for r in db.execute("SELECT id, status FROM club_members")},
    }

ws = ath.get("/api/athlete/workspace").json()
check("the athlete workspace loads", "editable" in ws)
before_status = ws["editable"]["status"]

app_view = ath.get("/api/athlete/application").json()
check("RULE 9 · the applicant is shown the admit bar",
      app_view.get("thresholds", {}).get("admit") is not None)

weak = ath.post("/api/athlete/application", json={
    "competition_level": "local", "years_competing": 1, "birth_year": 2004,
    "proof_kind": "none", "proof_url": ""}).json()
check("RULE 10 · a weak claim does not delist a grandfathered athlete",
      weak["listing"] == "listed" and weak["decision"] != "admitted",
      f"decision={weak['decision']} listing={weak['listing']}")

minor = ath.post("/api/athlete/application", json={
    "competition_level": "regional", "years_competing": 2, "birth_year": 2011,
    "proof_kind": "none", "proof_url": ""}).json()
check("RULE 11 · a declared age under 16 is refused and delists",
      minor["rule"] == "under_minimum_age" and minor["listing"] == "draft",
      f"rule={minor['rule']} listing={minor['listing']}")

# put the athlete back where the seed had them
ath.post("/api/athlete/application", json={
    "competition_level": "national", "years_competing": 6, "birth_year": 2002,
    "proof_kind": "results", "proof_url": "https://athletics.example/results"})

posts = ath.get("/api/athlete/posts").json()
check("the athlete has attachable posts", len(posts) > 0)


# ── content ─────────────────────────────────────────────────────────────────
section("Content")
free = ath.post("/api/athlete/content", json={
    "kind": "post", "title": "Journey · free post", "body": "Visible to anyone.",
    "min_tier": ""}).json()
paid = ath.post("/api/athlete/content", json={
    "kind": "course", "title": "Journey · paid course", "body": "Members only.",
    "min_tier": "insider"}).json()
for item in (free, paid):
    ath.post(f"/api/content/{item['id']}/publish")

check("a course accepts ordered parts",
      ath.post("/api/athlete/content", json={
          "kind": "post", "title": "Journey · week 1",
          "part_of": paid["id"], "position": 1}).status_code == 201)

check("sponsored content must name the advertiser",
      ath.post("/api/athlete/content", json={
          "kind": "post", "title": "x", "label": "sponsored"}).status_code == 422)
check("a session without a date is refused",
      ath.post("/api/athlete/content", json={
          "kind": "session", "title": "x"}).status_code == 422)

seen = {i["title"]: i for i in pub.get("/api/athletes/kaia-mercer/content").json()}
open_one, shut = seen.get("Journey · free post"), seen.get("Journey · paid course")
check("RULE 7 · a locked item withholds the body and nothing else",
      bool(open_one and shut)
      and open_one["locked"] is False and open_one["body"]
      and shut["locked"] is True and shut["body"] == ""
      and shut["title"] and shut["tier_label"],
      f"free={open_one and open_one['locked']} paid={shut and shut['locked']}")


# ── sponsor ─────────────────────────────────────────────────────────────────
section("Sponsor")
spo = session("sponsor@demo.stride")

commercial = spo.get("/api/athletes/kaia-mercer").json()
check("RULE 8 · and a sponsor still gets the decomposed score",
      bool(commercial.get("score", {}).get("dimensions")) and commercial.get("base_rate_eur"),
      str(sorted(commercial)[:6]))

board = spo.get("/api/sponsor/workspace").json()
check("the sponsor board loads", "campaigns" in board)
campaign_id = board["campaigns"][0]["id"]

matches = spo.get(f"/api/campaigns/{campaign_id}/matches").json()
top = matches["matches"][0]
check("matches come back ranked", len(matches["matches"]) > 1
      and matches["matches"][0]["score"] >= matches["matches"][1]["score"])

# The score is the components blended by the weights that actually applied —
# `effective_weights`, not the nominal ones, because a dimension that could not
# be measured is excluded and its weight redistributed among the rest.
weights = top["effective_weights"]
rebuilt = 100 * sum(top["components"][k] * weights[k] for k in top["components"])
check("RULE 8 · a match score is exactly its components times the weights applied",
      abs(rebuilt - top["score"]) < 0.15,
      f"rebuilt {rebuilt:.2f} vs reported {top['score']:.2f}")
check("RULE 8 · the applied weights sum to one",
      abs(sum(weights.values()) - 1.0) < 1e-6, f"{sum(weights.values()):.4f}")
check("every match explains itself",
      bool(top.get("reasons") or top.get("caveats")))

unmeasured = None
for d in spo.get("/api/sponsor/workspace").json().get("deals", []):
    perf = spo.get(f"/api/deals/{d['id']}/performance")
    if perf.status_code == 200 and perf.json()["delivered"]["posts"] == 0:
        unmeasured = perf.json()
        break
check("RULE 1 · an unmeasured campaign reads as unmeasured, not free",
      unmeasured is not None
      and unmeasured["delivered"]["reach"] is None
      and unmeasured["delivered"]["engagements"] is None
      and unmeasured["variance_pct"] is None
      and unmeasured["delivered"]["posts"] == 0,
      "no unmeasured deal found" if unmeasured is None else str(unmeasured["delivered"]))


# ── club ────────────────────────────────────────────────────────────────────
section("Club")
clb = session("club@demo.stride")

club_app = clb.get("/api/club/application").json()
scored = club_app.get("scored", {})
check("RULE 2 · a club above the bar still waits for a human",
      scored.get("legitimacy", 0) >= 65 and club_app["application"]["decision"] == "review",
      f"legitimacy={scored.get('legitimacy')} decision={club_app['application']['decision']}")

check("an unverified club cannot nominate",
      clb.post("/api/club/nominations", json={"athlete_slug": "sofia-brandt"}).status_code == 403)

invite = clb.post("/api/club/members", json={"athlete_slug": "sofia-brandt", "position": "Runner"})
check("inviting an athlete is accepted", invite.status_code == 201, invite.text[:100])

roster = {m["slug"]: m for m in clb.get("/api/club/workspace").json()["roster"]}
check("RULE 6 · an invitation is not a membership",
      roster.get("sofia-brandt", {}).get("membership_status") == "invited",
      str(roster.get("sofia-brandt", {}).get("membership_status")))

pkg = clb.post("/api/club/packages", json={
    "name": "Journey direct", "package_type": "player_direct", "price_eur": 5000,
    "description": "x", "athlete_slug": "sofia-brandt", "perks": []})
check("RULE 6 · no package can be sold around an athlete who has not accepted",
      pkg.status_code == 409, f"status={pkg.status_code}")


# ── admin ───────────────────────────────────────────────────────────────────
section("Admin")
adm = session("admin@demo.stride")

queue = adm.get("/api/admin/review-queue", params={"decision": "review"}).json()
check("the review queue is populated and openable",
      len(queue) > 0 and any(r.get("proof_url") for r in queue),
      f"{len(queue)} rows")

chaos = adm.post("/api/admin/chaos", json={"latency_ms": 0, "error_rate": 0}).json()
check("the chaos endpoint reports whether injection is enabled",
      "enabled" in chaos, str(list(chaos)))
adm.post("/api/admin/chaos/reset")

audit = adm.get("/api/admin/events").json()
check("the audit log records what happened", len(audit) > 0)


# ── fan ─────────────────────────────────────────────────────────────────────
section("Supporter")
fan = session("fan@demo.stride")

disc = fan.get("/api/discover", params={"interests": "Athletics"}).json()
check("discovery ranks and explains",
      len(disc["athletes"]) > 0 and disc["athletes"][0].get("affinity") is not None
      and bool(disc["athletes"][0].get("reasons")))
check("RULE 12 · discovery searches athletes and clubs in one place",
      bool(disc["clubs"])
      and fan.get("/api/discover", params={"kind": "athlete"}).json()["clubs"] == [],
      f"{len(disc['clubs'])} clubs")
check("a fan is not shown the sponsorship rate card or the score",
      all("base_rate_eur" not in a and "score" not in a for a in disc["athletes"]),
      str([k for k in disc["athletes"][0] if k in ("base_rate_eur", "score")]))

feed_content = fan.get("/api/feed/content").json()
mine = [i for i in feed_content if i["title"].startswith("Journey ·")]
check("the free feed carries followed athletes' content", len(mine) > 0)
check("RULE 7 · the feed respects the lock",
      all(i["body"] == "" for i in mine if i["locked"]),
      "a locked item leaked its body")


# ── consent ─────────────────────────────────────────────────────────────────
section("Consent")
if db:
    acct = db.execute("""
        SELECT pa.id FROM platform_accounts pa
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        WHERE a.slug = 'kaia-mercer' AND pa.connection_status = 'connected' LIMIT 1""").fetchone()
    before = len(ath.get("/api/athlete/posts").json())
    db.execute("UPDATE platform_accounts SET connection_status='disconnected' WHERE id=?",
               (acct["id"],))
    db.commit()
    after = len(ath.get("/api/athlete/posts").json())
    db.execute("UPDATE platform_accounts SET connection_status='connected' WHERE id=?",
               (acct["id"],))
    db.commit()
    check("RULE 4 · disconnecting withdraws the posts it supplied", after < before,
          f"{before} -> {after}")
else:
    check("RULE 4 · disconnecting withdraws the posts it supplied", False,
          "no local database: point this at a local server to drive the consent rule")


# ── put the demo back ─────────────────────────────────────────────
# The run deliberately delists an athlete (rule 11), files a weak claim (rule 10),
# invites someone to a roster (rule 6) and publishes content (rule 7). None of
# that can be undone through the API -- re-submitting a good claim resets the
# proof to unverified by design -- so it goes back the way it came, through the
# database. Without this the next run reads its own wreckage as failures.
if db and before_state:
    db.execute("DELETE FROM content_items WHERE title LIKE 'Journey · %'")
    db.execute("DELETE FROM club_members WHERE id NOT IN (%s)"
               % ",".join(str(i) for i in before_state["member_ids"] or [0]))
    for member_id, status in before_state["member_status"].items():
        db.execute("UPDATE club_members SET status = ? WHERE id = ?", (status, member_id))
    saved = before_state["application"]
    if saved:
        cols = [c for c in saved if c != "id"]
        db.execute("UPDATE athlete_applications SET %s WHERE id = ?"
                   % ", ".join(f"{c} = ?" for c in cols),
                   tuple(saved[c] for c in cols) + (saved["id"],))
    db.execute("UPDATE athlete_profiles SET status = ? WHERE id = ?",
               (before_state["profile"]["status"], before_state["profile"]["id"]))
    db.commit()
    db.close()


# ── verdict ─────────────────────────────────────────────────────────────────
print()
print("─" * 62)
print(f"{len(passed)} passed, {len(failed)} failed")
if failed:
    print("\nfailed:")
    for f in failed:
        print("  -", f)
raise SystemExit(1 if failed else 0)
