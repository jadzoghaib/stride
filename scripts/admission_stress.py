"""Adversarial stress test for the admission policy.

    python scripts/admission_stress.py

Not a test suite — a search for the inputs that embarrass the policy. Four
questions, each swept exhaustively over the discrete input space rather than
spot-checked, because the interesting failures in a scoring rule are always at
combinations nobody thought to write a case for:

    1. MONOTONICITY   does more evidence, a higher level or a longer career
                      ever *lower* a score?
    2. WITHHOLDING    is there any field an applicant does better to leave blank?
    3. CLUBS          the same two questions, plus: can a club verify itself?
    4. DECISION       the verdict's invariants over the *joint* input space —
                      credibility x proof x age x social x nomination floor
    5. BOUNDS         scores in range, and stable across repeated evaluation
    6. FORGERY COST   what is the cheapest input that gets admitted, and does
                      any zero-evidence application get in?
    7. OPS LOAD       under a plausible applicant mix, how many humans does the
                      review band cost — and how far do the thresholds move it?

Sections 3 to 5 exist because the first version of this harness missed two real
defects that only surfaced when the running API was driven by hand: an unchecked
"international" claim admitted at 62.4, and a fabricated club that verified
itself at 70. Both lived in parts of the input space nothing swept.

A policy that is individually correct on every case and sends 60% of applicants
to a manual queue is still a broken policy, which is why (4) is here.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from stride_api.admission import (ADMIT_AT, AGENT_DENSITY, COMPETITION_LEVELS,  # noqa: E402
                                  EVIDENCE_MULTIPLIER, MIN_AGE, PROOF_STATUSES, REVIEW_AT,
                                  admission_decision, athlete_credibility, club_legitimacy,
                                  nomination_floor)

YEAR = 2026
SPORTS = ["football", "padel", "running / trail", "korfball"]
YEARS = [0, 1, 2, 3, 5, 8, 12]
BIRTHS = [2010, 2008, 2004, 1998, 1990]
KINDS = ["none", "roster", "results", "licence"]

# evidence, weakest first — the order monotonicity is checked against
EVIDENCE_ORDER = ["rejected", "unverified", "pending", "verified"]
LEVEL_ORDER = list(COMPETITION_LEVELS)

failures: list[str] = []


def note(section: str, message: str) -> None:
    failures.append(f"[{section}] {message}")


def application(**kw) -> dict:
    base = dict(sport="football", competition_level="regional", years_competing=3,
                birth_year=2004, proof_kind="roster", proof_status="verified")
    base.update(kw)
    return base


def cred(app: dict) -> float:
    return athlete_credibility(app, today_year=YEAR)["credibility"]


def outcome(app: dict, social: float | None = None, floor: float | None = None) -> str:
    scored = athlete_credibility(app, today_year=YEAR)
    return admission_decision(
        scored["credibility"], proof_status=app["proof_status"], social_score=social,
        age=(YEAR - app["birth_year"]) if app["birth_year"] else None,
        club_floor=floor, scoreable=scored["scoreable"])["decision"]


def grid():
    """Every combination of the discrete inputs — 4 x 4 x 7 x 5 x 4 x 4 = 8,960."""
    return itertools.product(SPORTS, LEVEL_ORDER, YEARS, BIRTHS, KINDS, PROOF_STATUSES)


# ── 1. monotonicity ─────────────────────────────────────────────────────────
def check_monotonicity() -> int:
    checked = 0
    for sport, level, years, birth, kind in itertools.product(
            SPORTS, LEVEL_ORDER, YEARS, BIRTHS, KINDS):
        base = dict(sport=sport, competition_level=level, years_competing=years,
                    birth_year=birth, proof_kind=kind)
        # stronger evidence must never score lower
        scores = [cred(application(**base, proof_status=st)) for st in EVIDENCE_ORDER]
        for a, b, sa, sb in zip(EVIDENCE_ORDER, EVIDENCE_ORDER[1:], scores, scores[1:]):
            checked += 1
            if sb < sa - 1e-9:
                note("monotonicity", f"{a}->{b} LOWERS the score for {base}: {sa} -> {sb}")
    for sport, years, birth, kind, status in itertools.product(
            SPORTS, YEARS, BIRTHS, KINDS, PROOF_STATUSES):
        # a higher competition level must never score lower
        scores = [cred(application(sport=sport, competition_level=lv, years_competing=years,
                                   birth_year=birth, proof_kind=kind, proof_status=status))
                  for lv in LEVEL_ORDER]
        for a, b, sa, sb in zip(LEVEL_ORDER, LEVEL_ORDER[1:], scores, scores[1:]):
            checked += 1
            if sb < sa - 1e-9:
                note("monotonicity", f"level {a}->{b} LOWERS the score: {sa} -> {sb}")
    for sport, level, birth, kind, status in itertools.product(
            SPORTS, LEVEL_ORDER, BIRTHS, KINDS, PROOF_STATUSES):
        # more seasons must never score lower
        scores = [cred(application(sport=sport, competition_level=level, years_competing=y,
                                   birth_year=birth, proof_kind=kind, proof_status=status))
                  for y in YEARS]
        for a, b, sa, sb in zip(YEARS, YEARS[1:], scores, scores[1:]):
            checked += 1
            if sb < sa - 1e-9:
                note("monotonicity", f"{a}->{b} seasons LOWERS the score: {sa} -> {sb}")
    return checked


# ── 2. withholding ──────────────────────────────────────────────────────────
BLANKABLE = {"competition_level": "", "years_competing": None, "birth_year": None,
             "proof_kind": "none"}


def check_withholding() -> int:
    """For every application, blanking any subset of fields must not improve the
    outcome. This is the property the first draft of the scorer failed: a blank
    competition level renormalised its whole weight onto tenure and scored 100."""
    # `pending` ranks with `rejected`: neither is admitted and neither occupies a
    # reviewer, so an applicant gains nothing by stalling into it.
    rank = {"rejected": 0, "pending": 0, "review": 1, "admitted": 2}
    checked = 0
    for sport, level, years, birth, kind, status in grid():
        full = application(sport=sport, competition_level=level, years_competing=years,
                           birth_year=birth, proof_kind=kind, proof_status=status)
        full_rank = rank[outcome(full)]
        full_cred = cred(full)
        for size in (1, 2):
            for fields in itertools.combinations(BLANKABLE, size):
                checked += 1
                blanked = {**full, **{f: BLANKABLE[f] for f in fields}}
                if rank[outcome(blanked)] > full_rank:
                    note("withholding", f"blanking {fields} IMPROVES outcome for {full}")
                if cred(blanked) > full_cred + 1e-9:
                    note("withholding", f"blanking {fields} RAISES credibility "
                                        f"{full_cred} -> {cred(blanked)} for {full}")
    return checked


# ── 6. what does admission cost a liar? ─────────────────────────────────────
def check_forgery_cost() -> dict:
    admitted_without_evidence = []
    cheapest = None
    for sport, level, years, birth, kind, status in grid():
        app = application(sport=sport, competition_level=level, years_competing=years,
                          birth_year=birth, proof_kind=kind, proof_status=status)
        if outcome(app, social=95.0) != "admitted":
            continue
        # `pending` belongs in this list: a link nobody has opened is not
        # evidence. Leaving it out was the blind spot that let an unchecked
        # "international" claim through the first sweep at 62.4.
        if kind == "none" or status != "verified":
            admitted_without_evidence.append(app)
        # "cheapest" = lowest claimed level, then fewest seasons
        key = (LEVEL_ORDER.index(level), years)
        if cheapest is None or key < cheapest[0]:
            cheapest = (key, app)
    if admitted_without_evidence:
        note("forgery", f"{len(admitted_without_evidence)} applications admitted with no "
                        f"checked evidence, e.g. {admitted_without_evidence[0]}")
    return {"cheapest_admitted": cheapest[1] if cheapest else None,
            "unevidenced_admits": len(admitted_without_evidence)}


# ── clubs, swept the way athletes are ───────────────────────────────────────
# The hand-picked cases below used to be the whole club story, and that is
# exactly why the self-verifying club escaped: a fabricated application scored
# 70, cleared the 65 bar at the `pending` multiplier, and nothing here looked.
CLUB_REG = ["", "G-08123456"]
CLUB_FED_NAME = ["", "Federacio Catalana"]
CLUB_FED_ID = ["", "FCF-2211"]
CLUB_FOUNDED = [None, 2024, 2010, 1970]
CLUB_TEAMS = [None, 0, 2, 9]
CLUB_ROSTER = ["", "https://club.example/roster"]


def club_grid():
    """2 x 2 x 2 x 4 x 4 x 2 x 4 x 4 = 8,192 club applications."""
    return itertools.product(CLUB_REG, CLUB_FED_NAME, CLUB_FED_ID, CLUB_FOUNDED,
                             CLUB_TEAMS, CLUB_ROSTER, KINDS, PROOF_STATUSES)


def _club_fields(combo) -> dict:
    reg, fed_name, fed_id, founded, teams, roster, kind, status = combo
    return dict(registration_id=reg, federation_name=fed_name, federation_id=fed_id,
                founded_year=founded, teams_count=teams, roster_url=roster,
                proof_kind=kind, proof_status=status)


def legit(app: dict) -> float:
    return club_legitimacy(app, today_year=YEAR)["legitimacy"]


def check_clubs() -> int:
    """Monotonicity, withholding, self-verification and floor sanity, over every
    combination rather than over the six cases somebody thought to write."""
    rank = {"rejected": 0, "review": 1, "verified": 2}
    checked = 0

    for combo in club_grid():
        fields = _club_fields(combo)
        scored = club_legitimacy(fields, today_year=YEAR)
        checked += 1

        # `verified` must mean somebody verified something
        if scored["decision"] == "verified" and fields["proof_status"] != "verified":
            note("club", f"verified on {fields['proof_status']} proof: {fields}")
        # a floor only exists behind a verified decision, and never exceeds the score
        floor = scored["nomination_floor"]
        if floor and scored["decision"] != "verified":
            note("club", f"floor {floor} behind a {scored['decision']} decision: {fields}")
        if floor > scored["legitimacy"] + 1e-9:
            note("club", f"floor {floor} exceeds legitimacy {scored['legitimacy']}")
        if not 0.0 <= scored["legitimacy"] <= 100.0:
            note("club", f"legitimacy {scored['legitimacy']} out of bounds: {fields}")

        # withholding: blanking any single field must not help
        for field, blank in (("registration_id", ""), ("federation_name", ""),
                             ("federation_id", ""), ("founded_year", None),
                             ("teams_count", None), ("roster_url", ""),
                             ("proof_kind", "none")):
            checked += 1
            blanked = {**fields, field: blank}
            after = club_legitimacy(blanked, today_year=YEAR)
            if after["legitimacy"] > scored["legitimacy"] + 1e-9:
                note("club", f"blanking {field} RAISES legitimacy "
                             f"{scored['legitimacy']} -> {after['legitimacy']}: {fields}")
            if rank[after["decision"]] > rank[scored["decision"]]:
                note("club", f"blanking {field} IMPROVES the decision "
                             f"{scored['decision']} -> {after['decision']}: {fields}")

    # stronger evidence never scores lower
    for combo in itertools.product(CLUB_REG, CLUB_FED_NAME, CLUB_FED_ID, CLUB_FOUNDED,
                                   CLUB_TEAMS, CLUB_ROSTER, KINDS):
        fields = _club_fields((*combo, "unverified"))
        scores = [legit({**fields, "proof_status": st}) for st in EVIDENCE_ORDER]
        for a, b, sa, sb in zip(EVIDENCE_ORDER, EVIDENCE_ORDER[1:], scores, scores[1:]):
            checked += 1
            if sb < sa - 1e-9:
                note("club", f"{a}->{b} LOWERS legitimacy {sa} -> {sb}: {fields}")
    return checked


def check_decision_surface() -> int:
    """The decision function's invariants over the joint input space rather than
    one axis at a time. `club_floor` x `proof_status` x `age` x `social_score`
    interact, and both defects that escaped this harness lived in that
    interaction."""
    rank = {"rejected": 0, "pending": 0, "review": 1, "admitted": 2}
    checked = 0
    for c, status, age, social, floor, scoreable in itertools.product(
            [0.0, 10.0, 24.9, 25.0, 40.0, 54.9, 55.0, 80.0, 100.0],
            PROOF_STATUSES, [None, 15, 16, 24, 40], [None, 0.0, 69.9, 70.0, 100.0],
            [None, 0.0, 30.0, 75.0], [True, False]):
        d = admission_decision(c, proof_status=status, social_score=social, age=age,
                               club_floor=floor, scoreable=scoreable)
        checked += 1
        verdict = d["decision"]

        if verdict not in rank:
            note("decision", f"unknown verdict {verdict}")
        if age is not None and age < MIN_AGE and verdict != "rejected":
            note("decision", f"under-age admitted as {verdict}: c={c} age={age}")
        if status == "rejected" and verdict != "rejected":
            note("decision", f"rejected proof survived as {verdict}: c={c}")
        if verdict == "admitted":
            if age is None:
                note("decision", f"admitted with no date of birth: c={c}")
            if d["effective_credibility"] < ADMIT_AT - 1e-9:
                note("decision", f"admitted below the bar: {d['effective_credibility']}")
            if status != "verified" and not floor:
                note("decision", f"admitted on unchecked evidence: c={c} status={status}")
            if not scoreable:
                note("decision", f"admitted on an unscoreable application: c={c}")

        # The social score may never ADMIT. Moving a case to review is what the
        # rule is for — reach behind a claim we cannot verify is the profile
        # that deserves human eyes. The stronger invariant written here first
        # ("never improves the verdict") only ever passed because the branch it
        # guarded was unreachable: SOCIAL_REVIEW_MIN_CREDIBILITY sat equal to
        # REVIEW_AT, so anything that reached it had already been sent to
        # review. A test that passes because the code is dead is not a test.
        quiet = admission_decision(c, proof_status=status, social_score=None, age=age,
                                   club_floor=floor, scoreable=scoreable)
        if verdict == "admitted" and quiet["decision"] != "admitted":
            note("decision", f"a social score ADMITTED a case that was "
                             f"{quiet['decision']} without it")

        # a larger floor may never worsen it
        if floor:
            without = admission_decision(c, proof_status=status, social_score=social,
                                         age=age, club_floor=None, scoreable=scoreable)
            if rank[verdict] < rank[without["decision"]]:
                note("decision", f"a club floor of {floor} WORSENED "
                                 f"{without['decision']} -> {verdict}")
    return checked


def check_bounds_and_idempotence() -> int:
    """Scores stay in range, and evaluating the same application twice says the
    same thing — the property every retry, refresh and re-review depends on."""
    checked = 0
    for sport, level, years, birth, kind, status in grid():
        app = application(sport=sport, competition_level=level, years_competing=years,
                          birth_year=birth, proof_kind=kind, proof_status=status)
        first = athlete_credibility(app, today_year=YEAR)
        second = athlete_credibility(app, today_year=YEAR)
        checked += 1
        if first != second:
            note("idempotence", f"credibility is not stable for {app}")
        if not 0.0 <= first["credibility"] <= 100.0:
            note("bounds", f"credibility {first['credibility']} out of range: {app}")
        # Both figures are rounded to one decimal before they are returned, so
        # comparing them needs the rounding back: 0.05 on the credibility plus
        # 1.15 x 0.05 on the claim is ~0.11. A tighter epsilon reports 594
        # failures that are entirely an artifact of the display precision.
        ceiling = first["claim"] * max(EVIDENCE_MULTIPLIER.values()) + 0.12
        if first["scoreable"] and first["credibility"] > ceiling:
            note("bounds", f"credibility exceeds claim x max multiplier: {app}")
    return checked


def check_nomination_laundering() -> None:
    """A club's word must not compound. The floor is a floor, so nominating an
    athlete twice, or nominating from a club that was itself only reviewed, must
    not accumulate."""
    strong = club_legitimacy(dict(registration_id="G1", federation_name="F", federation_id="1",
                                  founded_year=1970, teams_count=12, roster_url="https://a/b",
                                  proof_kind="roster", proof_status="verified"), today_year=YEAR)
    floor = strong["nomination_floor"]
    empty = application(competition_level="", years_competing=None, birth_year=None,
                        proof_kind="none", proof_status="unverified")
    if outcome(empty, floor=floor) == "admitted":
        note("nomination", "a nomination alone admits an athlete who supplied nothing")
    # a club that only reached review confers nothing at all
    for decision in ("review", "rejected", "pending"):
        if nomination_floor(99.0, decision) != 0.0:
            note("nomination", f"a {decision} club confers a floor of "
                               f"{nomination_floor(99.0, decision)}")
    # the floor cannot exceed the club's own score
    for legitimacy in (10.0, 50.0, 100.0):
        if nomination_floor(legitimacy, "verified") > legitimacy:
            note("nomination", f"floor {nomination_floor(legitimacy, 'verified')} exceeds "
                               f"club legitimacy {legitimacy}")


def check_social_cannot_lift() -> None:
    """The social score's only legal direction is towards review."""
    rank = {"rejected": 0, "pending": 0, "review": 1, "admitted": 2}
    for sport, level, years, birth, kind, status in grid():
        app = application(sport=sport, competition_level=level, years_competing=years,
                          birth_year=birth, proof_kind=kind, proof_status=status)
        quiet, loud = outcome(app, social=None), outcome(app, social=100.0)
        if rank[loud] > rank[quiet] and loud == "admitted":
            note("social", f"a social score turned {quiet} into {loud} for {app}")


