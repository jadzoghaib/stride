"""Adversarial stress test for the admission policy.

    python scripts/admission_stress.py

Not a test suite — a search for the inputs that embarrass the policy. Four
questions, each swept exhaustively over the discrete input space rather than
spot-checked, because the interesting failures in a scoring rule are always at
combinations nobody thought to write a case for:

    1. MONOTONICITY   does more evidence, a higher level or a longer career
                      ever *lower* a score?
    2. WITHHOLDING    is there any field an applicant does better to leave blank?
    3. FORGERY COST   what is the cheapest input that gets admitted, and does
                      any zero-evidence application get in?
    4. OPS LOAD       under a plausible applicant mix, how many humans does the
                      review band cost — and how far do the thresholds move it?

A policy that is individually correct on every case and sends 60% of applicants
to a manual queue is still a broken policy, which is why (4) is here.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from stride_api.admission import (ADMIT_AT, AGENT_DENSITY, COMPETITION_LEVELS,  # noqa: E402
                                  EVIDENCE_MULTIPLIER, PROOF_STATUSES, REVIEW_AT,
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


# ── 3. what does admission cost a liar? ─────────────────────────────────────
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


# ── 4. what does the policy cost in humans? ─────────────────────────────────
# Shares are an assumption, not a measurement — the point of the sweep is the
# sensitivity, not the level. Replace with real intake data the moment it exists.
POPULATION = [
    ("regional athlete, proof checked", 0.15,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="roster", proof_status="verified")),
    ("regional athlete, proof queued", 0.25,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="roster", proof_status="pending")),
    ("local athlete, proof queued", 0.20,
     dict(competition_level="local", years_competing=3, birth_year=2005,
          proof_kind="roster", proof_status="pending")),
    ("national athlete, proof checked", 0.05,
     dict(competition_level="national", years_competing=7, birth_year=2000,
          proof_kind="licence", proof_status="verified")),
    ("influencer, no proof", 0.10,
     dict(competition_level="local", years_competing=5, birth_year=1999,
          proof_kind="none", proof_status="unverified")),
    ("incomplete form", 0.15,
     dict(competition_level="", years_competing=None, birth_year=None,
          proof_kind="none", proof_status="unverified")),
    ("under age", 0.03,
     dict(competition_level="regional", years_competing=3, birth_year=2012,
          proof_kind="roster", proof_status="verified")),
    ("regional athlete, no proof supplied", 0.07,
     dict(competition_level="regional", years_competing=4, birth_year=2002,
          proof_kind="none", proof_status="unverified")),
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
        for _, share, spec in POPULATION:
            mix[outcome(application(**spec), social=85.0)] += share
        return mix
    finally:
        policy.ADMIT_AT = original


def main() -> int:
    print("STRIDE — admission policy stress test")
    print(f"thresholds: admit {ADMIT_AT}, review {REVIEW_AT}   "
          f"evidence: {EVIDENCE_MULTIPLIER}\n")

    n = check_monotonicity()
    print(f"1. monotonicity     {n:>6,} ordered pairs checked")
    n = check_withholding()
    print(f"2. withholding      {n:>6,} blanked variants checked")
    forgery = check_forgery_cost()
    check_nomination_laundering()
    check_social_cannot_lift()
    print(f"3. forgery cost     unevidenced admissions: {forgery['unevidenced_admits']}")
    cheapest = forgery["cheapest_admitted"]
    if cheapest:
        print(f"   cheapest admitted claim: {cheapest['competition_level']}, "
              f"{cheapest['years_competing']} seasons, {cheapest['proof_kind']} "
              f"({cheapest['proof_status']})")

    print("\n4. ops load under the assumed applicant mix")
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
    print("No monotonicity, withholding, forgery or nomination failures found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
