"""Admission: who gets in, on what evidence, and what a club's word is worth.

The properties pinned here are the ones the policy exists to guarantee. Each is
a thing that a compensatory `A = 0.6*C + 0.4*S` gate gets wrong, so each is
written as the counter-example rather than as a range check on a number.
"""

from __future__ import annotations

from stride_api.admission import (ADMIT_AT, admission_decision, athlete_credibility,
                                  club_legitimacy, nomination_floor, tenure_value)

YEAR = 2026


def score(**kw) -> dict:
    application = dict(sport="football", competition_level="regional", years_competing=3,
                       birth_year=2006, proof_kind="roster", proof_status="verified",
                       proof_url="https://club.example/roster")
    application.update(kw)
    return athlete_credibility(application, today_year=YEAR)


def decide(application_overrides=None, **decision_kw) -> dict:
    application = dict(sport="football", competition_level="regional", years_competing=3,
                       birth_year=2006, proof_kind="roster", proof_status="verified",
                       proof_url="https://club.example/roster")
    application.update(application_overrides or {})
    scored = athlete_credibility(application, today_year=YEAR)
    kw = {"proof_status": application["proof_status"],
          "age": YEAR - application["birth_year"] if application["birth_year"] else None,
          "scoreable": scored["scoreable"]}
    kw.update(decision_kw)
    return admission_decision(scored["credibility"], **kw)


# ── the failure the whole design exists to prevent ──────────────────────────

def test_a_large_following_cannot_buy_its_way_in():
    """The counter-example to blending credibility with the social score.

    A fitness influencer with a 95 social score and a self-declared local club
    and no proof clears `A = 0.6C + 0.4S` at 62. Here they are rejected, because
    reach is not evidence of competing — which is the entire promise the product
    makes to sponsors.
    """
    result = decide({"competition_level": "local", "years_competing": 5,
                     "birth_year": 2000, "proof_kind": "none",
                     "proof_status": "unverified"},
                    social_score=95.0)
    assert result["decision"] == "rejected"


def test_the_social_score_can_route_to_review_but_never_to_admitted():
    """Its only permitted direction is towards a human. An athlete with real
    reach and bad paperwork deserves eyes; nobody deserves an auto-admit for
    being popular."""
    weak = {"competition_level": "regional", "proof_status": "unverified"}
    without = decide(weak, social_score=None)
    with_reach = decide(weak, social_score=95.0)
    # both land in the review band on credibility alone — the point is that the
    # social score did not lift the second one past it
    assert without["decision"] == with_reach["decision"] == "review"
    assert with_reach["effective_credibility"] == without["effective_credibility"]

    # and where it does act, it acts downward-only: into review, never past it
    rescued = admission_decision(30.0, proof_status="unverified", social_score=95.0, age=24)
    assert rescued["decision"] == "review"


def test_no_unevidenced_claim_of_any_size_is_admitted():
    """Evidence multiplies rather than adds, so the largest possible claim with
    nothing behind it still cannot clear the gate. Under an additive rubric this
    application scores 85+ and walks in."""
    result = decide({"competition_level": "international", "years_competing": 10,
                     "birth_year": 1998, "proof_kind": "none",
                     "proof_status": "unverified"})
    assert result["decision"] == "rejected"
    assert score(competition_level="international", years_competing=10, birth_year=1998,
                 proof_kind="none")["credibility"] < 25


def test_verified_modesty_beats_unverified_grandeur():
    """A checked regional claim outranks an unchecked international one. Under
    an additive rubric the ordering inverts, which is the wrong incentive to put
    in front of an applicant."""
    modest = score(competition_level="regional", proof_status="verified")["credibility"]
    grand = score(competition_level="international", proof_status="unverified")["credibility"]
    assert modest > grand


# ── withholding must never pay ──────────────────────────────────────────────

def test_leaving_the_competition_level_blank_does_not_score_at_all():
    """Renormalising over missing self-reported fields would hand level's whole
    weight to tenure and produce a perfect 100 for an empty form. An unanswerable
    application is a queue item, not a pass."""
    blank = score(competition_level="", years_competing=8)
    assert blank["scoreable"] is False
    assert blank["credibility"] == 0.0
    incomplete = decide({"competition_level": "", "years_competing": 8})
    assert incomplete["rule"] == "incomplete_application"
    # `pending`, not `review`: see the regression test below for why that matters
    assert incomplete["decision"] == "pending"