# ── 7. what does the policy cost in humans? ─────────────────────────────────
# Shares are an assumption, not a measurement — the point of the sweep is the
# sensitivity, not the level. Replace with real intake data the moment it exists.
# Each archetype carries its own following. A blanket social score across the
# whole population was fine while the social-review branch was dead code, and
# badly wrong once it worked: it treated every applicant as having 85, which is
# the one input that routes a weak claim to a human, and doubled the modelled
# review queue overnight. A regional club athlete does not have an influencer's
# reach, and the model should not pretend otherwise.
POPULATION = [
    ("regional athlete, proof checked", 0.15,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="roster", proof_status="verified"), 45.0),
    ("regional athlete, proof queued", 0.25,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="roster", proof_status="pending"), 40.0),
    ("local athlete, proof queued", 0.20,
     dict(competition_level="local", years_competing=3, birth_year=2005,
          proof_kind="roster", proof_status="pending"), 30.0),
    ("national athlete, proof checked", 0.05,
     dict(competition_level="national", years_competing=7, birth_year=2000,
          proof_kind="licence", proof_status="verified"), 62.0),
    ("influencer, no proof", 0.10,
     dict(competition_level="local", years_competing=5, birth_year=1999,
          proof_kind="none", proof_status="unverified"), 92.0),
    ("incomplete form", 0.15,
     dict(competition_level="", years_competing=None, birth_year=None,
          proof_kind="none", proof_status="unverified"), 35.0),
    ("under age", 0.03,
     dict(competition_level="regional", years_competing=3, birth_year=2012,
          proof_kind="roster", proof_status="verified"), 28.0),
    ("regional athlete, no proof supplied", 0.07,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="none", proof_status="unverified"), 38.0),
]


