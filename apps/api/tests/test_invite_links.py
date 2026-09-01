"""Club invite links: what they replace, and what they deliberately do not.

A verified club can onboard its own athletes without each one waiting in the
proof queue. The link says "this person is ours", which is what a reviewer
would have been checking on a roster page, so it stands in for **the proof
check**.

It is not a bypass of admission, and the tests that matter here are the ones
that prove it: the athlete still supplies their own age, and the 16+ gate still
refuses them, because a club cannot know or assert somebody else's date of
birth. Nothing about a link makes minting athletes free either -- links are
single-use and bounded by the roster the club declared.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows

STRONG_CLUB = {
    "legal_name": "Meridian Football Club Ltd", "registration_id": "09823117",
    "federation_name": "London FA", "federation_id": "LFA-4471",
    "founded_year": 1968, "competition_level": "regional", "teams_count": 7,
    "registered_athletes": 24, "roster_url": "https://meridianfc.example/first-team",
    "proof_kind": "roster",
}


@pytest.fixture(autouse=True)
def clean_slate(db):
    def snapshot(table):
        return {r["id"]: dict(r) for r in rows(db, f"SELECT * FROM {table}")}

    def restore(table, saved):
        if saved:
            keep = tuple(saved)
            db.execute(f"DELETE FROM {table} WHERE id NOT IN"
                       f" ({', '.join('?' for _ in keep)})", keep)
        else:
            db.execute(f"DELETE FROM {table}")
        for row_id, saved_row in saved.items():
            cols = [c for c in saved_row if c != "id"]
            db.execute(f"UPDATE {table} SET {', '.join(f'{c} = ?' for c in cols)} WHERE id = ?",
                       tuple(saved_row[c] for c in cols) + (row_id,))

    # club_applications too: verifying Meridian is how these tests reach the
    # feature, and leaving it verified makes "an unverified club cannot" pass
    # or fail on test order rather than on the rule.
    tables = ("club_invite_links", "athlete_applications", "notifications",
              "athlete_profiles", "club_applications")
    before = {t: snapshot(t) for t in tables}
    yield
    for table in tables:
        restore(table, before[table])
    db.commit()


def _verify_club(db, admin, clubu):
    """Put Meridian through club verification, which links require."""
    clubu.post("/api/club/application", json=STRONG_CLUB)
    club = row(db, "SELECT id FROM clubs WHERE slug = 'meridian-fc'")
    admin.post(f"/api/admin/clubs/{club['id']}/proof", json={"proof_status": "verified"})
    return club


def _issue(clubu):
    made = clubu.post("/api/club/invite-links")
    assert made.status_code == 201, made.text
    return made.json()["token"]


CLAIM = {"competition_level": "national", "years_competing": 6, "birth_year": 1999}


# -- what a link replaces ----------------------------------------------------

def test_a_link_admits_without_anyone_opening_a_proof_page(db, admin, clubu, athlete2):
    """The club is the evidence, so there is no reviewer step."""
    _verify_club(db, admin, clubu)
    verdict = athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)
    assert verdict.status_code == 200, verdict.text
    assert verdict.json()["decision"] == "admitted"

    application = row(db, "SELECT * FROM athlete_applications ap JOIN athlete_profiles a"
                          " ON a.id = ap.athlete_id WHERE a.slug = 'sofia-brandt'")
    assert application["proof_status"] == "verified", "the club supplied the proof half"
    assert application["nominated_by_club"] is not None


def test_an_unverified_club_cannot_issue_links(db, clubu):
    """The whole value of a link is the club's own verification standing behind
    it, so a club without one has nothing to lend.

    The precondition is set here rather than inherited: another test file
    verifies this same club and does not put it back, so relying on the seeded
    state made this pass or fail on which files ran first.
    """
    db.execute("UPDATE club_applications SET decision = 'review' WHERE club_id ="
               " (SELECT id FROM clubs WHERE slug = 'meridian-fc')")
    db.commit()
    res = clubu.post("/api/club/invite-links")
    assert res.status_code == 403
    assert res.json()["detail"] == "club_not_verified"


# -- what a link does not replace --------------------------------------------

def test_a_link_does_not_clear_the_age_gate(db, admin, clubu, athlete2):
    """The one rule a third party must never be able to clear on somebody
    else's behalf. A club cannot know an athlete's date of birth, so a link
    cannot assert it."""
    _verify_club(db, admin, clubu)
    verdict = athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem",
                            json={**CLAIM, "birth_year": 2012})
    assert verdict.status_code == 200
    assert verdict.json()["rule"] == "under_minimum_age"
    assert verdict.json()["listing"] == "draft"


def test_a_link_is_single_use(db, admin, clubu, athlete2):
    _verify_club(db, admin, clubu)
    token = _issue(clubu)
    assert athlete2.post(f"/api/athlete/invite-links/{token}/redeem", json=CLAIM).status_code == 200
    again = athlete2.post(f"/api/athlete/invite-links/{token}/redeem", json=CLAIM)
    assert again.status_code == 409
    assert again.json()["detail"] == "link_redeemed"


def test_links_are_bounded_by_the_roster_the_club_declared(db, admin, clubu):
    """Otherwise a verified club is an unlimited supply of admitted athletes,
    and the declared roster size stops being a checkable claim."""
    club = _verify_club(db, admin, clubu)
    db.execute("UPDATE club_applications SET registered_athletes = 2 WHERE club_id = ?",
               (club["id"],))
    db.commit()

    assert clubu.post("/api/club/invite-links").status_code == 201
    assert clubu.post("/api/club/invite-links").status_code == 201
    third = clubu.post("/api/club/invite-links")
    assert third.status_code == 409
    assert third.json()["detail"] == "roster_budget_exhausted"


def test_an_unknown_token_is_a_404(athlete2):
    assert athlete2.post("/api/athlete/invite-links/not-a-real-token/redeem",
                         json=CLAIM).status_code == 404


# -- revoking, and the two ways back -----------------------------------------

def test_revoking_freezes_the_athlete_it_admitted(db, admin, clubu, athlete2):
    """The club is the only evidence behind this listing. Withdrawing it has to
    take the listing with it, or a club could onboard anybody, walk away, and
    leave a profile standing on nothing."""
    _verify_club(db, admin, clubu)
    athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)

    link = row(db, "SELECT * FROM club_invite_links ORDER BY id DESC LIMIT 1")
    revoked = clubu.post(f"/api/club/invite-links/{link['id']}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["froze"] == "sofia-brandt"

    profile = row(db, "SELECT * FROM athlete_profiles WHERE slug = 'sofia-brandt'")
    assert profile["frozen_at"] is not None
    assert profile["status"] == "draft"

    frozen_view = athlete2.get("/api/athlete/application").json()
    assert frozen_view["frozen"]["club"] == "Meridian FC", "and they are told who, and why"


def test_a_freeze_survives_re_evaluation(db, admin, clubu, athlete2):
    """Re-running the scorer must not quietly undo a club's withdrawal."""
    _verify_club(db, admin, clubu)
    athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)
    link = row(db, "SELECT * FROM club_invite_links ORDER BY id DESC LIMIT 1")
    clubu.post(f"/api/club/invite-links/{link['id']}/revoke")

    again = athlete2.post("/api/athlete/application", json={
        **CLAIM, "proof_kind": "results", "proof_url": "https://athletics.example/r"})
    assert again.json()["listing"] == "draft", "still frozen"


