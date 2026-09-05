"""A campaign can be corrected and closed; a sponsor can rename itself.

Both were write-once. A typo in a brief meant abandoning it and its measured
delivery, and an organisation that renamed itself had no way to say so while
its old name sat on every offer it had sent.
"""

from __future__ import annotations

import json

import pytest

from stride_api.db import row

BRIEF = {
    "name": "Autumn trials", "category": "Sportswear", "objective": "Reach trail runners",
    "deal_types": ["social_post"], "budget_eur_min": 1000, "budget_eur_max": 5000,
    "target_age_buckets": ["18-24"], "target_genders": ["female"],
    "target_countries": ["United Kingdom"], "target_topics": ["running"],
}


@pytest.fixture
def campaign(sponsor, db):
    made = sponsor.post("/api/campaigns", json=BRIEF)
    assert made.status_code == 201, made.text
    cid = made.json()["id"]
    yield made.json()
    db.execute("DELETE FROM deals WHERE campaign_id = ?", (cid,))
    db.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
    db.commit()


# ── editing a brief ──────────────────────────────────────────────────────────

def test_a_brief_can_be_corrected_without_losing_its_deals(sponsor, campaign, db):
    listed = row(db, "SELECT id FROM athlete_profiles WHERE status = 'listed' LIMIT 1")
    offer = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": listed["id"], "amount_eur": 1200, "deal_type": "social_post",
        "message": "before the edit"})
    assert offer.status_code == 201

    fixed = sponsor.put(f"/api/campaigns/{campaign['id']}",
                        json={**BRIEF, "name": "Autumn trials 2027", "budget_eur_max": 9000})
    assert fixed.status_code == 200
    assert fixed.json()["name"] == "Autumn trials 2027"
    assert fixed.json()["budget_eur_max"] == 9000
    assert row(db, "SELECT COUNT(*) AS n FROM deals WHERE campaign_id = ?",
               (campaign["id"],))["n"] == 1, "the offer under it survives the edit"


def test_retargeting_gets_a_new_target_so_old_snapshots_stay_true(sponsor, campaign, db):
    before = row(db, "SELECT sponsor_target_id FROM campaigns WHERE id = ?", (campaign["id"],))

    same_targeting = sponsor.put(f"/api/campaigns/{campaign['id']}", json={**BRIEF, "name": "Renamed only"})
    assert same_targeting.status_code == 200
    unchanged = row(db, "SELECT sponsor_target_id FROM campaigns WHERE id = ?", (campaign["id"],))
    assert unchanged["sponsor_target_id"] == before["sponsor_target_id"], \
        "a rename is not a retarget"

    retargeted = sponsor.put(f"/api/campaigns/{campaign['id']}",
                             json={**BRIEF, "target_countries": ["France", "Spain"]})
    assert retargeted.status_code == 200
    after = row(db, "SELECT sponsor_target_id, target_countries FROM campaigns WHERE id = ?",
                (campaign["id"],))
    assert after["sponsor_target_id"] != before["sponsor_target_id"], \
        "new brief, new target — a snapshot computed under the old one stays true"
    assert json.loads(after["target_countries"]) == ["France", "Spain"]


def test_a_brief_belongs_to_its_own_organization(sponsor, sponsor2, campaign):
    r = sponsor2.put(f"/api/campaigns/{campaign['id']}", json={**BRIEF, "name": "Not yours"})
    assert r.status_code == 404, "another org cannot even see it, let alone edit it"
    assert sponsor2.post(f"/api/campaigns/{campaign['id']}/status",
                         json={"status": "closed"}).status_code == 404


def test_an_impossible_budget_is_still_refused_on_edit(sponsor, campaign):
    r = sponsor.put(f"/api/campaigns/{campaign['id']}",
                    json={**BRIEF, "budget_eur_min": 9000, "budget_eur_max": 100})
    assert r.status_code == 422 and r.json()["detail"] == "budget_max_below_min"


# ── closing one ──────────────────────────────────────────────────────────────

