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
    athletes = client.get("/api/athletes").json()
    assert len(athletes) == 24
    scored = [a for a in athletes if a["score"]]
    assert len(scored) >= 20
    assert any(a["score"] is None for a in athletes)  # unconnected stays unscored

    facets = client.get("/api/athletes/facets").json()
    assert "Athletics" in facets["sports"]


def test_public_athlete_detail(client):
    detail = client.get("/api/athletes/kaia-mercer").json()
    assert detail["score"]["coverage"]["connected"] == 3
    assert "age" in detail["audience"]
    assert detail["clubs"] == []  # independent athlete says so explicitly

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
        "deal_types": ["social_post"], "budget_usd_min": 1000, "budget_usd_max": 8000,
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
        "amount_usd": 4000, "message": "test offer"})
    assert offer.status_code == 201
    dup = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": target["athlete_id"], "deal_type": "social_post", "amount_usd": 4000})
    assert dup.status_code == 409
    assert sponsor.post(f"/api/deals/{offer.json()['id']}/withdraw").status_code == 200


# ---- club loop ---------------------------------------------------------------


def test_club_workspace_and_guardrails(clubu):
    ws = clubu.get("/api/club/workspace").json()
    assert ws["club"]["slug"] == "meridian-fc"
    assert len(ws["roster"]) == 2
    assert ws["revenue_active"] == 0
    bad = clubu.post("/api/club/packages", json={
        "name": "Bad package", "package_type": "player_direct",
        "price_usd": 100, "athlete_slug": "kaia-mercer"})
    assert bad.status_code == 409  # not on roster


def test_package_backing_lifecycle(client, sponsor, clubu, fan):
    mfc = client.get("/api/clubs/meridian-fc").json()
    pd = next(p for p in mfc["packages"] if p["package_type"] == "player_direct")

    assert fan.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 403
    commit = sponsor.post(f"/api/clubs/packages/{pd['id']}/commit")
    assert commit.status_code == 201
    assert sponsor.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 409

    ws = clubu.get("/api/club/workspace").json()
    assert ws["revenue_active"] == pd["price_usd"]
    sws = sponsor.get("/api/sponsor/workspace").json()
    assert any(x["package_id"] == pd["id"] and x["status"] == "active"
               for x in sws["club_commitments"])
    assert sponsor.post(f"/api/commitments/{commit.json()['id']}/cancel").status_code == 200


def test_roster_removal_ends_commitments(client, sponsor, clubu):
    mfc = client.get("/api/clubs/meridian-fc").json()
    pd = next(p for p in mfc["packages"] if p["package_type"] == "player_direct")
    assert sponsor.post(f"/api/clubs/packages/{pd['id']}/commit").status_code == 201

    marcus = next(m for m in mfc["roster"] if m["slug"] == "marcus-oyelaran")
    removed = clubu.post(f"/api/club/members/{marcus['athlete_id']}/remove").json()
    assert removed["commitments_ended"] == 1
    ws = clubu.get("/api/club/workspace").json()
    assert ws["revenue_active"] == 0
    assert len(ws["roster"]) == 1


# ---- fan loop ----------------------------------------------------------------


def test_discovery_and_feed(fan):
    ranked = fan.get("/api/discover?interests=running,cycling&country=Germany").json()
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
    assert reg.post("/api/athlete/platforms/connect",
                    json={"platform": "instagram"}).status_code == 200
    ws = reg.get("/api/athlete/workspace").json()
    assert ws["analytics"] is not None


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
