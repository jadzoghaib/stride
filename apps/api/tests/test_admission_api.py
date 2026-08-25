"""Admission end to end: applications, club verification, nomination, revocation.

Where test_admission.py pins the arithmetic, this pins what the arithmetic is
allowed to *do* — which profiles become visible, whose word carries whom, and
what happens when a club that vouched for people turns out not to qualify.
"""

from __future__ import annotations

import pytest

from stride_api.admission import ADMIT_AT
from stride_api.db import now_iso, row, rows


@pytest.fixture(autouse=True)
def restore_directory(db, client):
    """Put the seeded directory back after each test.

    These tests deliberately move profiles in and out of the directory, which is
    the whole point of an admission gate — but the suite shares one seeded
    database, so leaving an athlete drafted would silently fail whichever test
    happens to run next.
    """
    before = {r["slug"]: r["status"] for r in rows(db, "SELECT slug, status FROM athlete_profiles")}
    yield
    db.execute("DELETE FROM athlete_applications")
    for slug, status in before.items():
        db.execute("UPDATE athlete_profiles SET status = ? WHERE slug = ?", (status, slug))
    db.commit()

STRONG_CLUB = {
    "legal_name": "Club Deportivo Vallès", "registration_id": "G-08123456",
    "federation_name": "Federació Catalana", "federation_id": "FCF-2211",
    "founded_year": 1974, "competition_level": "regional", "teams_count": 9,
    "registered_athletes": 3, "roster_url": "https://cdvalles.example/plantilla",
    "proof_kind": "roster",
}


@pytest.fixture()
def verified_club(clubu, admin, db, client):
    """A club that clears the gate. Proof is marked verified the way ops would,
    since nothing in this suite reaches the public internet."""
    assert clubu.post("/api/club/application", json=STRONG_CLUB).status_code == 201
    club = row(db, "SELECT * FROM clubs WHERE user_id = "
               "(SELECT id FROM users WHERE email = 'club@demo.stride')")
    db.execute("UPDATE club_applications SET proof_status = 'verified' WHERE club_id = ?",
               (club["id"],))
    db.commit()
    # re-submitting re-scores against the now-verified proof
    assert clubu.post("/api/club/application", json=STRONG_CLUB).status_code == 201
    db.execute("UPDATE club_applications SET proof_status = 'verified', decision = 'verified'"
               " WHERE club_id = ?", (club["id"],))
    db.commit()
    yield club
    db.execute("DELETE FROM athlete_applications WHERE nominated_by_club = ?", (club["id"],))
    db.execute("DELETE FROM club_applications WHERE club_id = ?", (club["id"],))
    db.commit()


def _application(db, slug="kaia-mercer"):
    return row(db, "SELECT ap.* FROM athlete_applications ap"
               " JOIN athlete_profiles a ON a.id = ap.athlete_id WHERE a.slug = ?", (slug,))


def test_a_complete_verified_application_is_admitted_and_listed(athlete, admin, db):
    res = athlete.post("/api/athlete/application", json={
        "competition_level": "national", "discipline": "800m", "club_name": "Bay Track",
        "league_name": "US Nationals", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://usatf.example/results/2026", "proof_kind": "results"})
    assert res.status_code == 201, res.text
    # submitted proof is queued, not trusted — so this is review, not admitted
    assert res.json()["decision"] == "review"

    application = _application(db)
    checked = admin.post(f"/api/admin/applications/{application['id']}/proof",
                         json={"proof_status": "verified"})
    assert checked.status_code == 200, checked.text
    assert checked.json()["decision"] == "admitted"
    # gate on legitimacy, tier on value: this athlete has analytics, so listed
    assert checked.json()["listing"] == "listed"
    assert row(db, "SELECT status FROM athlete_profiles WHERE slug = 'kaia-mercer'"
               )["status"] == "listed"


def test_the_applicant_can_read_the_decision_that_excluded_them(athlete):
    athlete.post("/api/athlete/application", json={
        "competition_level": "local", "years_competing": 1, "birth_year": 2004,
        "proof_kind": "none"})
    seen = athlete.get("/api/athlete/application").json()
    assert seen["application"]["decision"] in ("review", "rejected")
    # a gate whose result cannot be explained is a gate that cannot be appealed
    assert seen["scored"]["caveats"]
    assert seen["scored"]["evidence_multiplier"] == 0.25


def test_submitting_a_new_claim_invalidates_the_proof_already_checked(athlete, admin, db):
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://usatf.example/r", "proof_kind": "results"})
    application = _application(db)
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "verified"})
    assert _application(db)["proof_status"] == "verified"

    athlete.post("/api/athlete/application", json={
        "competition_level": "international", "years_competing": 9, "birth_year": 2002,
        "proof_url": "https://usatf.example/r", "proof_kind": "results"})
    # the link was checked against the old claim; it says nothing about the new one
    assert _application(db)["proof_status"] == "pending"


