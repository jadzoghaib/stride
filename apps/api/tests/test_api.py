"""End-to-end API contract tests — every role, every core loop, offline.

Ordered file: the rate-limit test exhausts the auth bucket, so it runs last.
"""

from __future__ import annotations

from conftest import PASSWORD, make_session  # noqa: F401 — pytest prepend import mode

# ---- ops surface -------------------------------------------------------------


def test_health_probes(client):
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").json()["status"] == "ready"
    assert "stride_http_requests_total" in client.get("/metrics").text


# ---- public surface ----------------------------------------------------------


def test_public_directory(client):
    page = client.get("/api/athletes").json()
    athletes = page["athletes"]
    assert len(athletes) == page["limit"] == 24
    # No rate card and no score for a signed-out reader: both are sales material
    # aimed at a buyer, and a visitor browsing athletes is not one.
    assert all("base_rate_eur" not in a and "score" not in a for a in athletes)
    assert all("socials" in a for a in athletes)

    facets = client.get("/api/athletes/facets").json()
    assert "Athletics" in facets["sports"]


def test_a_sponsor_sees_the_commercials_a_fan_does_not(sponsor, fan, client):
    """The same endpoint, three readers, three answers."""
    for reader, expected in ((sponsor, True), (fan, False), (client, False)):
        athletes = reader.get("/api/athletes").json()["athletes"]
        scored = [a for a in athletes if a.get("score")]
        priced = [a for a in athletes if a.get("base_rate_eur")]
        assert bool(scored) is expected, "score"
        assert bool(priced) is expected, "rate card"