def test_closing_stops_new_offers_and_keeps_the_history(sponsor, campaign, db):
    listed = row(db, "SELECT id FROM athlete_profiles WHERE status = 'listed' LIMIT 1")
    other = row(db, "SELECT id FROM athlete_profiles WHERE status = 'listed' AND id <> ? LIMIT 1",
                (listed["id"],))
    assert sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": listed["id"], "amount_eur": 1200, "deal_type": "social_post",
        "message": "while open"}).status_code == 201

    closed = sponsor.post(f"/api/campaigns/{campaign['id']}/status", json={"status": "closed"})
    assert closed.status_code == 200 and closed.json()["status"] == "closed"

    refused = sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": other["id"], "amount_eur": 1200, "deal_type": "social_post",
        "message": "after closing"})
    assert refused.status_code == 409 and refused.json()["detail"] == "campaign_not_active"
    assert row(db, "SELECT COUNT(*) AS n FROM deals WHERE campaign_id = ?",
               (campaign["id"],))["n"] == 1, "closing is not deleting"

    # and it can be reopened
    assert sponsor.post(f"/api/campaigns/{campaign['id']}/status",
                        json={"status": "active"}).status_code == 200
    assert sponsor.post(f"/api/campaigns/{campaign['id']}/offers", json={
        "athlete_id": other["id"], "amount_eur": 1200, "deal_type": "social_post",
        "message": "after reopening"}).status_code == 201


def test_only_the_two_real_statuses_are_accepted(sponsor, campaign):
    for bad in ("draft", "archived", "deleted", ""):
        assert sponsor.post(f"/api/campaigns/{campaign['id']}/status",
                            json={"status": bad}).status_code == 422


# ── the organisation itself ──────────────────────────────────────────────────

def test_a_sponsor_can_edit_its_own_details(sponsor, db):
    before = row(db, "SELECT * FROM sponsor_orgs WHERE name = 'Northwind Apparel'")
    try:
        r = sponsor.put("/api/sponsor/org", json={
            "name": "Northwind Group", "industry": "Outdoor", "regions": ["Europe"],
            "website": "https://northwind.example"})
        assert r.status_code == 200
        assert r.json()["name"] == "Northwind Group" and r.json()["regions"] == ["Europe"]
        assert sponsor.get("/api/sponsor/workspace").json()["org"]["name"] == "Northwind Group"
    finally:
        db.execute("UPDATE sponsor_orgs SET name = ?, industry = ?, website = ?, regions = ?"
                   " WHERE id = ?", (before["name"], before["industry"], before["website"],
                                     before["regions"], before["id"]))
        db.commit()


def test_a_website_has_to_be_a_url(sponsor):
    r = sponsor.put("/api/sponsor/org", json={"name": "Northwind Apparel",
                                              "website": "javascript:alert(1)"})
    assert r.status_code == 422 and r.json()["detail"] == "website_must_be_a_url"


def test_the_org_routes_are_the_sponsor_role_only(athlete, clubu, fan, client, campaign):
    for who in (athlete, clubu, fan):
        assert who.put("/api/sponsor/org", json={"name": "Hijack"}).status_code == 403
        assert who.put(f"/api/campaigns/{campaign['id']}", json=BRIEF).status_code == 403
    assert client.put("/api/sponsor/org", json={"name": "Hijack"}).status_code == 401


def test_two_campaigns_can_share_a_name(sponsor, db):
    """The target name was built from `now_iso()` -- second resolution -- so
    two campaigns named the same within one second collided on
    `sponsor_targets.name` and the sponsor got a 500. A double-clicked
    "Create campaign" was enough."""
    made = [sponsor.post("/api/campaigns", json={**BRIEF, "name": "Same name twice"})
            for _ in range(3)]
    try:
        assert [r.status_code for r in made] == [201, 201, 201], [r.text[:80] for r in made]
        assert len({r.json()["id"] for r in made}) == 3
    finally:
        for r in made:
            if r.status_code == 201:
                db.execute("DELETE FROM campaigns WHERE id = ?", (r.json()["id"],))
        db.commit()
