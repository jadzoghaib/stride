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
        "budget_eur_min": 1000, "budget_eur_max": 20000, "target_countries": ["US"],
        "target_topics": ["running"], "require_verified_athletes": True}).json()
    open_brief = sponsor.post("/api/campaigns", json={
        "name": "Open brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_eur_min": 1000, "budget_eur_max": 20000, "target_countries": ["US"],
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


def test_matching_records_the_slate_once_per_exposure_and_only_on_intent(sponsor, admin):
    """Offers alone are a biased sample. Without the candidate set behind them a
    later ranker has nothing to learn from and no way to be evaluated
    off-policy — and the missing candidates never come back.

    Reading the ranking is not an exposure, though. This used to log and commit
    on every GET, so a sponsor refreshing the page manufactured duplicate
    training rows; recording is now an explicit POST, idempotent on the slate's
    own fingerprint so that re-opening an unchanged ranking is not counted twice.
    """
    campaign = sponsor.post("/api/campaigns", json={
        "name": "Slate brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_eur_min": 1000, "budget_eur_max": 20000, "target_countries": ["US"],
        "target_topics": ["running"]}).json()

    def slates():
        return [e for e in admin.get("/api/admin/events",
                                     params={"event_type": "matching.ran"}).json()
                if e["object_id"] == campaign["id"]]

    # reading it twice writes nothing
    first = sponsor.get(f"/api/campaigns/{campaign['id']}/matches").json()
    sponsor.get(f"/api/campaigns/{campaign['id']}/matches")
    assert slates() == []
    assert first["duration_ms"] >= 0 and first["slate_id"]

    recorded = sponsor.post(f"/api/campaigns/{campaign['id']}/matches").json()
    assert recorded["recorded"] is True
    assert len(slates()) == 1

    # the same ranking again is the same exposure, not a new one
    again = sponsor.post(f"/api/campaigns/{campaign['id']}/matches").json()
    assert again["recorded"] is False
    assert again["slate_id"] == recorded["slate_id"]
    assert len(slates()) == 1

    detail = slates()[0]["detail"]
    shown = recorded["matches"]
    assert detail["duration_ms"] >= 0
    assert detail["model_version"] and detail["weights"]
    assert len(detail["slate"]) == recorded["ranked_total"] > len(shown),         "the whole ranking is recorded, not only the page that was rendered"
    assert [s["rank"] for s in detail["slate"]] == list(range(1, len(detail["slate"]) + 1))
    assert "audience_fit" in detail["slate"][0]["components"]

    # everything past the fold is the negatives, kept cheap
    tail = detail["slate"][len(shown):]
    assert tail and all(e["truncated"] and "components" not in e for e in tail)


def test_congestion_is_surfaced_rather_than_silently_reranked(sponsor, db):
    """The honest answer to the top athletes absorbing every offer. Telling the
    sponsor lets them choose; quietly reordering their results chooses for
    them."""
    athlete_id = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'noa-lindqvist'")["id"]
    campaign = sponsor.post("/api/campaigns", json={
        "name": "Congestion brief", "category": "Sportswear", "deal_types": ["social_post"],
        "budget_eur_min": 1000, "budget_eur_max": 20000, "target_countries": ["DE"],
        "target_topics": ["cycling"]}).json()
    org_id = row(db, "SELECT id FROM sponsor_orgs WHERE user_id ="
                 " (SELECT id FROM users WHERE email = 'sponsor@demo.stride')")["id"]
    for _ in range(3):
        db.execute("INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_eur,"
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


def test_the_club_queue_is_navigable(clubu, admin, db):
    """Building the review interface is what exposed this: an admin could record
    a check against a club but had no way to find which clubs were waiting for
    one. An endpoint nobody can navigate to is a workflow that does not exist.
    """
    assert clubu.post("/api/club/application", json=STRONG_CLUB).status_code == 201
    queued = admin.get("/api/admin/club-queue", params={"decision": "review"}).json()
    mine = next(c for c in queued if c["name"])
    assert mine["scored"]["legitimacy"] > 0
    assert mine["roster_url"]                 # there is something to open
    assert mine["club_id"]                    # and somewhere to record the answer

    before = db.execute("SELECT proof_status, legitimacy, decision, policy_version,"
                        " decided_at FROM club_applications WHERE club_id = ?",
                        (mine["club_id"],)).fetchone()
    # The database is session-scoped, so verifying this club is a change every
    # later test inherits — including the ones that count verified clubs. The
    # restore has to be in a `finally`: a cleanup that only runs when every
    # assertion passed is a cleanup for the case that did not need it.
    try:
        checked = admin.post(f"/api/admin/clubs/{mine['club_id']}/proof",
                             json={"proof_status": "verified"})
        assert checked.status_code == 200
        assert checked.json()["decision"] == "verified"
        assert not [c for c in admin.get("/api/admin/club-queue").json()
                    if c["club_id"] == mine["club_id"]]
    finally:
        # Named, not `tuple(before)`: sqlite3.Row iterates its values and
        # psycopg's dict_row iterates its *keys*, so the tuple form silently
        # bound the column names as values on Postgres.
        db.execute("UPDATE club_applications SET proof_status = ?, legitimacy = ?,"
                   " decision = ?, policy_version = ?, decided_at = ? WHERE club_id = ?",
                   (before["proof_status"], before["legitimacy"], before["decision"],
                    before["policy_version"], before["decided_at"], mine["club_id"]))
        db.commit()


def test_a_proof_that_does_not_exist_cannot_be_marked_checked(athlete, admin, db):
    """`verified` means somebody opened a link and saw the applicant's name on
    it. With no link there is nothing to open, so the status must be
    unreachable — otherwise a high-scoring claim is admitted on a check that
    never happened, which is the hole the evidence multiplier exists to close.
    """
    athlete.post("/api/athlete/application", json={
        "competition_level": "international", "years_competing": 10,
        "birth_year": 1998, "proof_kind": "none"})
    application = _application(db)
    assert not application["proof_url"]

    refused = admin.post(f"/api/admin/applications/{application['id']}/proof",
                         json={"proof_status": "verified"})
    assert refused.status_code == 409
    assert refused.json()["detail"] == "no_proof_to_check"
    assert _application(db)["decision"] != "admitted"


def test_verified_clubs_are_listed_so_revocation_is_reachable(clubu, admin, db):
    """Revocation only ever applies to a club that IS verified, and the review
    queue by definition contains none. Listing only the queue left the one
    control that can undo a verification rendered for nobody."""
    assert clubu.post("/api/club/application", json=STRONG_CLUB).status_code == 201
    club = row(db, "SELECT * FROM clubs WHERE user_id = "
               "(SELECT id FROM users WHERE email = 'club@demo.stride')")
    admin.post(f"/api/admin/clubs/{club['id']}/proof", json={"proof_status": "verified"})

    waiting = admin.get("/api/admin/club-queue", params={"decision": "review"}).json()
    verified = admin.get("/api/admin/club-queue", params={"decision": "verified"}).json()
    assert club["id"] not in [c["club_id"] for c in waiting]
    assert club["id"] in [c["club_id"] for c in verified]
    assert next(c for c in verified if c["club_id"] == club["id"])["scored"]["nomination_floor"] > 0


# ── auto-verification, end to end ───────────────────────────────────────────

def test_auto_check_verifies_a_real_roster_and_admits(athlete, admin, db, monkeypatch):
    """The queue exists because nobody had opened the link. When the name is
    plainly on the page there is nothing for a human to decide."""
    from stride_api import proofcheck

    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://baytrack.example/roster", "proof_kind": "roster"})
    application = _application(db)
    assert application["decision"] == "review"

    monkeypatch.setattr(proofcheck, "fetch",
                        lambda url: ("<li>7 — Kaia Mercer — 800m</li>", "ok"))
    res = admin.post(f"/api/admin/applications/{application['id']}/auto-check")
    assert res.status_code == 200, res.text
    assert res.json()["checked"] is True
    assert res.json()["decision"] == "admitted"
    assert _application(db)["proof_status"] == "verified"


def test_auto_check_leaves_an_absent_name_for_a_human(athlete, admin, db, monkeypatch):
    from stride_api import proofcheck
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://baytrack.example/roster", "proof_kind": "roster"})
    application = _application(db)

    monkeypatch.setattr(proofcheck, "fetch", lambda url: ("<p>Somebody else</p>", "ok"))
    res = admin.post(f"/api/admin/applications/{application['id']}/auto-check").json()
    assert res["checked"] is False and res["reason"] == "name_not_found"
    assert _application(db)["decision"] == "review"
    assert _application(db)["proof_status"] == "pending"


def test_a_fetch_that_fails_never_admits_anybody(athlete, admin, db, monkeypatch):
    """Silence is not consent. A timeout leaves the application exactly where
    it was rather than resolving it in the applicant's favour."""
    from stride_api import proofcheck
    athlete.post("/api/athlete/application", json={
        "competition_level": "international", "years_competing": 10, "birth_year": 1998,
        "proof_url": "https://unreachable.example/roster", "proof_kind": "roster"})
    application = _application(db)

    monkeypatch.setattr(proofcheck, "fetch", lambda url: (None, "timeout"))
    res = admin.post(f"/api/admin/applications/{application['id']}/auto-check").json()
    assert res["checked"] is False and res["reason"] == "timeout"
    assert _application(db)["decision"] != "admitted"


def test_a_crawler_cannot_clear_a_rejected_proof(athlete, admin, db, monkeypatch):
    """A failed check is a finding about the applicant. Only a reviewer clears
    it — otherwise re-running the sweep launders it."""
    from stride_api import proofcheck
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://forged.example/roster", "proof_kind": "roster"})
    application = _application(db)
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "rejected"})

    monkeypatch.setattr(proofcheck, "fetch",
                        lambda url: ("<li>Kaia Mercer</li>", "ok"))
    res = admin.post(f"/api/admin/applications/{application['id']}/auto-check")
    assert res.status_code == 409
    assert _application(db)["proof_status"] == "rejected"


def test_admission_speed_counts_the_applications_still_waiting(athlete, admin, db):
    """The same anti-survivorship rule the sponsor speed tile follows: a median
    over the ones that got through reads fastest exactly when the queue is worst,
    so the ones still in it are reported beside it."""
    athlete.post("/api/athlete/application", json={
        "competition_level": "regional", "years_competing": 4, "birth_year": 2002,
        "proof_url": "https://club.example/roster", "proof_kind": "roster"})

    speed = admin.get("/api/admin/admission-speed").json()
    assert speed["still_waiting"] >= 1
    assert speed["decided"] >= 1
    assert speed["median_hours_to_decision"] is not None
    assert speed["median_hours_to_decision"] >= 0
    # nothing has been admitted in this fixture, and that reads as None
    assert "median_hours_to_listed" in speed
    assert "waiting_on_an_unopened_link" in speed


def test_a_bare_scheme_cannot_be_marked_checked(athlete, admin, db):
    """The guard was "non-empty", which `http://` satisfies. There is nothing at
    that address for a reviewer to have opened."""
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "http://", "proof_kind": "roster"})
    application = _application(db)
    refused = admin.post(f"/api/admin/applications/{application['id']}/proof",
                         json={"proof_status": "verified"})
    assert refused.status_code == 409
    assert refused.json()["detail"] == "no_proof_to_check"