def test_the_directory_pages_without_skipping_or_repeating(client):
    """A keyset cursor rather than an offset: this set shifts every time an
    athlete is admitted or delisted, and an offset silently skips or repeats a
    row when it does."""
    first = client.get("/api/athletes", params={"limit": 10}).json()
    assert len(first["athletes"]) == 10 and first["next_cursor"]

    second = client.get("/api/athletes",
                        params={"limit": 10, "cursor": first["next_cursor"]}).json()
    assert len(second["athletes"]) == 10

    slugs_a = [a["slug"] for a in first["athletes"]]
    slugs_b = [a["slug"] for a in second["athletes"]]
    assert not set(slugs_a) & set(slugs_b), "pages must not overlap"
    assert slugs_a + slugs_b == sorted(
        slugs_a + slugs_b,
        key=lambda s: next(a["display_name"] for a in first["athletes"] + second["athletes"]
                           if a["slug"] == s))

    # walking to the end terminates and covers everything exactly once
    seen, cursor, guard = [], None, 0
    while guard < 20:
        guard += 1
        page = client.get("/api/athletes",
                          params={"limit": 10, **({"cursor": cursor} if cursor else {})}).json()
        seen += [a["slug"] for a in page["athletes"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 24


def test_a_malformed_cursor_is_refused_rather_than_ignored(client):
    assert client.get("/api/athletes", params={"cursor": "nonsense"}).status_code == 422


def test_public_athlete_detail(client, sponsor):
    detail = client.get("/api/athletes/kaia-mercer").json()
    assert "score" not in detail and "base_rate_eur" not in detail
    assert "audience" not in detail, "a fan has no use for their own age bracket"
    assert detail["clubs"] == []  # independent athlete says so explicitly
    assert [s["platform"] for s in detail["socials"]], "but they do get the handles"

    # the same profile, read by a buyer
    commercial = sponsor.get("/api/athletes/kaia-mercer").json()
    assert commercial["score"]["coverage"]["connected"] == 3
    assert "age" in commercial["audience"]
    assert commercial["base_rate_eur"] > 0

    club_member = client.get("/api/athletes/luca-ferreira").json()
    assert [c["name"] for c in club_member["clubs"]] == ["Meridian FC"]


def test_public_clubs(client):
    clubs = client.get("/api/clubs").json()
    assert len(clubs) == 2
    mfc = client.get("/api/clubs/meridian-fc").json()
    assert len(mfc["roster"]) == 2
    assert len(mfc["packages"]) == 3
    pd = [p for p in mfc["packages"] if p["package_type"] == "player_direct"]
    assert pd and all(p["athlete_name"] for p in pd)


# ---- RBAC boundaries ---------------------------------------------------------


def test_rbac_boundaries(client, athlete, fan, clubu):
    assert client.get("/api/athlete/workspace").status_code == 401
    assert athlete.get("/api/sponsor/workspace").status_code == 403
    assert clubu.get("/api/sponsor/workspace").status_code == 403
    assert fan.get("/api/campaigns/1/matches").status_code == 403
    assert fan.get("/api/admin/events").status_code == 403


def test_admin_reaches_discover_but_not_feed(admin):
    """The client route guards in apps/web/src/App.tsx mirror these two exactly.
    They differ on purpose — a following feed needs follows, which an admin has
    none of — so a client guard that admits admin to /feed only routes them to
    a 403. Keep the two lists in step."""
    assert admin.get("/api/discover").status_code == 200
    assert admin.get("/api/feed").status_code == 403


# ---- athlete loop ------------------------------------------------------------


def test_athlete_workspace_and_deals(athlete):
    ws = athlete.get("/api/athlete/workspace").json()
    assert len(ws["accounts"]) == 3
    assert ws["analytics"] is not None
    assert "platform_kpis" in ws["analytics"]["inputs"]  # evidence attached

    offered = [d for d in ws["deals"] if d["status"] == "offered"]
    assert offered
    deal = athlete.post(f"/api/athlete/deals/{offered[0]['id']}/respond",
                        json={"action": "accept"}).json()
    assert deal["status"] == "accepted"
    again = athlete.post(f"/api/athlete/deals/{offered[0]['id']}/respond",
                         json={"action": "accept"})
    assert again.status_code == 409


def test_session_revocation(athlete):
    assert athlete.post("/api/auth/logout-all").status_code == 200
    assert athlete.get("/api/athlete/workspace").status_code == 401
    relogin = athlete.post("/api/auth/login",
                           json={"email": "athlete@demo.stride", "password": PASSWORD})
    assert relogin.status_code == 200
    assert athlete.get("/api/athlete/workspace").status_code == 200


# ---- sponsor loop ------------------------------------------------------------


def test_matching_is_explainable_and_sorted(sponsor):
    ws = sponsor.get("/api/sponsor/workspace").json()
    campaign = ws["campaigns"][-1]  # oldest = seeded Spring Performance Line
    res = sponsor.get(f"/api/campaigns/{campaign['id']}/matches").json()
    matches = res["matches"]
    assert len(matches) >= 10
    top = matches[0]
    assert set(top["weights"].keys()) == set(top["components"].keys())
    assert abs(sum(top["weights"].values()) - 1.0) < 1e-9
    assert all(matches[i]["score"] >= matches[i + 1]["score"] for i in range(len(matches) - 1))
    assert all(0 <= m["score"] <= 100 for m in matches)
    # athletes without analytics carry an explicit caveat, never silence
    for m in matches:
        if m["analytics_summary"] is None:
            assert any("commercial signals only" in c for c in m["caveats"])


def test_audience_fit_is_campaign_specific(sponsor):
    created = sponsor.post("/api/campaigns", json={
        "name": "Contract Test Campaign", "category": "Wellness",
        "deal_types": ["social_post"], "budget_eur_min": 1000, "budget_eur_max": 8000,
        "target_age_buckets": ["18-24", "25-34"], "target_countries": ["US", "AU"],
        "target_topics": ["wellness", "fitness"]})
    assert created.status_code == 201
    ws = sponsor.get("/api/sponsor/workspace").json()
    base = ws["campaigns"][-1]
    res_a = sponsor.get(f"/api/campaigns/{base['id']}/matches").json()["matches"]
    res_b = sponsor.get(f"/api/campaigns/{created.json()['id']}/matches").json()["matches"]
    slug = res_a[0]["slug"]
    fit_a = res_a[0]["components"]["audience_fit"]
    fit_b = next(m for m in res_b if m["slug"] == slug)["components"]["audience_fit"]
    assert fit_a != fit_b


def test_offer_lifecycle(sponsor):
    ws = sponsor.get("/api/sponsor/workspace").json()
    campaign = ws["campaigns"][-1]
    matches = sponsor.get(f"/api/campaigns/{campaign['id']}/matches").json()["matches"]
    target = next(m for m in matches if m["slug"] != "kaia-mercer")
    offer = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": target["athlete_id"], "deal_type": "social_post",
        "amount_eur": 4000, "message": "test offer"})
    assert offer.status_code == 201
    dup = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": target["athlete_id"], "deal_type": "social_post", "amount_eur": 4000})
    assert dup.status_code == 409
    assert sponsor.post(f"/api/deals/{offer.json()['id']}/withdraw").status_code == 200