def test_withholding_seasons_competed_lowers_the_score_it_does_not_raise_it():
    supplied = score(years_competing=3)["credibility"]
    withheld = score(years_competing=None)["credibility"]
    assert withheld < supplied


def test_a_club_withholding_its_history_scores_below_one_that_supplies_it():
    full = dict(registration_id="G1", federation_name="RFEF", federation_id="ES-1",
                founded_year=1990, teams_count=8, roster_url="https://c/r",
                proof_kind="roster", proof_status="verified")
    partial = full | {"founded_year": None, "teams_count": None}
    assert (club_legitimacy(partial, today_year=YEAR)["legitimacy"]
            < club_legitimacy(full, today_year=YEAR)["legitimacy"])


# ── the ladder is read against its own sport ────────────────────────────────

def test_the_same_label_is_worth_more_in_a_sport_with_no_agents():
    """"Regional" in football sits under several professional tiers; in padel it
    is near the competitive ceiling. A flat ladder mis-ranks both."""
    assert (score(sport="padel")["credibility"]
            > score(sport="football")["credibility"])


def test_an_unlisted_sport_falls_back_to_neutral_rather_than_to_a_hole():
    assert score(sport="korfball")["scoreable"] is True
    assert score(sport="korfball")["credibility"] > 0


# ── age ─────────────────────────────────────────────────────────────────────

def test_tenure_does_not_punish_the_sixteen_year_olds_the_platform_wants():
    """Raw years is an age proxy. Eight seasons is full marks whether you are 16
    or 30 — see business-plan/05-product-gaps.md on the under-18 cohort."""
    assert tenure_value(8, 2010, YEAR) == tenure_value(8, 1996, YEAR) == 1.0
    # below full marks, the young are credited on share of an inevitably shorter
    # career, so four seasons is worth more at 16 than at 30 — never less
    young, adult = tenure_value(4, 2010, YEAR), tenure_value(4, 1996, YEAR)
    assert young > adult
    assert adult == 4 / 8  # the adult still gets the absolute reading, not a penalty


def test_under_sixteen_is_refused_whatever_the_credibility():
    result = decide({"birth_year": YEAR - 15, "competition_level": "international",
                     "years_competing": 8})
    assert result["decision"] == "rejected"
    assert result["rule"] == "under_minimum_age"


def test_an_unstated_date_of_birth_cannot_auto_admit():
    """The age gate is a legal obligation, and it cannot be cleared by silence."""
    result = decide({"birth_year": None, "competition_level": "national",
                     "years_competing": 8})
    assert result["decision"] == "review"


# ── clubs ───────────────────────────────────────────────────────────────────

def test_only_a_verified_club_confers_anything():
    assert nomination_floor(80.0, "review") == 0.0
    assert nomination_floor(80.0, "rejected") == 0.0
    assert nomination_floor(80.0, "verified") == 60.0


def test_a_nomination_lifts_a_real_application_but_cannot_carry_an_empty_one():
    """The security model of club onboarding in one property: a club's word is
    worth credibility, never identity. Minting athletes still costs one complete
    form each — including a date of birth the club cannot supply."""
    lifted = decide({"proof_status": "unverified"}, club_floor=75.0)
    assert lifted["decision"] == "admitted"
    assert lifted["effective_credibility"] == 75.0

    empty = decide({"competition_level": "", "years_competing": None, "birth_year": None,
                    "proof_kind": "none", "proof_status": "unverified"}, club_floor=75.0)
    assert empty["decision"] == "pending"
    assert empty["rule"] == "incomplete_application"


def test_a_club_with_no_paperwork_is_not_merely_weak_but_rejected():
    shell = club_legitimacy(dict(registration_id="", federation_name="", federation_id="",
                                 founded_year=None, teams_count=None, roster_url="",
                                 proof_kind="none", proof_status="unverified"), today_year=YEAR)
    assert shell["legitimacy"] == 0.0
    assert shell["decision"] == "rejected"
    assert shell["nomination_floor"] == 0.0


def test_checked_and_failed_proof_is_a_refusal_not_a_discount():
    assert decide({"proof_status": "rejected"})["rule"] == "proof_rejected"
    assert club_legitimacy(dict(registration_id="G1", federation_name="RFEF",
                                federation_id="ES-1", founded_year=1990, teams_count=8,
                                roster_url="https://c/r", proof_kind="roster",
                                proof_status="rejected"), today_year=YEAR)["decision"] == "rejected"