def ops_load(admit_at: float | None = None) -> dict:
    """Outcome mix under the population above. `admit_at` shifts the threshold to
    show how sharply the queue responds."""
    import stride_api.admission as policy
    original = policy.ADMIT_AT
    if admit_at is not None:
        policy.ADMIT_AT = admit_at
    try:
        mix = {"admitted": 0.0, "review": 0.0, "rejected": 0.0, "pending": 0.0}
        for _, share, spec, social in POPULATION:
            mix[outcome(application(**spec), social=social)] += share
        return mix
    finally:
        policy.ADMIT_AT = original


def check_financial_model_is_in_step() -> None:
    """The financial model prices reviewer time off these very numbers.

    business-plan/model.py carries `admission_rate_direct` and
    `review_rate_direct`, and its Research sheet tells a reader they are "the
    ops-load output of scripts/admission_stress.py". That claim is only true
    while the two agree — retune a threshold here and the workbook would quietly
    keep costing an old funnel. So the sweep asserts it.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "business-plan"))
    try:
        from model import A as FIN
    except Exception as exc:                      # the sweep still runs without it
        note("financial", f"could not import the financial model: {exc}")
        return
    mix = ops_load()
    for label, measured, carried in (
            ("admission_rate_direct", mix["admitted"], FIN.admission_rate_direct),
            ("review_rate_direct", mix["review"], FIN.review_rate_direct)):
        if abs(measured - carried) > 0.005:
            note("financial", f"business-plan/model.py carries {label}={carried:.0%} but this "
                              f"sweep now measures {measured:.0%} — the workbook is costing a "
                              f"funnel that no longer exists")


def main() -> int:
    print("STRIDE — admission policy stress test")
    print(f"thresholds: admit {ADMIT_AT}, review {REVIEW_AT}   "
          f"evidence: {EVIDENCE_MULTIPLIER}\n")

    n = check_monotonicity()
    print(f"1. monotonicity     {n:>6,} ordered pairs checked")
    n = check_withholding()
    print(f"2. withholding      {n:>6,} blanked variants checked")
    n = check_clubs()
    print(f"3. clubs            {n:>6,} club applications and variants checked")
    n = check_decision_surface()
    print(f"4. decision surface {n:>6,} joint (credibility, proof, age, social, floor) points")
    n = check_bounds_and_idempotence()
    print(f"5. bounds           {n:>6,} scores checked in range and for stability")
    forgery = check_forgery_cost()
    check_nomination_laundering()
    check_social_cannot_lift()
    check_financial_model_is_in_step()
    print(f"6. forgery cost     unevidenced admissions: {forgery['unevidenced_admits']}")
    cheapest = forgery["cheapest_admitted"]
    if cheapest:
        print(f"   cheapest admitted claim: {cheapest['competition_level']}, "
              f"{cheapest['years_competing']} seasons, {cheapest['proof_kind']} "
              f"({cheapest['proof_status']})")

    print("\n7. ops load under the assumed applicant mix")
    print(f"   {'admit threshold':<18}{'admitted':>10}{'review':>10}{'rejected':>10}"
          f"{'pending':>10}")
    for threshold in (45.0, 50.0, ADMIT_AT, 60.0, 65.0):
        mix = ops_load(threshold)
        marker = "  <- current" if threshold == ADMIT_AT else ""
        print(f"   {threshold:<18.0f}{mix['admitted']:>9.0%}{mix['review']:>10.0%}"
              f"{mix['rejected']:>10.0%}{mix['pending']:>10.0%}{marker}")
    current = ops_load()
    per_1000 = current["review"] * 1000
    print(f"\n   {per_1000:.0f} manual reviews per 1,000 applicants."
          f"  At 4 minutes each that is {per_1000 * 4 / 60:.1f} hours per 1,000.")

    print(f"\n   sport tilt: regional reads "
          f"{cred(application(sport='padel')):.1f} in padel (agent density "
          f"{AGENT_DENSITY['padel']}) vs {cred(application(sport='football')):.1f} in football "
          f"({AGENT_DENSITY['football']})")

    print()
    if failures:
        print(f"FAILURES ({len(failures)}):")
        for f in failures[:20]:
            print("  -", f)
        if len(failures) > 20:
            print(f"  ... and {len(failures) - 20} more")
        return 1
    print("No monotonicity, withholding, forgery or nomination failures found,")
    print("and business-plan/model.py is costing the same funnel this sweep measures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