# ---- club loop ---------------------------------------------------------------


def test_club_workspace_and_guardrails(clubu):
    ws = clubu.get("/api/club/workspace").json()
    assert ws["club"]["slug"] == "meridian-fc"
    assert len(ws["roster"]) == 2
    # The seed backs one of this club's packages, so the figure is the sum of
    # its active commitments rather than a hard-coded zero -- a demo club with
    # no revenue demonstrated the board and not the reason for it.
    assert ws["revenue_active"] == sum(x["amount_eur"] for x in ws["commitments"]
                                       if x["status"] == "active") > 0
    bad = clubu.post("/api/club/packages", json={
        "name": "Bad package", "package_type": "player_direct",
        "price_eur": 100, "athlete_slug": "kaia-mercer"})
    assert bad.status_code == 409  # not on roster


def test_package_backing_lifecycle(client, sponsor, clubu, fan):
    mfc = client.get("/api/clubs/meridian-fc").json()
    pd = next(p for p in mfc["packages"] if p["package_type"] == "player_direct")

    before = clubu.get("/api/club/workspace").json()["revenue_active"]
    assert fan.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 403
    commit = sponsor.post(f"/api/clubs/packages/{pd['id']}/commit")
    assert commit.status_code == 201
    assert sponsor.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 409

    ws = clubu.get("/api/club/workspace").json()
    assert ws["revenue_active"] == before + pd["price_eur"]
    sws = sponsor.get("/api/sponsor/workspace").json()
    assert any(x["package_id"] == pd["id"] and x["status"] == "active"
               for x in sws["club_commitments"])
    assert sponsor.post(f"/api/commitments/{commit.json()['id']}/cancel").status_code == 200


def test_roster_removal_ends_commitments(client, sponsor, clubu):
    mfc = client.get("/api/clubs/meridian-fc").json()
    pd = next(p for p in mfc["packages"] if p["package_type"] == "player_direct")
    before = clubu.get("/api/club/workspace").json()["revenue_active"]
    assert sponsor.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 201

    marcus = next(m for m in mfc["roster"] if m["slug"] == "marcus-oyelaran")
    removed = clubu.post(f"/api/club/members/{marcus['athlete_id']}/remove").json()
    assert removed["commitments_ended"] == 1
    ws = clubu.get("/api/club/workspace").json()
    # only the player-direct commitment ends; the club-level one the seed
    # placed is untouched by a roster change
    assert ws["revenue_active"] == before
    assert len(ws["roster"]) == 1


# ---- fan loop ----------------------------------------------------------------


def test_discovery_and_feed(fan):
    # discover answers with both kinds now: clubs used to have their own tab and
    # their own filters, which meant two places to ask the same question
    found = fan.get("/api/discover?interests=running,cycling&country=Germany").json()
    ranked = found["athletes"]
    assert ranked[0]["affinity"] > 0
    assert ranked[0]["reasons"]
    feed = fan.get("/api/feed").json()
    assert len(feed) == 4  # seeded follows

    new_id = next(a["id"] for a in ranked if not a["following"])
    assert fan.post(f"/api/follows/{new_id}").status_code == 201
    assert len(fan.get("/api/feed").json()) == 5
    assert fan.delete(f"/api/follows/{new_id}").status_code == 200


# ---- registration (local credential path) ------------------------------------


def test_registration_creates_analytics_identity(client):
    from fastapi.testclient import TestClient
    from stride_api.main import app
    reg = TestClient(app)
    me = reg.post("/api/auth/register", json={
        "email": "contract-test@stride.test", "password": "longenough1",
        "display_name": "Contract Athlete", "role": "athlete",
        "sport": "Rowing", "country": "Ireland"})
    assert me.status_code == 201
    assert me.json()["athlete_profile"] is not None

    ws = reg.get("/api/athlete/workspace").json()
    assert ws["analytics"] is None  # nothing connected yet — no fabricated numbers

    # consent is the lawful basis for the ingest, so the server refuses without it
    assert reg.post("/api/athlete/platforms/connect",
                    json={"platform": "instagram"}).status_code == 422
    assert reg.get("/api/athlete/workspace").json()["analytics"] is None

    assert reg.post("/api/athlete/platforms/connect",
                    json={"platform": "instagram", "consent": True,
                          "policy_version": "2026-08-17"}).status_code == 200
    ws = reg.get("/api/athlete/workspace").json()
    assert ws["analytics"] is not None


