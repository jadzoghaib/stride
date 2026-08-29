"""Who gets onto the platform — athletes and clubs — from submitted data only.

The design decision that shapes everything here: **credibility and commercial
value are two different scores and only one of them is a gate.**

    credibility   "is this entity what it claims to be?"   adversarial, evidence-based, GATES
    social_score  "how valuable is this to a sponsor?"     observational, measured, RANKS

Blending them into one admission number — `A = 0.6·C + 0.4·S` — makes the gate
compensatory, which means social reach can buy legitimacy. Worked through, a
fitness influencer with a 95 social score and a self-declared local league claim
clears such a gate, while a genuine regional athlete with no connected platforms
fails it. That is precisely backwards for a product whose pitch to sponsors is
"real athletes, not influencers", and it destroys supply at the same time.

So here: **credibility decides admission; the social score can only route a case
to human review, never raise it.** What the social score actually governs is
listing — an admitted athlete with nothing to show starts as `draft`, which the
schema already models. Gate on legitimacy, tier on value.

Three further rules the arithmetic enforces:

1. **Evidence multiplies, it does not add.** A claim nobody checked is worth a
   fraction of the same claim with a federation roster behind it. As an addend,
   an unverified `international` claim outscores a verified `regional` one; as a
   multiplier it cannot. The strongest possible unevidenced application scores
   ~22 and is rejected.
2. **Missing is zero here — the opposite of `matching.py`, on purpose.** That
   module renormalises weights over the analytics it could measure, because the
   athlete does not control whether a platform returned data and a gap is a
   measurement failure, not a bad result. Everything on an application form is
   the opposite: the applicant chooses what to supply. Renormalising over
   self-reported fields makes *withholding information raise the score* — a
   blank competition level would hand its whole weight to tenure and score 100.
   Renormalise over what the system could not measure; never over what the
   applicant chose not to write down.
3. **Competition level is read relative to its own sport.** "Regional" in
   football sits under several professional tiers; "regional" in padel is near
   the competitive ceiling. A flat ladder would mis-rank both.

Every decision records its full input vector through `events`, so the policy is
back-testable: when there are outcomes, these thresholds can be re-fitted
against them instead of re-argued.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .proofcheck import looks_openable

POLICY_VERSION = "admission-v1"

# ── Evidence ────────────────────────────────────────────────────────────────
# Proof quality is a multiplier on the whole claim. `verified` exceeds 1.0
# deliberately: verification is the thing this gate is actually buying, so it
# should be able to lift a modest claim over the line while leaving a large
# unevidenced one far below it. Results are capped at 100.
EVIDENCE_MULTIPLIER = {
    "verified": 1.15,     # a human or crawler confirmed the link names this athlete
    "pending": 0.70,      # submitted, queued for checking
    "unverified": 0.55,   # a link exists, nobody has looked at it
    "rejected": 0.10,     # checked and did not support the claim
}
NO_PROOF_MULTIPLIER = 0.25   # nothing supplied at all
PROOF_KINDS = ("none", "roster", "results", "licence")
PROOF_STATUSES = ("unverified", "pending", "verified", "rejected")

# ── Sport structure ─────────────────────────────────────────────────────────
# Share of commercially active athletes who already have representation, from
# business-plan/sport_data.py. Duplicated rather than imported because the sport
# index is a planning module outside the API package; when it is wired into the
# product this table should be read from it instead of maintained here.
# Keys are lower-case because the lookup lower-cases the athlete's sport before
# reading this table. "MMA" sat here in its published capitalisation and could
# therefore never be matched: every MMA applicant was silently scored against
# the neutral fallback instead of a 0.66 agent density.
AGENT_DENSITY = {
    "running / trail": 0.10, "cycling": 0.35, "swimming": 0.25, "football": 0.88,
    "fitness / gym": 0.08, "padel": 0.15, "tennis": 0.78, "basketball": 0.78,
    "volleyball": 0.45, "climbing": 0.12, "athletics": 0.48, "triathlon": 0.14,
    "surfing": 0.22, "golf": 0.72, "boxing": 0.70, "mma": 0.66, "gymnastics": 0.42,
    "handball": 0.42, "rowing": 0.18, "skateboarding": 0.28, "motorsport": 0.85,
}
NEUTRAL_DENSITY = 0.45          # an unlisted sport is treated as neither dense nor sparse
DENSITY_SENSITIVITY = 0.12      # how far the ladder tilts between the extremes

COMPETITION_LEVELS = ("local", "regional", "national", "international")
LEVEL_BASE = {"local": 0.35, "regional": 0.58, "national": 0.78, "international": 0.92}

CLAIM_WEIGHTS = {"level": 0.85, "tenure": 0.15}

# Tenure is credited on whichever reading is kinder, because the two failure
# modes point opposite ways: raw years is an age proxy that penalises the 16- and
# 17-year-olds this platform deliberately onboards, while pure share penalises
# the adult who came to the sport late. Eight seasons is full marks either way.
#
# TENURE_START_AGE is the age at which registered competition typically begins,
# and it has to sit above MIN_AGE - TENURE_FULL_YEARS or the share reading can
# never bind for anyone old enough to hold an account, leaving the kinder-of-two
# rule as decoration. At 10 a 16-year-old has six eligible seasons, so five of
# them reads as deep commitment rather than as "fewer years than an adult".
TENURE_START_AGE = 10
TENURE_FULL_YEARS = 8

# ── Thresholds ──────────────────────────────────────────────────────────────
# Calibrated so that: verified regional and above admits, verified local goes to
# review, unverified regional goes to review, and no unevidenced claim of any
# size admits. See tests/test_admission.py, which pins each of those.
ADMIT_AT = 55.0
REVIEW_AT = 25.0

MIN_AGE = 16                    # see business-plan/05-product-gaps.md — the age model

#: Rules that are findings about the applicant rather than a shortage of
#: evidence about them. The distinction matters exactly once — a profile listed
#: before this gate existed keeps that listing through an insufficient claim,
#: because an application is a request to be admitted and not a re-audit of what
#: came before. It must not survive these two: one is somebody having checked
#: the proof and rejected it, the other is an age the platform may not serve at
#: all. "Your claim is weak" is not the same category as "you are 15".
DISQUALIFYING_RULES = ("proof_rejected", "under_minimum_age")
SOCIAL_REVIEW_FLOOR = 70.0      # a following this size behind a weak claim gets human eyes
# Must sit BELOW REVIEW_AT, or the branch it guards is unreachable: anything at
# or above the review floor has already been sent to a human by the band check.
# It was set equal to REVIEW_AT, so the rule the policy documents most loudly —
# reach without credibility gets human eyes — was dead code, and the sweep's
# "the social score never lifts a decision" assertion passed trivially.
SOCIAL_REVIEW_MIN_CREDIBILITY = 12.0


def _blend(weights: dict[str, float], values: dict[str, float | None]) -> float:
    """Plain weighted sum, with an unsupplied component scoring zero.

    Deliberately *not* the renormalisation `matching.py` performs. There, a
    missing component is a measurement the platform could not take. Here it is a
    box the applicant left empty, and any rule under which leaving a box empty
    improves the outcome is an invitation, not a policy. The empty box is still
    named in `caveats`, so the applicant can see what it cost them.
    """
    return sum(w * (values.get(k) or 0.0) for k, w in weights.items())


def _missing(values: dict[str, float | None]) -> list[str]:
    return [k for k, v in values.items() if v is None]


def level_value(level: str, sport: str) -> float | None:
    """Competition level, normalised and read against its own sport's structure.

    The tilt is small on purpose. It encodes a real difference — regional
    football sits below several professional tiers, regional padel does not —
    without pretending the correction is precise enough to move an application
    more than one band.
    """
    if level not in LEVEL_BASE:
        return None
    density = AGENT_DENSITY.get(sport.lower().strip(), NEUTRAL_DENSITY)
    tilt = 1 + DENSITY_SENSITIVITY * (NEUTRAL_DENSITY - density)
    return max(0.0, min(1.0, LEVEL_BASE[level] * tilt))


def tenure_value(years_competing: int | None, birth_year: int | None,
                 today_year: int | None = None) -> float | None:
    if years_competing is None or years_competing < 0:
        return None
    absolute = min(1.0, years_competing / TENURE_FULL_YEARS)
    age = age_from(birth_year, today_year)
    if age is None:
        return absolute
    eligible = max(1, age - TENURE_START_AGE)
    return min(1.0, max(absolute, years_competing / eligible))


def evidence_multiplier(proof_kind: str, proof_status: str,
                        url: str | None = None) -> float:
    # A failed check outranks the absence of one, and it does so here in the
    # pure function rather than only at the endpoint. Otherwise withdrawing a
    # link that was checked and did not stand up scores better (0.25) than
    # leaving it in place (0.10), which makes "get caught, then delete the
    # evidence" a strictly better move than never having lied. Found by
    # scripts/admission_stress.py, not by hand.
    if proof_status == "rejected":
        return EVIDENCE_MULTIPLIER["rejected"]
    if proof_kind not in PROOF_KINDS or proof_kind == "none":
        return NO_PROOF_MULTIPLIER
    # Choosing "roster" from the dropdown and leaving the link box empty bought
    # the same 0.55x as an actual unchecked link. There is nothing there for a
    # reviewer to open, so it scores as what it is. `looks_openable` rather than
    # a non-blank test, and imported rather than re-implemented, so the meaning
    # of "there is a page here" cannot drift from the reviewer's verify button.
    if url is not None and not looks_openable(url):
        return NO_PROOF_MULTIPLIER
    return EVIDENCE_MULTIPLIER.get(proof_status, EVIDENCE_MULTIPLIER["unverified"])


def age_from(birth_year: int | None, today_year: int | None = None) -> int | None:
    if not birth_year:
        return None
    year = today_year or datetime.now(timezone.utc).year
    return year - birth_year


def athlete_credibility(application: dict, today_year: int | None = None) -> dict:
    """Credibility in [0,100] with the decomposition that produced it.

    Returns components, the weights that actually applied, the evidence
    multiplier, and plain-text reasons — the same contract `sponsor_matches`
    honours, because a decision an applicant cannot have explained to them is a
    decision they cannot appeal.
    """
    sport = application.get("sport") or ""
    values: dict[str, float | None] = {
        "level": level_value(application.get("competition_level") or "", sport),
        "tenure": tenure_value(application.get("years_competing"),
                               application.get("birth_year"), today_year),
    }
    multiplier = evidence_multiplier(application.get("proof_kind") or "none",
                                     application.get("proof_status") or "unverified",
                                     url=application.get("proof_url") or "")
    # Competition level is the load-bearing claim; without it there is nothing to
    # discount and nothing to check, so the application is incomplete rather than
    # weak. Scoring it anyway would let an applicant omit the one field the whole
    # gate turns on.
    scoreable = values["level"] is not None
    claim = 100 * _blend(CLAIM_WEIGHTS, values) if scoreable else 0.0
    credibility = min(100.0, claim * multiplier)

    reasons, caveats = [], []
    level = application.get("competition_level")
    if values["level"] is not None:
        density = AGENT_DENSITY.get(sport.lower().strip())
        note = "" if density is None else (
            " (read against a crowded professional pyramid)" if density > 0.6
            else " (read against a sport with little agent coverage)" if density < 0.3
            else "")
        reasons.append(f"Competes at {level} level in {sport}{note}")
    else:
        caveats.append("Competition level missing or unrecognised — the application cannot "
                       "be scored without it")
    if values["tenure"] is None:
        caveats.append("Seasons competing not supplied — scored as zero, not excluded")
    if values["tenure"] is not None and values["tenure"] >= 0.6:
        reasons.append(f"{application.get('years_competing')} seasons competing")
    # Gated on the same openability test the multiplier uses. A declared kind
    # with nothing behind it scores as no proof, so it has to *read* as no proof:
    # an applicant told "roster link, unchecked" while being charged the no-proof
    # rate cannot tell which number to argue with.
    if (application.get("proof_kind") in ("roster", "results", "licence")
            and looks_openable(application.get("proof_url") or "")):
        state = application.get("proof_status") or "unverified"
        (reasons if state == "verified" else caveats).append(
            f"Proof of participation: {application['proof_kind']} link, {state}")
    elif application.get("proof_kind") in ("roster", "results", "licence"):
        # `multiplier`, not the constant: a rejected proof short-circuits to 0.10
        # before the openability test ever runs, so quoting NO_PROOF_MULTIPLIER
        # here told an applicant 25% while charging them 10%.
        caveats.append(f"A {application['proof_kind']} was named but no link was supplied — "
                       "there is nothing for a reviewer to open, so the claim is discounted "
                       f"to {int(multiplier * 100)}% of its face value")
    else:
        caveats.append("No proof of participation supplied — claim discounted to "
                       f"{int(multiplier * 100)}% of its face value")

    return {
        "credibility": round(credibility, 1),
        "claim": round(claim, 1),
        "components": {k: (round(v, 3) if v is not None else None) for k, v in values.items()},
        "weights": CLAIM_WEIGHTS,
        "missing": _missing(values),
        "scoreable": scoreable,
        "evidence_multiplier": multiplier,
        "reasons": reasons,
        "caveats": caveats,
        "policy_version": POLICY_VERSION,
    }


def admission_decision(credibility: float, *, proof_status: str = "unverified",
                       social_score: float | None = None, age: int | None = None,
                       club_floor: float | None = None, scoreable: bool = True) -> dict:
    """`admitted` | `review` | `rejected` | `pending`, with the rule that fired.

    Ordering matters. Disqualifications run first and cannot be outscored;
    the credibility bands run next; the social score runs last and only ever
    moves a case *towards* human review.
    """
    effective = credibility
    notes: list[str] = []
    # A club floor is only ever non-zero for a verified club, whose own proof was
    # checked — so a nomination counts as a checked source even when the
    # athlete's own link has not been opened yet.
    checked = proof_status == "verified" or bool(club_floor)
    if club_floor is not None and club_floor > effective:
        notes.append(f"Raised to {club_floor:.1f} by a verified club's nomination")
        effective = club_floor

    if proof_status == "rejected":
        return _decision("rejected", "proof_rejected", effective,
                         ["Proof of participation was checked and did not support the claim"])
    if age is not None and age < MIN_AGE:
        # Above the incompleteness check, not below it. The docstring promises
        # disqualifications run first and this is one: when the date of birth is
        # on the form, the applicant is refused whatever else is missing.
        # Holding a known minor in `pending` would keep their data on file and
        # invite them to finish a form they can never pass.
        return _decision("rejected", "under_minimum_age", effective,
                         [f"Under the {MIN_AGE} minimum age for an account"])
    if not scoreable:
        # `pending`, not `review` — and the distinction was found by the stress
        # sweep, not by hand. Routing an unanswerable form into the review queue
        # makes it *better* than an honest weak claim, because a queued case can
        # still be admitted by a human while a rejected one cannot. That hands
        # every applicant heading for rejection a strategy: leave a box blank.
        # An incomplete form is not a lenient decision, it is the absence of one.
        # It consumes no reviewer and confers nothing, so stalling gains nothing.
        return _decision("pending", "incomplete_application", effective,
                         notes + ["Competition level missing — nothing to score yet"])
    if age is None:
        notes.append("Date of birth not supplied — cannot confirm the age gate, so this "
                     "cannot auto-admit")

    if effective >= ADMIT_AT and age is not None:
        # Nothing auto-admits on evidence nobody has looked at. `pending` means
        # a link was supplied, not that it says what the applicant says it says,
        # and at 0.70 a large enough claim clears the line on its own — an
        # unchecked "international" scored 62.4 and walked in. Admission needs
        # one *checked* source: the applicant's own proof, or a verified club
        # whose paperwork was itself checked.
        if checked:
            return _decision("admitted", "credibility_above_admit", effective, notes)
        return _decision("review", "evidence_not_checked", effective,
                         notes + ["Credibility clears the bar, but no evidence has been "
                                  "checked yet"])
    if effective >= REVIEW_AT:
        return _decision("review", "credibility_in_review_band", effective, notes)

    # Last, and only downwards: a large following behind a weak claim is the
    # exact profile this platform exists not to be, but it is also what a real
    # athlete who filled the form badly looks like. Human eyes, never auto-admit.
    if (social_score is not None and social_score >= SOCIAL_REVIEW_FLOOR
            and effective >= SOCIAL_REVIEW_MIN_CREDIBILITY):
        notes.append(f"Social score {social_score:.0f} against credibility "
                     f"{effective:.1f} — routed to review rather than rejected")
        return _decision("review", "social_reach_without_credibility", effective, notes)
    return _decision("rejected", "credibility_below_review", effective, notes)


def _decision(decision: str, rule: str, effective: float, notes: list[str]) -> dict:
    return {"decision": decision, "rule": rule,
            "effective_credibility": round(effective, 1), "notes": notes,
            "thresholds": {"admit": ADMIT_AT, "review": REVIEW_AT},
            "policy_version": POLICY_VERSION}


# ─────────────────────────────────────────────────────────────────────────────
# Clubs
# ─────────────────────────────────────────────────────────────────────────────
# Same split as above, and for the same reason: a club with a large Instagram is
# more *marketable*, not more *legitimate*. Reach belongs in package pricing, not
# in the gate. What is scored here is only what makes a club real — legal
# registration, federation affiliation, longevity, structure, a public roster.

CLUB_WEIGHTS = {
    "registration": 0.30,   # a legal entity exists and named itself
    "federation": 0.30,     # affiliated to a governing body, with a number
    "longevity": 0.15,      # a club that has existed for years is hard to fake
    "structure": 0.15,      # teams actually fielded
    "roster_proof": 0.10,   # a public page a third party can read
}
CLUB_LONGEVITY_FULL_YEARS = 25
CLUB_STRUCTURE_FULL_TEAMS = 6

CLUB_VERIFY_AT = 65.0
CLUB_REVIEW_AT = 35.0

# What a verified club's nomination is worth to an athlete who supplied nothing
# else. Deliberately below 1.0: a club vouching for someone is real evidence,
# but weaker than that person's own federation licence, and it must not be
# possible to mint admissions by clearing the club gate alone. At this factor
# only clubs scoring ~73+ can carry an athlete over ADMIT_AT unaided.
NOMINATION_TRANSFER = 0.75


def club_legitimacy(application: dict, today_year: int | None = None) -> dict:
    founded = application.get("founded_year")
    year = today_year or datetime.now(timezone.utc).year
    teams = application.get("teams_count")
    federation_name = (application.get("federation_name") or "").strip()
    federation_id = (application.get("federation_id") or "").strip()

    values: dict[str, float | None] = {
        "registration": 1.0 if (application.get("registration_id") or "").strip() else 0.0,
        # a name without a number is a claim; a number is a thing that can be looked up
        "federation": 1.0 if (federation_name and federation_id)
                      else 0.6 if federation_name else 0.0,
        "longevity": (min(1.0, max(0, year - founded) / CLUB_LONGEVITY_FULL_YEARS)
                      if founded else None),
        "structure": (min(1.0, teams / CLUB_STRUCTURE_FULL_TEAMS)
                      if teams is not None else None),
        # `looks_openable`, not a non-blank test: `http://` earned this component
        # in full while the evidence multiplier below already treated it as no
        # proof, so one URL was scored two different ways in the same function.
        "roster_proof": 1.0 if looks_openable(application.get("roster_url") or "") else 0.0,
    }
    # `roster_url` is the club's proof link — there is no separate field, so the
    # same URL feeds the roster_proof component and the evidence multiplier.
    multiplier = evidence_multiplier(application.get("proof_kind") or "none",
                                     application.get("proof_status") or "unverified",
                                     url=application.get("roster_url") or "")
    claim = 100 * _blend(CLUB_WEIGHTS, values)
    legitimacy = min(100.0, claim * multiplier)

    # A fully self-reported application — registration number, federation id,
    # founding year, team count, roster URL, none of them opened by anyone —
    # reaches claim 100 and, at the `pending` multiplier, 70. That cleared the
    # 65 verification bar, so a fabricated club could verify itself and start
    # nominating. `verified` has to mean somebody verified something.
    checked = (application.get("proof_status") or "") == "verified"
    decision = ("verified" if legitimacy >= CLUB_VERIFY_AT and checked
                else "review" if legitimacy >= CLUB_REVIEW_AT else "rejected")
    if (application.get("proof_status") or "") == "rejected":
        decision = "rejected"

    reasons, caveats = [], []
    if values["registration"]:
        reasons.append("Legal registration number supplied")
    else:
        caveats.append("No legal registration number — the strongest single signal, absent")
    if federation_name and federation_id:
        reasons.append(f"Affiliated to {federation_name} (#{federation_id})")
    elif federation_name:
        caveats.append(f"Names {federation_name} but supplies no affiliation number")
    else:
        caveats.append("No federation affiliation named")
    if values["longevity"] is None:
        caveats.append("Founding year not supplied — excluded from the score")
    elif founded:
        reasons.append(f"Operating since {founded}")
    if values["structure"] is None:
        caveats.append("Team count not supplied — excluded from the score")
    # The clubs had no line about their evidence at all, so a club discounted to
    # a quarter of its claim for naming a proof kind it never linked was told
    # nothing about the largest single factor in its own score.
    #
    # Both halves are gated on the *declaration* as well as the link, because the
    # multiplier is: a roster page supplied under `proof_kind: none` still scores
    # as no proof, and calling that "roster page supplied" praised evidence the
    # score had already thrown away. The percentage comes from `multiplier` for
    # the same reason — a rejected proof is 0.10, not the no-proof 0.25.
    named = application.get("proof_kind") or "none"
    declared = named in PROOF_KINDS and named != "none"
    linked = looks_openable(application.get("roster_url") or "")
    if declared and linked:
        state = application.get("proof_status") or "unverified"
        (reasons if state == "verified" else caveats).append(
            f"Roster page supplied, {state}")
    elif declared:
        caveats.append(f"A {named} was named but no page was linked — nothing to check, so "
                       f"the claim is discounted to {int(multiplier * 100)}% of its face value")
    elif linked:
        # Careful about "ignored": `roster_proof` credits any openable URL, so the
        # page does raise the claim. What it does not do is earn an evidence
        # multiplier, because nothing says what a reviewer is meant to check.
        caveats.append("A page is linked and counts towards the claim, but no kind of proof "
                       "is declared, so nobody knows what to check it against — the claim is "
                       f"discounted to {int(multiplier * 100)}% of its face value. Name what "
                       "the page is.")
    else:
        caveats.append("No roster or licence page linked — there is nothing a reviewer can "
                       f"open, so the claim is discounted to {int(multiplier * 100)}% of "
                       "its face value")

    return {
        "legitimacy": round(legitimacy, 1),
        "claim": round(claim, 1),
        "decision": decision,
        "components": {k: (round(v, 3) if v is not None else None) for k, v in values.items()},
        "weights": CLUB_WEIGHTS,
        "missing": _missing(values),
        "evidence_multiplier": multiplier,
        "nomination_floor": round(nomination_floor(legitimacy, decision), 1),
        "reasons": reasons,
        "caveats": caveats,
        "thresholds": {"verify": CLUB_VERIFY_AT, "review": CLUB_REVIEW_AT},
        "policy_version": POLICY_VERSION,
    }


def nomination_floor(legitimacy: float, decision: str) -> float:
    """The credibility floor a club's nomination confers on an athlete.

    A floor, not a bypass — the athlete's own evidence still counts and can
    exceed it. Only a verified club confers anything, which is what makes
    de-verifying a club a meaningful sanction.
    """
    return round(NOMINATION_TRANSFER * legitimacy, 1) if decision == "verified" else 0.0