# ── the calibration the thresholds claim ────────────────────────────────────

def test_the_bands_land_where_the_policy_says_they_do():
    """Documented in admission.py: verified regional and above admits, verified
    local reviews, unverified regional reviews, unevidenced anything rejects.
    Pinned so that retuning a constant has to be a deliberate act."""
    assert decide({"competition_level": "national"})["decision"] == "admitted"
    assert decide({"competition_level": "regional"})["decision"] == "admitted"
    assert decide({"competition_level": "local"})["decision"] == "review"
    assert decide({"competition_level": "regional",
                   "proof_status": "unverified"})["decision"] == "review"
    assert decide({"competition_level": "regional", "proof_kind": "none",
                   "proof_status": "unverified"})["decision"] == "rejected"


def test_every_decision_carries_the_policy_that_produced_it():
    """Thresholds get retuned. A decision that does not record which rules were
    in force cannot be re-examined against outcomes later."""
    result = decide()
    assert result["policy_version"]
    assert result["thresholds"]["admit"] == ADMIT_AT
    assert score()["reasons"] and score()["policy_version"]


# ── regressions found by scripts/admission_stress.py ────────────────────────
# Both were invisible to the hand-written cases above and turned up in an
# exhaustive sweep. Each is pinned here so the sweep does not have to re-find it.

def test_an_incomplete_form_is_not_a_softer_landing_than_an_honest_weak_claim():
    """Found by the withholding sweep: 13,992 combinations where an applicant
    heading for rejection did better by blanking a field, because `review` is a
    strictly better place to be than `rejected` — a human can still let you in.
    An incomplete form must therefore not be a decision at all."""
    honest = decide({"competition_level": "local", "years_competing": 0, "birth_year": 2010,
                     "proof_kind": "none", "proof_status": "unverified"})
    blanked = decide({"competition_level": "", "years_competing": 0, "birth_year": 2010,
                      "proof_kind": "none", "proof_status": "unverified"})
    assert honest["decision"] == "rejected"
    assert blanked["decision"] == "pending"   # not "review" — it queues nobody


def test_deleting_a_failed_proof_does_not_score_better_than_leaving_it():
    """Found by the same sweep: with `rejected` proof scored at 0.10 and absent
    proof at 0.25, withdrawing a link that had been checked and failed *raised*
    credibility — making "get caught, then delete the evidence" a better move
    than never lying. A failed check now dominates the absence of one."""
    caught = score(proof_kind="roster", proof_status="rejected")["credibility"]
    withdrawn = score(proof_kind="none", proof_status="rejected")["credibility"]
    assert withdrawn <= caught


def test_nothing_is_admitted_on_evidence_nobody_has_opened():
    """Found by smoke-testing the running app, not by the sweep — whose own
    definition of "unevidenced" wrongly counted a queued link as evidence.

    At the `pending` multiplier a big enough claim clears the admit line on its
    own: an unchecked "international" scored 62.4 and walked in. Admission needs
    one *checked* source — the applicant's proof, or a verified club whose
    paperwork was itself checked.
    """
    unchecked = decide({"competition_level": "international", "years_competing": 10,
                        "birth_year": 1998, "proof_kind": "results",
                        "proof_status": "pending"})
    assert unchecked["decision"] == "review"
    assert unchecked["rule"] == "evidence_not_checked"

    # a verified club's nomination is a checked source, so it can finish the job
    vouched = decide({"competition_level": "international", "years_competing": 10,
                      "birth_year": 1998, "proof_kind": "results",
                      "proof_status": "pending"}, club_floor=75.0)
    assert vouched["decision"] == "admitted"


def test_a_club_cannot_verify_itself_on_its_own_say_so():
    """Every field on a club application is a self-reported string. Filled in
    perfectly they reach claim 100, which at the `pending` multiplier is 70 —
    over the 65 bar. A fabricated club could verify itself and start nominating.
    """
    fabricated = dict(registration_id="G-00000000", federation_name="Invented FA",
                      federation_id="XX-1", founded_year=1974, teams_count=9,
                      roster_url="https://invented.example/roster",
                      proof_kind="roster", proof_status="pending")
    scored = club_legitimacy(fabricated, today_year=YEAR)
    assert scored["legitimacy"] >= 65        # the number still clears the bar
    assert scored["decision"] == "review"     # the decision does not
    assert scored["nomination_floor"] == 0.0

    checked = club_legitimacy(fabricated | {"proof_status": "verified"}, today_year=YEAR)
    assert checked["decision"] == "verified"