def test_a_new_link_thaws_them(db, admin, clubu, athlete2):
    """The first of the two ways back: another club vouches."""
    _verify_club(db, admin, clubu)
    athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)
    link = row(db, "SELECT * FROM club_invite_links ORDER BY id DESC LIMIT 1")
    clubu.post(f"/api/club/invite-links/{link['id']}/revoke")

    athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)
    profile = row(db, "SELECT * FROM athlete_profiles WHERE slug = 'sofia-brandt'")
    assert profile["frozen_at"] is None


def test_a_verified_proof_thaws_them(db, admin, clubu, athlete2):
    """The second: they go through the ordinary gate on their own evidence."""
    _verify_club(db, admin, clubu)
    athlete2.post(f"/api/athlete/invite-links/{_issue(clubu)}/redeem", json=CLAIM)
    link = row(db, "SELECT * FROM club_invite_links ORDER BY id DESC LIMIT 1")
    clubu.post(f"/api/club/invite-links/{link['id']}/revoke")

    athlete2.post("/api/athlete/application", json={
        **CLAIM, "proof_kind": "results", "proof_url": "https://athletics.example/results"})
    application = row(db, "SELECT ap.id FROM athlete_applications ap JOIN athlete_profiles a"
                          " ON a.id = ap.athlete_id WHERE a.slug = 'sofia-brandt'")
    admin.post(f"/api/admin/applications/{application['id']}/proof",
               json={"proof_status": "verified"})

    profile = row(db, "SELECT * FROM athlete_profiles WHERE slug = 'sofia-brandt'")
    assert profile["frozen_at"] is None


def test_a_club_cannot_revoke_another_clubs_link(db, admin, clubu, athlete2):
    _verify_club(db, admin, clubu)
    _issue(clubu)
    link = row(db, "SELECT * FROM club_invite_links ORDER BY id DESC LIMIT 1")
    db.execute("UPDATE club_invite_links SET club_id ="
               " (SELECT id FROM clubs WHERE slug = 'ironline-combat') WHERE id = ?",
               (link["id"],))
    db.commit()
    assert clubu.post(f"/api/club/invite-links/{link['id']}/revoke").status_code == 404


# ---- the directory invariant -------------------------------------------------


def test_every_listed_club_is_a_verified_club(db):
    """**Listed implies verified**, and the seed has to obey it too.

    Meridian used to be seeded `listed` with a `pending` application, so it
    appeared in the public directory beside a verified club while telling its
    own owner it was not verified yet -- two different answers to the same
    question depending on who asked. An applicant is a club that is not listed;
    that is what `draft` is for.
    """
    from stride_api.db import rows
    bad = rows(db, """
        SELECT c.slug FROM clubs c
        LEFT JOIN club_applications a ON a.club_id = c.id
        WHERE c.status = 'listed'
          AND (a.proof_status IS NULL OR a.proof_status <> 'verified')""")
    assert bad == [], f"listed but unverified: {[r['slug'] for r in bad]}"


def test_the_review_queue_still_has_a_club_to_decide_on(db):
    """Verifying both demo clubs must not empty the admin queue -- the applicant
    is a draft club, which is the state an unreviewed club is actually in."""
    from stride_api.db import rows
    waiting = rows(db, """
        SELECT c.slug, c.status FROM clubs c
        JOIN club_applications a ON a.club_id = c.id
        WHERE a.proof_status = 'pending'""")
    assert waiting, "no club left for the review queue"
    assert all(r["status"] == "draft" for r in waiting), \
        "a club awaiting review must not be listed"
