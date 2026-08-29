"""Do the business-plan documents still agree with the model behind them?

    python scripts/doc_consistency.py

Tables inside `<!-- MODEL:key -->` markers regenerate themselves, so they cannot
drift. Prose can, and did: several figures survived the Stripe rate correction
unchanged, and two documents ended up contradicting each other about the same
number — one saying a EUR 4.99 tier retains 54% of our take, the other 47%.

So every load-bearing number written in prose is pinned here against the code
that produces it. A claim is read back out of the document with a regex and
recomputed from `model.py`; drift fails the run and names the file.

Adding a claim is cheap. The rule of thumb: if a number in a document came out
of the model, it belongs in this list or inside a MODEL marker — never loose in
a sentence with nothing watching it.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "business-plan"))

import model  # noqa: E402

A = model.A
ROWS = model.build()
VAL = model.valuation(ROWS)
Y1, Y7, Y10 = ROWS[0], ROWS[6], ROWS[9]


def retained(price: float) -> float:
    take = price * A.take_fan
    return (take - (price * A.psp_pct + A.psp_fixed_eur)) / take


def blended_cac(r: dict) -> float:
    adds = r["athlete_gross_adds"]
    return (r["cac_per_application"] * r["applications"] / adds) if adds else 0.0


def churn_gross_adds() -> tuple[float, float]:
    """Y10 fan gross adds as modelled, and at benchmark churn.

    The plan calls niche engagement its most optimistic judgement, and for a long
    time claimed being wrong cost "roughly EUR 7M of Y10 revenue". It does not:
    Y10 revenue moves by +0.07M and the fan count is identical to the digit,
    because `fans_per_athlete` is a target the model solves backwards from and
    marketing is driven by athlete adds rather than fan adds.

    What it really moves is the acquisition burden, so that is what is watched.
    A claim about the plan's central risk is the last one that should be
    unpinned — that is how it was wrong by two orders of magnitude for so long.
    """
    import copy

    import market_model

    def run(niche_factor: float) -> float:
        original = model.A.segments
        swapped = []
        for seg in original:
            clone = copy.deepcopy(seg)
            if seg is model.NICHE:
                clone.fan_churn_month = [c / market_model.NICHE_ENGAGEMENT * niche_factor
                                         for c in seg.fan_churn_month]
            swapped.append(clone)
        model.A.segments = swapped
        try:
            return model.build()[-1]["fan_gross_adds"]
        finally:
            model.A.segments = original

    return run(market_model.NICHE_ENGAGEMENT), run(1.0)


def take_rate_delta() -> float:
    """Y7 revenue forgone by charging 15% on fan revenue instead of 20%."""
    import copy
    alt = copy.deepcopy(A)
    alt.segments = A.segments          # deepcopy would detach the segment objects
    alt.take_fan = 0.20
    original, model.A = model.A, alt
    try:
        return model.build()[6]["revenue"] - Y7["revenue"]
    finally:
        model.A = original


# The capital the plan needs: the deepest point of cumulative free cash flow,
# plus the buffer the funding table applies. Quoted in three documents, and it
# was wrong in all three at once — the prose said EUR 952k and EUR 1.03M while
# the generated table right beside it said EUR 625k.
def peak_funding() -> float:
    cum = trough = 0.0
    for r in ROWS:
        cum += r["fcf"]
        trough = min(trough, cum)
    return -trough


# (document, description, regex capturing one number, expected value, tolerance)
CLAIMS: list[tuple[str, str, str, float, float]] = [
    # --- the figures that had drifted, now watched -------------------------
    ("README.md", "capital required",
     r"Capital required to fund it: €(\d+)k", peak_funding() * 1.4 / 1e3, 1.0),
    ("README.md", "first EBITDA-positive year",
     r"EBITDA turns positive in \*\*Y(\d+)\*\*",
     next((r["year"] for r in ROWS if r["ebitda"] > 0), 0), 0.1),
    ("03-financial-model.md", "capital in the prose beside the table",
     r"\*\*€(\d+)k is a small number", peak_funding() * 1.4 / 1e3, 1.0),
    ("03-financial-model.md", "scenarios base-case Y7 revenue",
     r"\| \*\*Base\*\* \| As modelled \| €([\d.]+)M", Y7["revenue"] / 1e6, 0.02),
    ("03-financial-model.md", "scenarios base-case Y7 EBITDA",
     r"\| \*\*Base\*\* \| As modelled \| €[\d.]+M \| €([\d.]+)M", Y7["ebitda"] / 1e6, 0.02),
    ("04-capital-and-valuation.md", "DCF in the prose",
     r"The DCF says €([\d.]+)M", VAL["enterprise_value"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "terminal value share of the DCF",
     r"terminal value is (\d+)% of the DCF",
     VAL["pv_terminal"] / VAL["enterprise_value"] * 100, 0.6),
    ("04-capital-and-valuation.md", "the conservative floor",
     r"worth €([\d.]+)M today", VAL["enterprise_value"] / 1e6, 0.05),

    ("01-revenue-model.md", "EUR 4.99 retains x% of take",
     r"€4\.99 tier retains (\d+)% of our take", retained(4.99) * 100, 0.5),
    ("01-revenue-model.md", "Y7 SaaS revenue",
     r"By Y7 it is €([\d.]+)M of the", Y7["rev_saas"] / 1e6, 0.01),
    ("01-revenue-model.md", "Y7 total revenue",
     r"By Y7 it is €[\d.]+M of the €([\d.]+)M", Y7["revenue"] / 1e6, 0.02),
    ("01-revenue-model.md", "SaaS as share of Y7 gross profit",
     r"which is roughly ([\d.]+)% of gross profit", Y7["rev_saas"] / Y7["gross"] * 100, 0.6),
    # This one went stale twice: it is a Y7 figure in a model that runs to Y10,
    # so it reads plausibly whichever year it was last computed from.
    ("01-revenue-model.md", "value of one point of fan take at Y7",
     r"each point of take on fan GMV is worth \*\*€([\d.]+)M", Y7["fan_gmv"] * 0.01 / 1e6, 0.02),
    ("01-revenue-model.md", "Passes crossover",
     r"cross at \*\*€([\d,]+)/month", 27 / ((A.take_fan - 0.10) - 0.28 / A.avg_fan_txn_eur), 5),

    ("02-cost-model.md", "payments vs infrastructure multiple",
     r"\*\*Payments are (\w+) times larger", Y7["psp"] / Y7["infra"], 0.6),
    ("02-cost-model.md", "Y1 applications behind one athlete",
     r"Applications behind the athlete plan \| ([\d,]+) ", Y1["applications"], 1),
    ("02-cost-model.md", "Y1 manual reviews", r"\| Manual reviews \| ([\d,]+) ", Y1["reviews"], 1),
    ("02-cost-model.md", "peak verification cost",
     r"Verification peaks at\s+€([\d.]+)k a year",
     max(r["verification"] for r in ROWS) / 1e3, 0.6),

    # --- the executive summary, and the figure it shares with 04 -----------
    # 04 said the plan needed EUR 952k while 03 and the README said 625k: the
    # same quantity, two numbers, in one document set. Nothing watched 04's copy,
    # and it went stale when working capital and capex entered the free cash
    # flow. A pitch reader finding that is a pitch reader who stops believing the
    # rest, so both places are pinned now.
    ("04-capital-and-valuation.md", "capital the plan needs",
     r"The plan needs €(\d+)k", peak_funding() * 1.4 / 1e3, 1.0),
    ("00-executive-summary.md", "capital the plan needs",
     r"The plan needs €(\d+)k", peak_funding() * 1.4 / 1e3, 1.0),
    ("00-executive-summary.md", "first EBITDA-positive year",
     r"EBITDA turns positive in \*\*Y(\d+)\*\*",
     # `0` rather than letting `next` raise: a model with no profitable year is a
     # drift report, not an import-time crash in the checker that would report it
     next((r["year"] for r in ROWS if r["ebitda"] > 0), 0), 0.1),
    ("00-executive-summary.md", "fan take rate",
     r"\*\*(\d+)% on\s+fan revenue", A.take_fan * 100, 0.1),
    ("00-executive-summary.md", "sponsorship take rate",
     r"fan revenue, (\d+)% on sponsorship\*\*", A.take_sponsorship * 100, 0.1),
    ("00-executive-summary.md", "Y10 gross adds as modelled",
     r"instead of ([\d.]+)M\*\*", churn_gross_adds()[0] / 1e6, 0.02),
    ("00-executive-summary.md", "Y10 gross adds at benchmark churn",
     r"needs \*\*([\d.]+)M gross adds", churn_gross_adds()[1] / 1e6, 0.02),
    ("00-executive-summary.md", "revenue forfeited by the 15% take",
     r"forfeits €([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.1),

    # --- the preliminary full draft ---------------------------------------
    # A draft is exactly where a figure goes stale, and this one repeats numbers
    # from six other documents. The infrastructure pair is pinned because the
    # first version of it was wrong: it quoted a EUR 3.9M naive cost from the 9x
    # egress *rate*, when total infrastructure differs by 3.6x — compute and
    # storage are unaffected by the egress decision.
    # The tier prices, pinned to the one place they are defined. They had already
    # diverged once: model.py's unit-economics table carried a EUR 14.99 tier
    # that exists nowhere else and priced the season pass at 99 against 89.
    ("stride-business-plan-draft.md", "Insider tier price",
     r"\| \*\*Insider\*\* \| €([\d.]+) \|", lambda: __import__("market_model").TIER_PRICES[1], 0.001),
    ("stride-business-plan-draft.md", "Inner circle tier price",
     r"\| \*\*Inner circle\*\* \| €([\d.]+) \|", lambda: __import__("market_model").TIER_PRICES[2], 0.001),
    ("stride-business-plan-draft.md", "season pass price",
     r"\| \*\*Season pass\*\* \| €(\d+)/yr", lambda: __import__("market_model").SEASON_PASS_EUR, 0.001),

    ("stride-business-plan-draft.md", "capital the plan needs",
     r"The plan needs €(\d+)k", peak_funding() * 1.4 / 1e3, 1.0),
    # Y5, Y6 and Y7 each anchored by position rather than by quoting their
    # neighbours. The first version hardcoded "EUR 8.40M | EUR 16.20M |" as the
    # anchor for Y7, which made two unwatched figures load-bearing: drift in Y5
    # would have failed the *Y7* claim as "not found" and named the wrong column.
    ("stride-business-plan-draft.md", "Y5 net revenue in the seven-year table",
     r"\| Net revenue \|(?: €[\d.]+M \|){4} €([\d.]+)M", ROWS[4]["revenue"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "Y6 net revenue in the seven-year table",
     r"\| Net revenue \|(?: €[\d.]+M \|){5} €([\d.]+)M", ROWS[5]["revenue"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "Y7 net revenue in the seven-year table",
     r"\| Net revenue \|(?: €[\d.]+M \|){6} €([\d.]+)M", ROWS[6]["revenue"] / 1e6, 0.02),

    # The document describes the guard that checks it, so the guard checks that
    # description too. Self-referential on purpose: this count is exactly the
    # kind of figure that goes stale the moment anyone adds a claim.
    ("stride-business-plan-draft.md", "number of pinned claims",
     r"checks \*\*(\d+) prose\s+claims", lambda: len(CLAIMS), 0.1),
    ("stride-business-plan-draft.md", "number of documents checked",
     r"prose\s+claims across (\d+)\s+documents", lambda: len({c[0] for c in CLAIMS}), 0.1),
    ("stride-business-plan-draft.md", "Y7 infrastructure, engineered",
     r"\*\*€0\.008\*\* \| \*\*€(\d+)k\*\*", ROWS[6]["infra"] / 1e3, 1.0),
    ("stride-business-plan-draft.md", "Y7 infrastructure, naive",
     r"€0\.075 \| €([\d.]+)M", ROWS[6]["infra_naive"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "Y10 gross adds at benchmark churn",
     r"needs \*\*([\d.]+)M gross adds", churn_gross_adds()[1] / 1e6, 0.02),

    ("07-open-questions.md", "EUR 4.99 retention",
     r"€4\.99 retains (\d+)% of our take", retained(4.99) * 100, 0.5),
    ("07-open-questions.md", "EUR 9.99 retention",
     r"€9\.99 retains (\d+)%", retained(9.99) * 100, 0.5),
    ("07-open-questions.md", "season pass retention",
     r"season pass retains (\d+)%", retained(89) * 100, 0.5),
    ("07-open-questions.md", "revenue forgone by 15% vs 20%",
     r"forfeits €([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.1),
    ("07-open-questions.md", "DCF headline",
     r"the DCF \(€([\d.]+)M\)", VAL["enterprise_value"] / 1e6, 0.1),

    ("11-admission-and-matching.md", "peak reviewer FTE",
     r"(\d\.\d+) of one\s+reviewer", max(r["review_fte"] for r in ROWS), 0.01),
    # Pinned beside the per-point figure above, because the two are the same
    # statement twice and a paragraph that quotes both can contradict itself:
    # it said EUR 0.92M a point and EUR 5.3M for five of them.
    ("01-revenue-model.md", "revenue added by moving 15% to 20%",
     r"15% → 20%\s+adds €([\d.]+)M", take_rate_delta() / 1e6, 0.1),

    ("11-admission-and-matching.md", "Y10 blended admission rate",
     r"admission rate climbs from 20% to (\d+)%", Y10["admit_rate"] * 100, 0.6),
]

WORDS = {"fourteen": 14, "fifteen": 15, "sixteen": 16, "twenty": 20, "ten": 10, "twelve": 12}


def check_duplicated_sport_table() -> list[str]:
    """`admission.py` copies the agent-density column out of `sport_data.py`,
    because the sport index is a planning module outside the API package. A copy
    with nothing watching it is a copy that drifts, and the admission ladder
    would quietly start reading a different sport structure than the index the
    business plan argues from."""
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    from sport_data import SPORTS
    from stride_api.admission import AGENT_DENSITY
    # Compared case-insensitively, because the lookup lower-cases the sport
    # before reading the table. A raw-key comparison called the two identical
    # while "MMA" sat in admission.py in its published capitalisation, unable to
    # match anything, so every MMA applicant was scored on the neutral fallback.
    # A guard that compares the keys but not the way they are read is not a guard.
    # Normalised for the *comparison*, because that is how admission.py reads the
    # key — but stray whitespace is reported rather than absorbed. `sport_index`
    # looks these names up exactly, so a trailing space there falls back to a 1.0
    # multiplier in silence, and a guard that quietly strips it has hidden the
    # very typo it exists to find.
    source = {name.lower().strip(): density for name, _, _, density in SPORTS}
    out = [f"sport_data.py SPORTS name {name!r} has stray whitespace — sport_index "
           f"looks it up exactly and would fall back to a neutral multiplier"
           for name, *_ in SPORTS if name != name.strip()]
    for sport, density in AGENT_DENSITY.items():
        if sport != sport.lower().strip():
            out.append(f"admission.py AGENT_DENSITY key {sport!r} is not lower-case and "
                       f"stripped, so the lookup can never match it")
        if source.get(sport.lower().strip()) != density:
            out.append(f"admission.py AGENT_DENSITY[{sport!r}]={density} but sport_data.py "
                       f"says {source.get(sport.lower().strip())}")
    for sport in set(source) - {k.lower().strip() for k in AGENT_DENSITY}:
        out.append(f"sport_data.py has {sport!r}; admission.py does not, so it falls back to neutral")
    return out


def check_market_model_chain() -> list[str]:
    """The workbook says Comparables -> MarketModel -> Assumptions. Nothing in
    the workbook enforced it: MarketModel computes each figure from the
    published ones, and Assumptions carries a typed number that happens to
    match, so changing a comparable moved the derivation and left every
    assumption downstream where it was.

    The literals are not an independent guess — they are this derivation
    rounded to the precision each is written at, so the comparison is exact.
    A percentage tolerance was the first attempt and was worse: it let a
    comparable move a little at a time without ever tripping, which is the
    silent drift this exists to stop.
    """
    sys.path.insert(0, str(ROOT / "business-plan"))
    import market_model

    mature = {
        "niche_fans_per_athlete": A.segments[0].fans_per_athlete[-1],
        "popular_fans_per_athlete": A.segments[1].fans_per_athlete[-1],
        "niche_fan_arpu_month": A.segments[0].fan_arpu_month[-1],
        "popular_fan_arpu_month": A.segments[1].fan_arpu_month[-1],
        "niche_fan_churn_month": A.segments[0].fan_churn_month[-1],
        "popular_fan_churn_month": A.segments[1].fan_churn_month[-1],
    }
    produced = market_model.derived()
    # Driven by the expected names, not by whatever the derivation happened to
    # return: iterating the outputs meant a dropped one was silently not checked,
    # and a guard that can quietly check nothing is the failure mode of every
    # guard in this repository so far.
    out = [f"market_model.derived() no longer produces {name!r}, so nothing checks it"
           for name in mature if name not in produced]
    out += [f"market_model.derived() produces unexpected {name!r}, which nothing checks"
            for name in produced if name not in mature]

    for name in mature:
        if name not in produced:
            continue
        digits = market_model.PRECISION[name]
        derived, literal = produced[name], mature[name]
        # The rounded derivation against the literal itself, not against the
        # rounded literal: rounding both sides also accepts a literal carrying
        # precision it does not declare — 37.4 would pass as 37 while the model
        # ran on 37.4 and every document said 37.
        if round(derived, digits) != literal:
            out.append(f"model.py {name} is {literal:,.3f} but the MarketModel derivation "
                       f"from comparables_data.py gives {derived:,.3f} — the evidence chain "
                       f"the workbook advertises is broken")
    return out


def main() -> int:
    failures = check_duplicated_sport_table() + check_market_model_chain()
    for doc, label, pattern, expected, tol in CLAIMS:
        path = ROOT / "business-plan" / doc
        text = path.read_text(encoding="utf-8")
        m = re.search(pattern, text)
        if not m:
            failures.append(f"{doc}: claim not found — {label}  /{pattern}/")
            continue
        # `expected` may be a callable for a claim about CLAIMS itself, which
        # cannot be evaluated while the list is still being built.
        expected = expected() if callable(expected) else expected
        raw = m.group(1)
        # `([\d.]+)` can swallow a sentence-ending full stop, and a `(\d+)`
        # pattern against a prose figure that later gains a decimal silently
        # captures only the integer part and passes on a truncated number.
        found = float(WORDS.get(raw, raw.replace(",", "").rstrip(".")))
        if abs(found - expected) > tol:
            failures.append(f"{doc}: {label} says {found:,.2f}, model says {expected:,.2f}")

    print(f"checked {len(CLAIMS)} prose claims across "
          f"{len({c[0] for c in CLAIMS})} documents, the duplicated sport table, "
          f"and the Comparables -> MarketModel -> Assumptions chain")
    if failures:
        print(f"\nDRIFT ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("every figure written in prose still matches the model behind it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