def test_a_hard_disqualification_is_not_outranked_by_an_unfinished_form():
    """Found by sweeping the decision function's inputs *jointly* rather than one
    axis at a time — the earlier under-age test used a complete application, so
    the ordering bug hid behind it.

    `incomplete_application` used to run before the age gate, so a known
    15-year-old who left the competition level blank landed in `pending` instead
    of being refused. Holding a minor on file in a pending state, inviting them
    to finish a form they can never pass, is the opposite of what the age model
    is for.
    """
    minor_incomplete = decide({"birth_year": YEAR - 15, "competition_level": "",
                               "years_competing": None})
    assert minor_incomplete["decision"] == "rejected"
    assert minor_incomplete["rule"] == "under_minimum_age"

    # an adult with the same unfinished form is still simply unfinished
    adult_incomplete = decide({"birth_year": YEAR - 24, "competition_level": "",
                               "years_competing": None})
    assert adult_incomplete["decision"] == "pending"

    # and an unknown age cannot be disqualified on age — only held back from admission
    unknown_age = decide({"birth_year": None, "competition_level": "",
                          "years_competing": None})
    assert unknown_age["decision"] == "pending"


def test_a_proof_kind_with_no_link_behind_it_is_not_proof():
    """Picking "roster" from the dropdown and leaving the link box empty used to
    buy the full unchecked-link multiplier — 0.55 for evidence that does not
    exist and that no reviewer can ever resolve either way. It has to score as
    what it is, which is the same as claiming no proof at all."""
    real = score(proof_kind="roster", proof_status="unverified",
                 proof_url="https://club.example/roster")["credibility"]
    empty = score(proof_kind="roster", proof_status="unverified",
                  proof_url="")["credibility"]
    none = score(proof_kind="none", proof_status="unverified")["credibility"]
    assert empty == none < real

    # a bare scheme is not a link either: the same rule as the reviewer's button
    assert score(proof_kind="roster", proof_status="unverified",
                 proof_url="http://")["credibility"] == none

    # and it cannot be laundered into an admission by claiming a strong level
    verdict = decide({"competition_level": "international", "proof_kind": "results",
                      "proof_url": "", "proof_status": "unverified"})
    assert verdict["decision"] != "admitted"


def test_a_club_proof_kind_with_no_roster_url_is_not_proof_either():
    """Clubs have one URL, not two: `roster_url` is both the roster_proof
    component and the thing the evidence multiplier discounts against. With the
    URL blank, declaring a proof kind bought a better multiplier than admitting
    to none — so the claim is held fixed here and only the declaration varies,
    which is the comparison the earlier version of this test failed to make."""
    base = dict(registration_id="B-1", federation_name="RFEF", federation_id="F-9",
                founded_year=1998, teams_count=6, competition_level="regional",
                roster_url="", proof_status="unverified")
    claimed = club_legitimacy({**base, "proof_kind": "roster"}, today_year=YEAR)
    honest = club_legitimacy({**base, "proof_kind": "none"}, today_year=YEAR)
    assert claimed["legitimacy"] == honest["legitimacy"]
    assert claimed["evidence_multiplier"] == honest["evidence_multiplier"]

    # a real link still earns the unchecked-link multiplier
    linked = club_legitimacy({**base, "proof_kind": "roster",
                              "roster_url": "https://club.example/r"}, today_year=YEAR)
    assert linked["evidence_multiplier"] > claimed["evidence_multiplier"]


def test_the_caveat_says_the_same_thing_as_the_score():
    """An applicant charged the no-proof rate was still told "roster link,
    unverified", which describes the 0.55x they did not get. A reason that
    contradicts the number is worse than no reason: it tells them to argue with
    the wrong thing."""
    empty = score(proof_kind="roster", proof_status="unverified", proof_url="")
    text = " ".join(empty["caveats"]).lower()
    assert "no link was supplied" in text
    assert "roster link, unverified" not in text
    assert str(int(0.25 * 100)) + "%" in text

    real = score(proof_kind="roster", proof_status="unverified",
                 proof_url="https://club.example/roster")
    assert any("roster link, unverified" in c for c in real["caveats"])
