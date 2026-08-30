"""Does a change made by one role reach the roles that should see it?

    python scripts/propagation.py [base_url]

The permission sweep asks who may act. This asks whether acting had an effect
anywhere else -- an athlete publishes and a fan sees it, a club invites and the
athlete is asked, a sponsor offers and it lands in an inbox. Each line names the
author, the reader, and the thing that has to cross between them.

Everything is put back at the end, so it can be run repeatedly.

Each run signs in as six accounts. The auth rate limiter allows ~6 credential
attempts a minute per IP, so running this back to back with the other scripts
will eventually return 429 on login -- that is the limiter working, not a
failure here. Leave a minute between runs.
"""

from __future__ import annotations

import sqlite3
import sys

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173"
PASSWORD = "stride123"
TAG = "Propagation probe"

passed: list[str] = []
failed: list[str] = []


def check(author: str, reader: str, claim: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(claim)
    mark = "  ok  " if ok else "  FAIL"
    tail = ("  -- " + detail) if detail and not ok else ""
    print(f"{mark}  {author:>7} -> {reader:<7} {claim}{tail}")


def session(email: str | None = None) -> httpx.Client:
    c = httpx.Client(base_url=BASE, timeout=30.0, follow_redirects=True)
    if email:
        r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
        assert r.status_code == 200, f"login {email}: {r.status_code} {r.text[:120]}"
    return c


def local_db() -> sqlite3.Connection | None:
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


pub = session()
ath = session("athlete@demo.stride")
clb = session("club@demo.stride")
spo = session("sponsor@demo.stride")
fan = session("fan@demo.stride")
adm = session("admin@demo.stride")
db = local_db()

def sweep(con) -> None:
    """Clear anything a previous run of this script left behind.

    Run at the start as well as the end. A run that dies half way through -- and
    the first two did -- leaves an open offer and a roster row, and the next run
    then reads `offer_already_open` and `already_invited` as product failures.
    A cleanup that only happens on the happy path is not a cleanup.
    """
    con.execute("DELETE FROM content_items WHERE title LIKE ?", (f"{TAG}%",))
    con.execute("DELETE FROM deals WHERE message = ?", (f"{TAG} offer",))
    con.execute("UPDATE platform_accounts SET connection_status = 'connected'"
                " WHERE connection_status = 'disconnected'")
    con.commit()


if db:
    sweep(db)

before_members = [r["id"] for r in db.execute("SELECT id FROM club_members")] if db else []
made: list[int] = []

print("\nContent")
free = ath.post("/api/athlete/content", json={
    "kind": "post", "title": f"{TAG} free", "body": "Anyone may read this.",
    "min_tier": ""}).json()
made.append(free["id"])
ath.post(f"/api/content/{free['id']}/publish")

wall = [i["title"] for i in pub.get("/api/athletes/kaia-mercer/content").json()]
check("athlete", "public", "a published post reaches a signed-out visitor",
      f"{TAG} free" in wall)
check("athlete", "fan", "and reaches a follower's feed",
      any(i["title"] == f"{TAG} free" for i in fan.get("/api/feed/content").json()))

draft = ath.post("/api/athlete/content", json={"kind": "post", "title": f"{TAG} draft"}).json()
made.append(draft["id"])
check("athlete", "public", "a draft reaches nobody",
      all(i["title"] != f"{TAG} draft"
          for i in pub.get("/api/athletes/kaia-mercer/content").json()))

ath.post(f"/api/content/{free['id']}", json={
    "kind": "post", "title": f"{TAG} edited", "body": "Anyone may read this.", "min_tier": ""})
titles = [i["title"] for i in pub.get("/api/athletes/kaia-mercer/content").json()]
check("athlete", "public", "an edit replaces what the reader had",
      f"{TAG} edited" in titles and f"{TAG} free" not in titles, str(titles[:3]))

ath.post(f"/api/content/{free['id']}", json={
    "kind": "post", "title": f"{TAG} edited", "body": "Members only now.",
    "min_tier": "insider"})
feed = {i["title"]: i for i in fan.get("/api/feed/content").json()}
locked = feed.get(f"{TAG} edited", {})
check("athlete", "fan", "raising the tier locks the body and nothing else",
      locked.get("locked") is True and locked.get("body") == ""
      and locked.get("title") == f"{TAG} edited",
      str({k: locked.get(k) for k in ("locked", "body")}))

prod = ath.post("/api/athlete/content", json={
    "kind": "product", "title": f"{TAG} cap",
    "external_url": "https://shop.example/probe-cap"}).json()
made.append(prod["id"])
ath.post(f"/api/content/{prod['id']}/publish")
shop = {i["title"]: i for i in pub.get("/api/athletes/kaia-mercer/content").json()}
got = shop.get(f"{TAG} cap", {})
check("athlete", "public", "a product arrives unlocked, with its store link",
      got.get("locked") is False and got.get("external_url") == "https://shop.example/probe-cap")

ath.delete(f"/api/content/{prod['id']}")
made.remove(prod["id"])
check("athlete", "public", "a deletion removes it for the reader too",
      all(i["title"] != f"{TAG} cap"
          for i in pub.get("/api/athletes/kaia-mercer/content").json()))

print("\nConsent")
ws = ath.get("/api/athlete/workspace").json()
live = [a for a in ws["accounts"] if a["connection_status"] == "connected"]
before_platforms = {n["platform"] for n in
                    pub.get("/api/athletes/kaia-mercer/news", params={"limit": 60}).json()}
target = live[0]
dropped = ath.post(f"/api/athlete/platforms/{target['id']}/disconnect")
check("athlete", "public", "an athlete can withdraw a platform through the product",
      dropped.status_code == 200, f"{dropped.status_code} {dropped.text[:80]}")
after_platforms = {n["platform"] for n in
                   pub.get("/api/athletes/kaia-mercer/news", params={"limit": 60}).json()}
check("athlete", "public", "and the withdrawn platform stops feeding the public wall",
      target["platform"] in before_platforms and target["platform"] not in after_platforms,
      f"{sorted(before_platforms)} -> {sorted(after_platforms)}")
if db:
    db.execute("UPDATE platform_accounts SET connection_status = 'connected' WHERE id = ?",
               (target["id"],))
    db.commit()

print("\nRoster")
invite = clb.post("/api/club/members", json={"athlete_slug": "kaia-mercer", "position": "Distance"})
check("club", "athlete", "a club invitation reaches the athlete",
      invite.status_code == 201
      and any(i["name"] == "Meridian FC" for i in ath.get("/api/athlete/invitations").json()),
      invite.text[:80])

roster = {m["slug"]: m for m in clb.get("/api/club/workspace").json()["roster"]}
check("club", "club", "and reads as invited, not a member, until it is answered",
      roster.get("kaia-mercer", {}).get("membership_status") == "invited")

pending = ath.get("/api/athlete/invitations").json()
if pending:
    ath.post(f"/api/athlete/invitations/{pending[0]['invitation_id']}/respond",
             json={"action": "accept"})
roster = {m["slug"]: m for m in clb.get("/api/club/workspace").json()["roster"]}
check("athlete", "club", "accepting turns the invitation into a membership",
      roster.get("kaia-mercer", {}).get("membership_status") == "active")
check("athlete", "public", "and the club appears on the athlete's public profile",
      any(c["slug"] == "meridian-fc"
          for c in pub.get("/api/athletes/kaia-mercer").json()["clubs"]))

print("\nCommerce")
club_page = pub.get("/api/clubs/meridian-fc").json()
check("club", "public", "a club's packages are visible to a signed-out visitor",
      len(club_page.get("packages", [])) > 0)
check("club", "sponsor", "and a sponsor sees the same club page",
      len(spo.get("/api/clubs/meridian-fc").json().get("packages", []))
      == len(club_page.get("packages", [])))

board = spo.get("/api/sponsor/workspace").json()
campaign_id = board["campaigns"][0]["id"]
matches = spo.get(f"/api/campaigns/{campaign_id}/matches").json()["matches"]
check("sponsor", "sponsor", "matching returns ranked, explained candidates",
      len(matches) > 1 and bool(matches[0].get("reasons")))

# The sponsor already has an open offer to this athlete from the seed, and a
# second one is correctly refused -- so the propagation is checked on the real
# one rather than by manufacturing a duplicate the product is right to reject.
inbox = ath.get("/api/athlete/workspace").json()["deals"]
check("sponsor", "athlete", "a sponsor's offer sits in the athlete's inbox",
      any(d["status"] == "offered" for d in inbox),
      str([d["status"] for d in inbox]))

# ...and specifically one from *this* sponsor. The athlete's inbox spans every
# sponsor, and a campaign this sponsor does not own is a 404 to them -- rightly,
# since "forbidden" would confirm it exists.
mine_only = {c["id"] for c in board["campaigns"]}
open_offer = next((d for d in inbox
                   if d["status"] == "offered" and d["campaign_id"] in mine_only), None)

if open_offer:
    duplicate = spo.post(f"/api/campaigns/{open_offer['campaign_id']}/offers", json={
        "athlete_id": pub.get("/api/athletes/kaia-mercer").json()["id"],
        "amount_eur": 999, "deal_type": "social_post", "message": f"{TAG} offer"})
    check("sponsor", "sponsor", "and a second open offer to the same athlete is refused",
          duplicate.status_code == 409, f"{duplicate.status_code} {duplicate.text[:70]}")

    saved = None
    if db:
        saved = dict(db.execute("SELECT * FROM deals WHERE id = ?",
                                (open_offer["id"],)).fetchone())
    ath.post(f"/api/athlete/deals/{open_offer['id']}/respond", json={"action": "accept"})
    pipeline = spo.get("/api/sponsor/workspace").json()["deals"]
    mine = [d for d in pipeline if d["id"] == open_offer["id"]]
    check("athlete", "sponsor", "accepting it moves the sponsor's pipeline",
          bool(mine) and mine[0]["status"] == "accepted",
          str(mine[0]["status"]) if mine else "the deal left the pipeline")
    if db and saved:
        cols = [c for c in saved if c != "id"]
        db.execute("UPDATE deals SET " + ", ".join(f"{c} = ?" for c in cols) + " WHERE id = ?",
                   tuple(saved[c] for c in cols) + (saved["id"],))
        db.commit()

print("\nAdmission")
check("admin", "admin", "the review queue reaches the reviewer",
      len(adm.get("/api/admin/review-queue").json()) > 0)

if db:
    sweep(db)
    keep = before_members or [0]
    db.execute("DELETE FROM club_members WHERE id NOT IN ("
               + ", ".join(str(i) for i in keep) + ")")
    db.commit()
    db.close()

print()
print("-" * 62)
print(f"{len(passed)} passed, {len(failed)} failed")
if failed:
    print("\nfailed:")
    for name in failed:
        print("  -", name)
raise SystemExit(1 if failed else 0)