def test_platform_consent_and_withdrawal_are_both_recorded(admin):
    """A consent trail that records only the grant is not a trail (Art. 7(3)).

    Self-contained: registers its own athlete so it never disturbs the shared
    demo sessions other tests assert against.
    """
    from fastapi.testclient import TestClient
    from stride_api.main import app
    athlete = TestClient(app)
    assert athlete.post("/api/auth/register", json={
        "email": "consent-test@stride.test", "password": "longenough1",
        "display_name": "Consent Athlete", "role": "athlete",
        "sport": "Judo", "country": "Spain"}).status_code == 201

    connected = athlete.post("/api/athlete/platforms/connect",
                             json={"platform": "tiktok", "consent": True,
                                   "policy_version": "2026-08-17"})
    assert connected.status_code == 200
    account_id = connected.json()["account"]["id"]
    assert athlete.post(f"/api/athlete/platforms/{account_id}/disconnect").status_code == 200

    # NB: the events table names these object_type / object_id, not entity_*
    events = admin.get("/api/admin/events?limit=1000").json()
    mine = {e["event_type"]: e["detail"] for e in events
            if e["object_id"] == account_id and e["event_type"].startswith("consent.")}

    assert "consent.platform_granted" in mine, "granting must leave a record"
    assert "consent.platform_withdrawn" in mine, "withdrawing must leave one too"
    assert mine["consent.platform_granted"]["policy_version"] == "2026-08-17"
    assert "aggregate_demographics" in mine["consent.platform_granted"]["scopes"]


def test_duplicate_email_rejected(client):
    dup = client.post("/api/auth/register", json={
        "email": "contract-test@stride.test", "password": "longenough1",
        "display_name": "Someone Else", "role": "fan"})
    assert dup.status_code == 409


# ---- audit + chaos -----------------------------------------------------------


def test_audit_log_admin_only(admin, fan):
    events = admin.get("/api/admin/events?limit=50").json()
    assert len(events) == 50
    assert fan.get("/api/admin/events").status_code == 403


def test_chaos_drill_and_recovery(client, admin):
    assert admin.post("/api/admin/chaos", json={"error_rate": 1.0}).status_code == 200
    assert client.get("/api/athletes").status_code == 503
    assert admin.post("/api/admin/chaos", json={"db_down": True}).status_code == 200
    assert client.get("/readyz").status_code == 503
    assert admin.post("/api/admin/chaos/reset").status_code == 200
    assert client.get("/api/athletes").status_code == 200
    assert client.get("/readyz").status_code == 200


# ---- security hardening (LAST: the brute-force test drains the auth bucket) --


def test_security_headers(client):
    res = client.get("/api/athletes")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["content-security-policy"] == "default-src 'none'"


def test_oversized_body_rejected(client):
    res = client.post("/api/auth/logout", content=b"x" * 300_000,
                      headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def test_login_brute_force_rate_limited(client):
    codes = [client.post("/api/auth/login",
                         json={"email": "nobody@nowhere.test", "password": "wrong-pass"}).status_code
             for _ in range(30)]
    assert 401 in codes
    assert codes[-1] == 429


def test_discover_searches_athletes_and_clubs_together(fan):
    """One search box, four questions: name, sport, country, kind."""
    everyone = fan.get("/api/discover").json()
    assert everyone["athletes"] and everyone["clubs"]

    only_clubs = fan.get("/api/discover", params={"kind": "club"}).json()
    assert only_clubs["athletes"] == [] and only_clubs["clubs"]

    only_athletes = fan.get("/api/discover", params={"kind": "athlete"}).json()
    assert only_athletes["clubs"] == [] and only_athletes["athletes"]

    by_name = fan.get("/api/discover", params={"q": "meridian"}).json()
    assert [c["name"] for c in by_name["clubs"]] == ["Meridian FC"]
    assert by_name["athletes"] == [], "the search applies to both halves"

    by_sport = fan.get("/api/discover", params={"sport": "Boxing"}).json()
    assert [c["name"] for c in by_sport["clubs"]] == ["Ironline Combat Club"]