def test_an_unverified_club_cannot_nominate(clubu, db):
    club = row(db, "SELECT * FROM clubs WHERE user_id = "
               "(SELECT id FROM users WHERE email = 'club@demo.stride')")
    db.execute("DELETE FROM club_applications WHERE club_id = ?", (club["id"],))
    db.commit()
    res = clubu.post("/api/club/nominations", json={"athlete_slug": "sofia-brandt"})
    assert res.status_code == 403
    assert res.json()["detail"] == "club_not_verified"


def test_a_nomination_of_someone_who_filed_nothing_stays_pending(verified_club, clubu, db):
    """The fraud multiplier the design closes. If a nomination admitted outright,
    verifying one club would mint as many athletes as it liked; here each one
    still costs a completed form, including the date of birth no club can
    supply on someone else's behalf."""
    res = clubu.post("/api/club/nominations", json={"athlete_slug": "sofia-brandt"})
    assert res.status_code == 201, res.text
    assert res.json()["decision"] == "pending"
    assert res.json()["rule"] == "incomplete_application"
    # the club's word still moved the number — it just cannot finish the job
    assert res.json()["effective_credibility"] > 0


def test_a_nomination_is_bounded_by_the_roster_the_club_declared(verified_club, clubu, db):
    """Declared roster size is the nomination budget, which makes inflating it a
    checkable claim rather than free headroom."""
    for slug in ("sofia-brandt", "luca-ferreira", "noa-lindqvist"):
        assert clubu.post("/api/club/nominations",
                          json={"athlete_slug": slug}).status_code == 201
    res = clubu.post("/api/club/nominations", json={"athlete_slug": "amara-diallo"})
    assert res.status_code == 409
    assert res.json()["detail"] == "nomination_budget_exhausted"


def test_revoking_a_club_returns_only_the_athletes_who_depended_on_it(
        verified_club, clubu, admin, db):
    dependent, independent = "sofia-brandt", "luca-ferreira"
    for slug in (dependent, independent):
        assert clubu.post("/api/club/nominations",
                          json={"athlete_slug": slug}).status_code == 201

    # force the pair into the two states the cascade has to tell apart
    db.execute("UPDATE athlete_applications SET decision = 'admitted', credibility = 20.0,"
               " admitted_via = 'club_nomination' WHERE athlete_id ="
               " (SELECT id FROM athlete_profiles WHERE slug = ?)", (dependent,))
    db.execute("UPDATE athlete_applications SET decision = 'admitted', credibility = ?,"
               " admitted_via = 'club_nomination' WHERE athlete_id ="
               " (SELECT id FROM athlete_profiles WHERE slug = ?)", (ADMIT_AT + 10, independent))
    db.execute("UPDATE athlete_profiles SET status = 'listed' WHERE slug IN (?, ?)",
               (dependent, independent))
    db.commit()

    res = admin.post(f"/api/admin/clubs/{verified_club['id']}/revoke")
    assert res.status_code == 200, res.text
    assert res.json()["athletes_returned_to_review"] == 1

    # review, not rejected: losing your supporting evidence is not being caught lying
    assert _application(db, dependent)["decision"] == "review"
    assert _application(db, dependent)["decision_rule"] == "club_verification_revoked"
    assert row(db, "SELECT status FROM athlete_profiles WHERE slug = ?",
               (dependent,))["status"] == "draft"
    # the athlete who stood on their own is untouched
    assert _application(db, independent)["decision"] == "admitted"


def test_a_verified_only_campaign_sees_only_checked_athletes(sponsor, athlete, admin, db):
    """Brand-safety style requirements are filters, not weights: a strong
    audience fit must not be able to outscore a failed check."""
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://usatf.example/r", "proof_kind": "results"})
    application = _application(db)
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "verified"})

    strict = sponsor.post("/api/campaigns", json={
        "name": "Verified only brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_usd_min": 1000, "budget_usd_max": 20000, "target_countries": ["US"],
        "target_topics": ["running"], "require_verified_athletes": True}).json()
    open_brief = sponsor.post("/api/campaigns", json={
        "name": "Open brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_usd_min": 1000, "budget_usd_max": 20000, "target_countries": ["US"],
        "target_topics": ["running"]}).json()

    strict_matches = sponsor.get(f"/api/campaigns/{strict['id']}/matches").json()["matches"]
    open_slugs = {m["slug"] for m in
                  sponsor.get(f"/api/campaigns/{open_brief['id']}/matches").json()["matches"]}
    strict_slugs = {m["slug"] for m in strict_matches}
    assert strict_slugs == {"kaia-mercer"}
    assert strict_slugs < open_slugs

    # stated as an invariant rather than as a slug list: whatever the filter
    # returns, every one of them must actually be admitted on checked evidence.
    # A specific expected set only catches the leak somebody predicted.
    for match in strict_matches:
        application = _application(db, match["slug"])
        assert application is not None, f"{match['slug']} has no application at all"
        assert application["decision"] == "admitted"
        assert application["proof_status"] == "verified"