def test_applying_does_not_cost_an_athlete_the_listing_they_already_had(athlete, admin, db):
    """Found by a friend clicking through the demo: Kaia was Listed, he
    submitted the eligibility form, and she was Draft when he got back to the
    profile — out of matching, with nothing said about it.

    The seeded directory predates the gate on purpose (see the router
    docstring), and that grandfathering used to evaporate the moment such an
    athlete engaged with the gate. A weak claim leaves them un-admitted, which
    is right; it must not also take away what they had before they asked.
    """
    def status():
        return row(db, "SELECT status FROM athlete_profiles WHERE slug = 'kaia-mercer'")["status"]

    assert status() == "listed", "this test starts from a grandfathered listing"
    weak = {"competition_level": "local", "years_competing": 1, "birth_year": 2004,
            "proof_kind": "none", "proof_url": ""}

    first = athlete.post("/api/athlete/application", json=weak)
    assert first.status_code == 201, first.text
    assert first.json()["decision"] != "admitted"
    assert first.json()["listing"] == "listed"
    assert status() == "listed"

    # and again: keying this to "no application yet" would spring the same trap
    # on the second save, which is worse than the original bug because it waits
    assert athlete.post("/api/athlete/application", json=weak).json()["listing"] == "listed"
    assert status() == "listed"