def test_matching_logs_the_slate_it_showed_not_just_the_count(sponsor, admin):
    """Offers alone are a biased sample. Without the candidate set behind them a
    later ranker has nothing to learn from and no way to be evaluated
    off-policy — and the missing candidates never come back."""
    campaign = sponsor.post("/api/campaigns", json={
        "name": "Slate brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_usd_min": 1000, "budget_usd_max": 20000, "target_countries": ["US"],
        "target_topics": ["running"]}).json()
    shown = sponsor.get(f"/api/campaigns/{campaign['id']}/matches").json()["matches"]

    logged = admin.get("/api/admin/events", params={"event_type": "matching.ran"}).json()
    entry = next(e for e in logged if e["object_id"] == campaign["id"])
    slate = entry["detail"]["slate"]
    assert len(slate) == len(shown)
    assert [s["rank"] for s in slate] == list(range(1, len(shown) + 1))
    assert slate[0]["athlete_id"] == shown[0]["athlete_id"]
    # the weights are logged with it: a label without the policy that produced
    # it cannot be compared against a label from a later policy
    assert entry["detail"]["model_version"] and entry["detail"]["weights"]
    assert "audience_fit" in slate[0]["components"]


def test_congestion_is_surfaced_rather_than_silently_reranked(sponsor, db):
    """The honest answer to the top athletes absorbing every offer. Telling the
    sponsor lets them choose; quietly reordering their results chooses for
    them."""
    athlete_id = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'noa-lindqvist'")["id"]
    campaign = sponsor.post("/api/campaigns", json={
        "name": "Congestion brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_usd_min": 1000, "budget_usd_max": 20000, "target_countries": ["DE"],
        "target_topics": ["cycling"]}).json()
    org_id = row(db, "SELECT id FROM sponsor_orgs WHERE user_id ="
                 " (SELECT id FROM users WHERE email = 'sponsor@demo.stride')")["id"]
    for _ in range(3):
        db.execute("INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_usd,"
                   " status, created_at) VALUES (?, ?, ?, 'social_post', 1000, 'offered', ?)",
                   (campaign["id"], org_id, athlete_id, now_iso()))
    db.commit()

    matches = sponsor.get(f"/api/campaigns/{campaign['id']}/matches").json()["matches"]
    congested = next(m for m in matches if m["athlete_id"] == athlete_id)
    assert congested["open_offers"] >= 3
    assert any("already waiting" in c for c in congested["caveats"])

    db.execute("DELETE FROM deals WHERE campaign_id = ?", (campaign["id"],))
    db.commit()


def test_a_rejected_proof_cannot_be_laundered_by_resubmitting(athlete, admin, db):
    """Found by the stress sweep. Ops checks a link, finds it does not support
    the claim, and marks it rejected — at which point re-submitting the form used
    to reset the status to `pending` and hand the applicant a clean slate. A
    failed check is a finding about the applicant, so only a reviewer clears it.
    """
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://forged.example/roster", "proof_kind": "roster"})
    application = _application(db)
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "rejected"})
    assert _application(db)["decision"] == "rejected"

    resubmitted = athlete.post("/api/athlete/application", json={
        "competition_level": "regional", "years_competing": 4, "birth_year": 2002,
        "proof_kind": "none"})
    assert _application(db)["proof_status"] == "rejected"
    assert resubmitted.json()["decision"] == "rejected"

    # The way back is through a reviewer, not through the form. Clearing the flag
    # does not admit anyone — it only stops the next submission being forced back
    # to `rejected`, so fresh evidence can be queued on its merits again.
    application = _application(db)
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "unverified"})
    retried = athlete.post("/api/athlete/application", json={
        "competition_level": "regional", "years_competing": 4, "birth_year": 2002,
        "proof_url": "https://fcf.example/plantilla", "proof_kind": "roster"})
    assert _application(db)["proof_status"] == "pending"
    assert retried.json()["decision"] == "review"