def test_but_a_listing_the_gate_granted_can_be_lost_by_weakening_the_claim(athlete, admin, db):
    """The other half. Grandfathering protects standing that predates the gate;
    it must not protect a listing the gate itself granted, or editing your
    application down would be a free way to keep one it no longer supports."""
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://usatf.example/results/2026", "proof_kind": "results"})
    application = _application(db)
    admitted = admin.post(f"/api/admin/applications/{application['id']}/proof",
                          json={"proof_status": "verified"})
    assert admitted.json()["decision"] == "admitted"
    assert _application(db)["admitted_via"] == "self"

    # now withdraw the evidence the admission rested on
    weakened = athlete.post("/api/athlete/application", json={
        "competition_level": "local", "years_competing": 1, "birth_year": 2004,
        "proof_kind": "none", "proof_url": ""})
    assert weakened.json()["decision"] != "admitted"
    assert weakened.json()["listing"] == "draft"
    assert row(db, "SELECT status FROM athlete_profiles WHERE slug = 'kaia-mercer'"
               )["status"] == "draft"


def test_a_reviewer_cannot_delist_a_pre_gate_listing_by_finding_nothing(athlete, admin, db):
    """The grandfathering rule was applied at one call site out of three.

    It held when the athlete touched their own form and evaporated when a
    reviewer touched it: `set_proof` and the auto-checker still delisted a
    profile whose listing predates the gate. An inconclusive check is an absence
    of evidence, and it must not cost somebody standing they were granted before
    any of this existed.
    """
    def status():
        return row(db, "SELECT status FROM athlete_profiles WHERE slug = 'kaia-mercer'")["status"]

    assert status() == "listed"
    athlete.post("/api/athlete/application", json={
        "competition_level": "local", "years_competing": 1, "birth_year": 2004,
        "proof_url": "https://club.example/roster", "proof_kind": "roster"})
    assert status() == "listed"

    application = _application(db)
    checked = admin.post(f"/api/admin/applications/{application['id']}/proof",
                         json={"proof_status": "unverified"})
    assert checked.status_code == 200, checked.text
    assert checked.json()["decision"] != "admitted"
    assert checked.json()["listing"] == "listed", "an inconclusive check is not a finding"
    assert status() == "listed"


def test_but_a_rejected_proof_delists_even_a_pre_gate_listing(athlete, admin, db):
    """The exception that makes the rule safe. A rejection is somebody looking
    and finding the claim did not stand up — a finding about the applicant,
    which outranks anything they were grandfathered into."""
    athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 6, "birth_year": 2002,
        "proof_url": "https://usatf.example/r", "proof_kind": "results"})
    application = _application(db)
    rejected = admin.post(f"/api/admin/applications/{application['id']}/proof",
                          json={"proof_status": "rejected"})
    assert rejected.json()["decision"] == "rejected"
    assert rejected.json()["listing"] == "draft"
    assert row(db, "SELECT status FROM athlete_profiles WHERE slug = 'kaia-mercer'"
               )["status"] == "draft"
