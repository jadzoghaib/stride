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


def at_take(rate: float) -> dict:
    """Year 7 with the fan take rate moved, everything else held.

    Both ends of the corridor are real competitor rates now -- Patreon's
    published 10% below, OnlyFans' derived 20% above -- so the doc quotes a
    table rather than one sentence, and every cell in it is pinned here.
    """
    import copy
    alt = copy.deepcopy(A)
    alt.segments = A.segments          # deepcopy would detach the segment objects
    alt.take_fan = rate
    original, model.A = model.A, alt
    try:
        return model.build()[6]
    finally:
        model.A = original


TAKE_20 = at_take(0.20)
TAKE_10 = at_take(0.10)


def take_rate_delta() -> float:
    """Y7 revenue forgone by charging 15% on fan revenue instead of 20%."""
    return TAKE_20["revenue"] - Y7["revenue"]


def _trough(rows: list[dict]) -> float:
    """Deepest point of cumulative free cash flow, as a positive number."""
    cum = trough = 0.0
    for r in rows:
        cum += r["fcf"]
        trough = min(trough, cum)
    return -trough


def without_vat() -> list[dict]:
    """The plan re-run as if we were *not* the deemed supplier.

    VAT is in the model now: fan prices are treated as inclusive, because Art 9a
    makes a platform that both sets the terms and processes the payment the
    deemed supplier and the presumption cannot be rebutted. So the counterfactual
    has flipped. It used to be "what if VAT applies"; the interesting question
    now is what the plan looks like if the reading turns out to be wrong and the
    take is charged on a net price after all -- which is upside, and the only
    direction a surprise here can go.
    """
    import copy
    alt = copy.deepcopy(A)
    alt.segments = A.segments      # deepcopy would detach the segment objects
    alt.vat_rate_fan = 0.0
    original, model.A = model.A, alt
    try:
        return model.build()
    finally:
        model.A = original


NO_VAT = without_vat()
NO_VAT_Y7 = NO_VAT[6]


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


def egress_delta(year: int) -> float:
    """What the naive CDN costs over the zero-egress one, in a given year."""
    r = ROWS[year - 1]
    return r["infra_naive"] - r["infra"]


def egress_cumulative() -> float:
    return sum(r["infra_naive"] - r["infra"] for r in ROWS)


def startup_tax_saving() -> float:
    """What the Ley de Startups 15% rate is worth against the standard 25%.

    Section 04 claimed EUR 209k "across Y4-Y7" -- a window the model does not
    use and a figure nothing produced. The low rate lands on the first four
    TAXABLE years, which the slower ramp puts at Y6-Y9.
    """
    return sum(r["taxable"] * (A.tax_high - A.tax_low)
               for r in ROWS if abs(r["tax_rate"] - A.tax_low) < 1e-9)


def rounds_before_series_a() -> float:
    return sum(rd["amount"] for rd in model.ROUNDS if rd["stage"] != "Series A")


DILUTION = {d["stage"]: d for d in model.dilution()}

# The "discounted to today" column of the exit-multiple table in 04. Rebuilding
# the arithmetic here was a second source of truth: changing a multiple in
# model.render() would have left this guard approving the old prose. It reads
# the shared helper instead.
MULTIPLES = [e["today"] for e in model.exit_values(ROWS)]


# (document, description, regex capturing one number, expected value, tolerance)
CLAIMS: list[tuple[str, str, str, float, float]] = [
    # --- the figures that had drifted, now watched -------------------------
    # --- the plan README's headline table ---------------------------------
    # Twenty-five figures in the table a reader opens first, and none of them
    # were watched. Revenue happened to survive the egress correction; EBITDA,
    # one row below it, drifted in four cells out of five. Exactly the fault
    # already recorded against the draft's two headline tables, in a third
    # table nobody had thought to pin.
    # Tolerances are HALF THE LAST PRINTED PLACE, not a round number that looks
    # small. Written first with 0.01 against figures printed to two decimals,
    # which accepts a full display step of error: all four stale EBITDA cells
    # this table's correction was about passed the pins added to catch them.
    # A pin looser than its own display precision reports "checked" and checks
    # nothing.
    *[("README.md", f"headline table, Y{y} active athletes",
       r"\| Active athletes \(year end\) \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       ROWS[y - 1]["athletes"], 0.5) for n, y in enumerate((1, 3, 5, 7, 10))],
    *[("README.md", f"headline table, Y{y} paying fans",
       r"\| Paying fans \(year end\) \|" + r" \d+k \|" * n + r" (\d+)k",
       ROWS[y - 1]["paying_fans"] / 1e3, 0.5) for n, y in enumerate((1, 3, 5, 7, 10))],
    *[("README.md", f"headline table, Y{y} net revenue",
       r"\| \*\*Net revenue\*\* \|" + r" \*\*€[\d.]+M\*\* \|" * n + r" \*\*€([\d.]+)M\*\*",
       ROWS[y - 1]["revenue"] / 1e6, 0.005) for n, y in enumerate((1, 3, 5, 7, 10))],
    *[("README.md", f"headline table, Y{y} headcount",
       r"\| Headcount \|" + r" [\d.]+ \|" * n + r" ([\d.]+)",
       ROWS[y - 1]["headcount"], 0.05) for n, y in enumerate((1, 3, 5, 7, 10))],

    # EBITDA needs one regex per column rather than a comprehension: the row
    # mixes thousands and millions, and the sign is a real minus (U+2212), not
    # a hyphen. The sign sits in the pattern rather than the capture so a
    # flipped sign fails as "claim not found" instead of crashing float().
    ("README.md", "headline table, Y1 EBITDA",
     r"\| EBITDA \| −€(\d+)k", abs(ROWS[0]["ebitda"]) / 1e3, 0.5),
    ("README.md", "headline table, Y3 EBITDA",
     r"\| EBITDA \| −€\d+k \| −€(\d+)k", abs(ROWS[2]["ebitda"]) / 1e3, 0.5),
    ("README.md", "headline table, Y5 EBITDA",
     r"\| EBITDA \| −€\d+k \| −€\d+k \| €([\d.]+)M",
     ROWS[4]["ebitda"] / 1e6, 0.005),
    ("README.md", "headline table, Y7 EBITDA",
     r"\| EBITDA \| −€\d+k \| −€\d+k \| €[\d.]+M \| €([\d.]+)M",
     ROWS[6]["ebitda"] / 1e6, 0.005),
    ("README.md", "headline table, Y10 EBITDA",
     r"\| EBITDA \|(?: −?€[\d.]+[kM] \|){4} €([\d.]+)M",
     ROWS[9]["ebitda"] / 1e6, 0.005),

    # The fixed-fee mechanic the README leads with. Correct, and unpinned.
    ("README.md", "what a €4.99 tier retains",
     r"€4\.99 tier we keep (\d+)%", retained(4.99) * 100, 0.5),
    ("README.md", "what a €9.99 tier retains",
     r"At €9\.99 we\nkeep (\d+)%", retained(9.99) * 100, 0.5),

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
     r"\*\*Payments are nearly (\w+) times larger", Y7["psp"] / Y7["infra"], 0.6),
    ("02-cost-model.md", "infrastructure as a share of Y7 revenue",
     r"Infrastructure is ([\d.]+)% of revenue",
     100 * Y7["infra"] / Y7["revenue"], 0.05),
    # 02's team table never came onto the slower plan: it ran to 50 FTE by Y7
    # against the model's 22, with people cost stale to match, because nothing
    # watched either row. Both are per-year now, seven columns each.
    *[("02-cost-model.md", f"team table, Y{y} headcount",
       r"\| Headcount \(FTE\) \|" + r" [\d.]+ \|" * (y - 1) + r" ([\d.]+)",
       ROWS[y - 1]["headcount"], 0.05) for y in range(1, 8)],
    *[("02-cost-model.md", f"team table, Y{y} people cost",
       r"\| People cost \|" + r" €[\d.]+[kM] \|" * (y - 1) + r" €(\d+)k",
       ROWS[y - 1]["people"] / 1e3, 0.5) for y in range(1, 6)],
    *[("02-cost-model.md", f"team table, Y{y} people cost",
       r"\| People cost \|" + r" €[\d.]+[kM] \|" * (y - 1) + r" €([\d.]+)M",
       ROWS[y - 1]["people"] / 1e6, 0.005) for y in (6, 7)],

    # --- 12 Operations Plan (ESADE section 7) ----------------------------
    *[("12-operations-plan.md", f"operations volume, Y{y} applications",
       r"\| Applications \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       ROWS[y - 1]["applications"], 0.5) for n, y in enumerate((1, 3, 5, 7))],
    *[("12-operations-plan.md", f"operations volume, Y{y} manual reviews",
       r"\| Sent to human review \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       ROWS[y - 1]["reviews"], 0.5) for n, y in enumerate((1, 3, 5, 7))],
    *[("12-operations-plan.md", f"operations volume, Y{y} admission rate",
       r"\| Admission rate \|" + r" [\d.]+% \|" * n + r" ([\d.]+)%",
       100 * ROWS[y - 1]["admit_rate"], 0.05) for n, y in enumerate((1, 3, 5, 7))],
    *[("12-operations-plan.md", f"operations volume, Y{y} review FTE",
       r"\| \*\*Review FTE required\*\* \|" + r" \*\*[\d.]+\*\* \|" * n + r" \*\*([\d.]+)\*\*",
       ROWS[y - 1]["review_fte"], 0.005) for n, y in enumerate((1, 3, 5, 7))],

    ("12-operations-plan.md", "what the startup tax rate is worth",
     r"worth \*\*€([\d.]+)M across Y6–Y9\*\*", startup_tax_saving() / 1e6, 0.005),
    ("12-operations-plan.md", "Y7 payment processing",
     r"\| Payment processing \| €([\d.]+)M \|", Y7["psp"] / 1e6, 0.005),
    ("12-operations-plan.md", "Y7 infrastructure",
     r"\| Infrastructure \| €(\d+)k \|", Y7["infra"] / 1e3, 0.5),
    ("12-operations-plan.md", "infrastructure as a share of Y7 revenue",
     r"Infrastructure is ([\d.]+)% of revenue",
     100 * Y7["infra"] / Y7["revenue"], 0.05),
    ("12-operations-plan.md", "what a €4.99 tier retains",
     r"\| €4\.99 \| €0\.75 \| €0\.25 \+ 1\.9% \| \*\*(\d+)%\*\*",
     retained(4.99) * 100, 0.5),
    ("12-operations-plan.md", "what a €9.99 tier retains",
     r"\| €9\.99 \| €1\.50 \| €0\.25 \+ 1\.9% \| \*\*(\d+)%\*\*",
     retained(9.99) * 100, 0.5),

    # --- 13 Organization and HR (ESADE section 8) -------------------------
    *[("13-organization-and-hr.md", f"HR table, Y{y} headcount",
       r"\| Headcount \(FTE\) \|" + r" [\d.]+ \|" * (y - 1) + r" ([\d.]+)",
       ROWS[y - 1]["headcount"], 0.05) for y in range(1, 8)],
    *[("13-organization-and-hr.md", f"HR table, Y{y} people cost",
       r"\| People cost \|" + r" €[\d.]+[kM] \|" * (y - 1) + r" €(\d+)k",
       ROWS[y - 1]["people"] / 1e3, 0.5) for y in range(1, 6)],
    *[("13-organization-and-hr.md", f"HR table, Y{y} people cost",
       r"\| People cost \|" + r" €[\d.]+[kM] \|" * (y - 1) + r" €([\d.]+)M",
       ROWS[y - 1]["people"] / 1e6, 0.005) for y in (6, 7)],

    ("13-organization-and-hr.md", "Y10 headcount",
     r"Growth to (\d+) FTE by Y10", ROWS[9]["headcount"], 0.5),
    ("13-organization-and-hr.md", "Y7 revenue against the Y7 team",
     r"reaches \*\*€([\d.]+)M of revenue at Y7", Y7["revenue"] / 1e6, 0.05),
    ("13-organization-and-hr.md", "Y7 headcount in prose",
     r"of revenue at Y7 with (\d+) people", ROWS[6]["headcount"], 0.5),
    ("13-organization-and-hr.md", "founders held after the pre-seed",
     r"(\d+)% held after the 2% advisory grant",
     DILUTION["Pre-seed"]["held"] * 100, 0.5),
    ("13-organization-and-hr.md", "founders held after the seed",
     r"\| \*\*Seed\*\* \(€2\.0M, optional\) \|[^|]*\| (\d+)%",
     DILUTION["Seed (optional)"]["held"] * 100, 0.5),
    ("13-organization-and-hr.md", "founders held after the Series A",
     r"\| \*\*Series A\*\* \(€8\.0M\) \|[^|]*\| (\d+)%",
     DILUTION["Series A"]["held"] * 100, 0.5),
    # Anchored to its own row. `\*\*~(\d+)%\*\*` matched any bold ~NN% in the
    # file, so an unrelated figure added above it would have been checked
    # against the ESOP number without anyone noticing.
    ("13-organization-and-hr.md", "equity retained after the ESOP",
     r"\| Post-ESOP \|[^|]*\|\s*\*\*~(\d+)%\*\*",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("13-organization-and-hr.md", "revenue forfeited by the 15% take",
     r"forfeits \*\*€([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.05),

    ("14-legal-and-growth.md", "what the startup tax rate is worth",
     r"worth €([\d.]+)M across Y6–Y9", startup_tax_saving() / 1e6, 0.005),
    ("14-legal-and-growth.md", "Y10 EBITDA",
     r"€([\d.]+)M EBITDA by Y10", ROWS[9]["ebitda"] / 1e6, 0.05),

    # --- 15 Primary research (ESADE section 5.1.4) -------------------------
    ("15-market-research.md", "Y7 admission rate, the value the sentence ends on",
     r"\*\*20\.0% in Y1 to ([\d.]+)% by", 100 * ROWS[6]["admit_rate"], 0.05),

    # The risk register restates two cost figures the recalibration moved and
    # nothing watched: R6 quoted PSP at Y7 and R10 infra as a share of revenue.
    ("stride-business-plan-draft.md", "R6 payment processing at Y7",
     r"€([\d.]+)M at Y7\. Multi-PSP", Y7["psp"] / 1e6, 0.005),
    ("stride-business-plan-draft.md", "R10 infrastructure as a share of revenue",
     r"Infra is ([\d.]+)% of Y7 revenue", 100 * Y7["infra"] / Y7["revenue"], 0.05),

    # --- the ESADE submission body ----------------------------------------
    # The document that gets marked. It restates figures from fourteen other
    # files, so it is the likeliest place for a stale number to reach an
    # examiner, and it is pinned harder than any of them.
    ("esade-body.md", "capital the plan needs",
     r"The plan needs €(\d+)k", peak_funding() * 1.4 / 1e3, 0.5),
    ("esade-body.md", "the cash trough",
     r"a €(\d+)k cash\s+trough in Y4", peak_funding() / 1e3, 0.5),
    ("esade-body.md", "the pre-seed ask",
     r"\*\*The ask is €(\d+)k at €2\.5M pre-money\.\*\*",
     model.ROUNDS[0]["amount"] / 1e3, 0.5),
    ("esade-body.md", "spare over the trough",
     r"clears the trough itself with\s+€(\d+)k to spare",
     (model.ROUNDS[0]["amount"] - peak_funding()) / 1e3, 0.5),
    ("esade-body.md", "first EBITDA-positive year",
     r"EBITDA turns positive in \*\*Y(\d+)\*\*",
     next((r["year"] for r in ROWS if r["ebitda"] > 0), 0), 0.1),
    ("esade-body.md", "fan take rate",
     r"\*\*(\d+)% on\s+fan revenue", A.take_fan * 100, 0.1),
    ("esade-body.md", "sponsorship take rate",
     r"fan revenue, (\d+)% on sponsorship\*\*", A.take_sponsorship * 100, 0.1),
    ("esade-body.md", "Y3 gross margin",
     r"climbs from (\d+)% in Y3", 100 * ROWS[2]["gross"] / ROWS[2]["revenue"], 0.6),
    ("esade-body.md", "Y10 gross margin",
     r"to \*\*(\d+)% by Y10\*\*", 100 * Y10["gross"] / Y10["revenue"], 0.6),

    # the seven-year P&L, every cell
    *[("esade-body.md", f"P&L, Y{y} net revenue",
       r"\| Net revenue \|" + r" [\d,]+ \|" * (y - 1) + r" ([\d,]+)",
       ROWS[y - 1]["revenue"] / 1e3, 0.5) for y in range(1, 8)],
    *[("esade-body.md", f"P&L, Y{y} EBITDA",
       r"\| \*\*EBITDA\*\* \|" + r" \*\*−?[\d,]+\*\* \|" * (y - 1) + r" \*\*(−?[\d,]+)\*\*",
       ROWS[y - 1]["ebitda"] / 1e3, 0.5) for y in range(1, 8)],

    # the sales forecast
    *[("esade-body.md", f"forecast, Y{y} active athletes",
       r"\| Active athletes \(year end\) \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       ROWS[y - 1]["athletes"], 0.5) for n, y in enumerate((1, 3, 5, 7, 10))],
    *[("esade-body.md", f"forecast, Y{y} net revenue",
       r"\| \*\*Net revenue\*\* \|" + r" \*\*€[\d.]+M\*\* \|" * n + r" \*\*€([\d.]+)M\*\*",
       ROWS[y - 1]["revenue"] / 1e6, 0.005) for n, y in enumerate((1, 3, 5, 7, 10))],

    ("esade-body.md", "the DCF floor",
     r"The DCF says \*\*€([\d.]+)M\*\* today", VAL["enterprise_value"] / 1e6, 0.005),
    ("esade-body.md", "revenue forfeited by the 15% take",
     r"forfeits €([\d.]+)M of Y7\s+revenue", take_rate_delta() / 1e6, 0.05),
    ("esade-body.md", "what the startup tax rate is worth",
     r"worth €([\d.]+)M\s+across Y6–Y9", startup_tax_saving() / 1e6, 0.005),
    ("esade-body.md", "Y10 gross adds at benchmark churn",
     r"needs 0\.79M gross adds a year instead of\s+>?\s*([\d.]+)M",
     churn_gross_adds()[0] / 1e6, 0.02),
    ("esade-body.md", "payment processing as a share of Y7 revenue",
     r"\*\*Payment processing is (\d+)% of Y7 revenue",
     100 * Y7["psp"] / Y7["revenue"], 0.6),

    # The sales forecast's sponsor rows. The first version of this table called
    # the platform sponsor count "paying sponsors", overstating paying
    # customers fivefold; building the KPI sheet is what surfaced it.
    *[("esade-body.md", f"forecast, Y{y} sponsors on the platform",
       r"\| Sponsors on the platform \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       A.sponsors[y - 1], 0.5) for n, y in enumerate((1, 3, 5, 7, 10))],
    *[("esade-body.md", f"forecast, Y{y} sponsors paying SaaS",
       r"\| of which paying SaaS \|" + r" [\d,]+ \|" * n + r" ([\d,]+)",
       ROWS[y - 1]["paying_sponsors"], 0.6) for n, y in enumerate((1, 3, 5, 7, 10))],
    ("esade-body.md", "Y3 sponsors paying SaaS, in the objectives table",
     r"3,000 athletes, (\d+) sponsors paying SaaS",
     ROWS[2]["paying_sponsors"], 0.6),
    ("esade-body.md", "workbook formula count",
     r"evaluates all ([\d,]+) workbook\s+formulas", 2520, 0.5),

    # The pro forma cash flow the outline requires at 9.3. Read from the
    # workbook, so the body cannot disagree with the statement it came from.
    ("esade-body.md", "Y7 free cash flow",
     r"\| \*\*Free Cash Flow\*\* \|(?: \*\*−?€[\d.,]+[kM]\*\* \|){3} \*\*€([\d.]+)M\*\*",
     ROWS[6]["fcf"] / 1e6, 0.005),
    ("esade-body.md", "Y7 operating cash flow",
     r"\| \*\*Operating Cash Flow\*\* \|(?: \*\*−?€[\d.,]+[kM]\*\* \|){3} \*\*€([\d.]+)M\*\*",
     ROWS[6]["operating_cf"] / 1e6, 0.005),
    ("esade-body.md", "Y7 capital expenditure",
     r"\| Capital expenditure \|(?: −€[\d.,]+k \|){3} −€(\d+)k",
     ROWS[6]["capex"] / 1e3, 0.5),

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
    # "sits in the low 70s" described a margin that starts at 64%. Both ends of
    # the curve are pinned now, because a range in prose is two stale figures
    # waiting to happen rather than one.
    ("00-executive-summary.md", "Y3 gross margin",
     r"climbs\nfrom (\d+)% in Y3", 100 * ROWS[2]["gross"] / ROWS[2]["revenue"], 0.6),
    ("00-executive-summary.md", "Y10 gross margin",
     r"to \*\*(\d+)% by Y10\*\*", 100 * Y10["gross"] / Y10["revenue"], 0.6),

    ("00-executive-summary.md", "Y10 gross adds as modelled",
     r"instead of ([\d.]+)M\*\*", churn_gross_adds()[0] / 1e6, 0.02),
    ("00-executive-summary.md", "Y10 gross adds at benchmark churn",
     r"needs \*\*([\d.]+)M gross adds", churn_gross_adds()[1] / 1e6, 0.02),
    ("00-executive-summary.md", "revenue forfeited by the 15% take",
     r"forfeits €([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.1),

    # --- the raise schedule, and what it clears ---------------------------
    # The pre-seed went from EUR 400k to EUR 600k and the documents split three
    # ways: the draft moved, the workbook did not (it was still raising 400k in
    # Y1/Y3/Y5), and 00/04/07 kept the old ask next to the new capital need. The
    # amount now has one home in model.ROUNDS and every restatement is watched.
    ("00-executive-summary.md", "the pre-seed ask",
     r"\*\*€(\d+)k pre-seed at €2\.5M pre-money\.\*\*",
     model.ROUNDS[0]["amount"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the pre-seed ask",
     r"\| \*\*Pre-seed\*\* \| \*\*€(\d+)k\*\*", model.ROUNDS[0]["amount"] / 1e3, 1.0),
    ("stride-business-plan-draft.md", "the pre-seed ask",
     r"\| \*\*Pre-seed\*\* \| \*\*€(\d+)k\*\*", model.ROUNDS[0]["amount"] / 1e3, 1.0),

    ("00-executive-summary.md", "raised before a Series A",
     r"raise €([\d.]+)M before a Series A", rounds_before_series_a() / 1e6, 0.05),
    ("04-capital-and-valuation.md", "raised before a Series A",
     r"The rounds above raise €([\d.]+)M before Series A",
     rounds_before_series_a() / 1e6, 0.05),
    ("07-open-questions.md", "raised before a Series A",
     r"or the €([\d.]+)M the rounds imply", rounds_before_series_a() / 1e6, 0.05),
    ("07-open-questions.md", "capital the plan needs",
     r"Raise €(\d+)k, or the", peak_funding() * 1.4 / 1e3, 1.0),

    # The trough is the number the raise has to clear, so it is quoted in four
    # places and was right in one of them.
    ("00-executive-summary.md", "the cash trough",
     r"\*\*€(\d+)k cash trough in Y4\*\*", peak_funding() / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the cash trough",
     r"\*\*€(\d+)k trough in Y4\*\*", peak_funding() / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the trough the grant stack covers",
     r"covers most of the €(\d+)k", peak_funding() / 1e3, 1.0),
    ("README.md", "peak burn",
     r"peak burn €(\d+)k", peak_funding() / 1e3, 1.0),

    # The dilution path, cell by cell. It was typed by hand and its later rows
    # did not follow from its earlier ones under any reading of them.
    ("04-capital-and-valuation.md", "pre-seed post-money",
     r"\| Pre-seed \| €600k \| €2\.5M \| €([\d.]+)M \|",
     DILUTION["Pre-seed"]["post"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "pre-seed investor stake",
     r"\| Pre-seed \| €600k \| €2\.5M \| €3\.1M \| ([\d.]+)% \|",
     DILUTION["Pre-seed"]["stake"] * 100, 0.1),
    ("04-capital-and-valuation.md", "founders held after the pre-seed",
     r"€3\.1M \| 19\.4% \| (\d+)% \(after 2% advisory\)",
     DILUTION["Pre-seed"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after the seed",
     r"\| Seed \*\(optional\)\* \| €2\.0M \| €10M \| €12M \| 16\.7% \| (\d+)% \|",
     DILUTION["Seed (optional)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after the Series A",
     r"\| Series A \| €8\.0M \| €40M \| €48M \| 16\.7% \| (\d+)% \|",
     DILUTION["Series A"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after the ESOP",
     r"\| ESOP \(cumulative\) \| — \| — \| — \| 10% \| \*\*~(\d+)%\*\* \|",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "equity retained through the Series A",
     r"Retaining ~(\d+)% through Series A",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),

    # The founder-hurdle paragraph. Its old version multiplied a retention the
    # dilution table did not support by an enterprise value nothing produced.
    ("04-capital-and-valuation.md", "equity retained through the Series A, in prose",
     r"a founder retaining ~(\d+)% through the Series A",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "the founder's share of the DCF floor",
     r"\*\*€([\d.]+)M against the DCF floor",
     DILUTION["ESOP (cumulative)"]["held"] * VAL["enterprise_value"] / 1e6, 0.02),
    # The two ends of the founder's stake against the exit multiples. Derived
    # from the dilution cascade and a generated table, and quoted in prose --
    # which is the combination that goes stale.
    ("04-capital-and-valuation.md", "founder stake at the lowest exit multiple",
     r"and €([\d.]+)–[\d.]+M against the exit multiples",
     DILUTION["ESOP (cumulative)"]["held"] * min(MULTIPLES) / 1e6, 0.08),
    ("04-capital-and-valuation.md", "founder stake at the highest exit multiple",
     r"and €[\d.]+–([\d.]+)M against the exit multiples",
     DILUTION["ESOP (cumulative)"]["held"] * max(MULTIPLES) / 1e6, 0.08),

    # Unpinned figures that the egress correction moved and review caught:
    # the gap between the ask and the pre-seed, and G11's restatement of the
    # Y7 infrastructure number from the table three sections above it.
    ("04-capital-and-valuation.md", "the gap between the ask and the pre-seed",
     r"the €(\d+)k gap is what the non-dilutive stack",
     (peak_funding() * 1.4 - model.ROUNDS[0]["amount"]) / 1e3, 1.0),
    ("stride-business-plan-draft.md", "Y7 infrastructure in the G11 callout",
     r"€2\.55M against €(\d+)k at Y7", Y7["infra"] / 1e3, 1.0),

    ("04-capital-and-valuation.md", "the DCF floor itself",
     r"against the DCF floor of €([\d.]+)M\*\*", VAL["enterprise_value"] / 1e6, 0.005),

    ("04-capital-and-valuation.md", "what the startup tax rate is worth",
     r"worth €([\d.]+)M across Y6–Y9", startup_tax_saving() / 1e6, 0.005),

    # --- the egress decision, quoted in four documents ---------------------
    # Every one of these was stale, and the draft's prose contradicted a table
    # two lines above it: EUR 0.81M against EUR 344k is not a EUR 1.1M gap.
    # Every cell of the egress table, anchored by position rather than by
    # quoting its neighbours. Written the other way round first, which made ten
    # unwatched cells load-bearing: drift in the Y3 column would have failed the
    # *Y7* claim as "not found" and named the wrong year.
    *[("02-cost-model.md", f"egress table, Y{y} infrastructure (zero-egress)",
       r"\| AWS \+ zero-egress CDN \|" + r" €\d+k \|" * n + r" \*?\*?€(\d+)k",
       ROWS[y - 1]["infra"] / 1e3, 1.0) for n, y in enumerate((1, 3, 5, 7))],
    *[("02-cost-model.md", f"egress table, Y{y} infrastructure (CloudFront list)",
       r"\| AWS \+ CloudFront list price \|" + r" €\d+k \|" * n + r" \*?\*?€(\d+)k",
       ROWS[y - 1]["infra_naive"] / 1e3, 1.0) for n, y in enumerate((1, 3, 5, 7))],
    *[("02-cost-model.md", f"egress table, Y{y} annual difference",
       r"\| \*\*Annual difference\*\* \|" + r" €\d+k \|" * n + r" \*?\*?€(\d+)k",
       egress_delta(y) / 1e3, 1.0) for n, y in enumerate((1, 3, 5, 7))],
    # On avg_fans, like the model: a fan consumes bandwidth for the months
    # they are subscribed, so the year-end count bills the whole year for
    # people who joined in November. These two pins carried the old base and
    # would have gone on approving it.
    ("02-cost-model.md", "Y7 bandwidth at CloudFront list",
     r"\*\*the bandwidth alone is €(\d+)k\*\*",
     Y7["avg_fans"] * A.gb_per_fan_month * 12 * A.egress_eur_per_gb_naive / 1e3, 1.0),
    ("02-cost-model.md", "Y7 bandwidth behind a zero-egress CDN",
     r"the same bytes cost \*\*€(\d+)k\*\*",
     Y7["avg_fans"] * A.gb_per_fan_month * 12 * A.egress_eur_per_gb / 1e3, 1.0),
    ("02-cost-model.md", "Y7 average paying fans, the egress driver",
     r"an average of (\d+)k paying fans", Y7["avg_fans"] / 1e3, 1.0),
    ("02-cost-model.md", "the Y7 compute and storage floor",
     r"they add the €(\d+)k of AWS compute", A.aws_base_month[6] * 12 / 1e3, 1.0),
    ("02-cost-model.md", "the Y7 egress difference",
     r"\*\*€(\d+)k a year is most of", egress_delta(7) / 1e3, 1.0),
    ("02-cost-model.md", "the trough the egress difference is compared to",
     r"most of this plan's entire €(\d+)k cash trough", peak_funding() / 1e3, 1.0),
    ("README.md", "the trough the egress difference is compared to",
     r"this plan's entire €(\d+)k cash trough", peak_funding() / 1e3, 1.0),
    ("02-cost-model.md", "the egress difference across the plan",
     r"— €([\d.]+)M across the ten\s+years", egress_cumulative() / 1e6, 0.05),
    ("README.md", "the Y7 egress difference",
     r"costs \*\*€(\d+)k more in Y7\*\*", egress_delta(7) / 1e3, 1.0),
    ("README.md", "the egress difference across the plan",
     r"more in Y7\*\* — and €([\d.]+)M", egress_cumulative() / 1e6, 0.05),
    ("stride-business-plan-draft.md", "the Y7 egress difference",
     r"is \*\*€(\d+)k a year at Y7\*\*", egress_delta(7) / 1e3, 1.0),
    ("stride-business-plan-draft.md", "the egress difference across the plan",
     r"\*\*€([\d.]+)M cumulative across the plan\*\*", egress_cumulative() / 1e6, 0.05),
    ("stride-business-plan-draft.md", "the infrastructure ratio",
     r"infrastructure differs by \*\*([\d.]+)×\*\*",
     Y7["infra_naive"] / Y7["infra"], 0.05),
    ("stride-business-plan-draft.md", "gross margin points lost to naive egress",
     r"\*\*([\d.]+) points of gross margin at Y7\*\*",
     100 * egress_delta(7) / Y7["revenue"], 0.1),

    # --- the acquisition machine ------------------------------------------
    # Stated in thousands of fans and left on the old ramp, where it read as
    # though the plan acquired 831k fans a year.
    ("03-financial-model.md", "Y7 fan gross adds",
     r"In Y7 we acquire\n(\d+)k fans", Y7["fan_gross_adds"] / 1e3, 1.0),
    ("03-financial-model.md", "Y7 paying fans",
     r"fans to finish with (\d+)k", Y7["paying_fans"] / 1e3, 1.0),
    ("03-financial-model.md", "Y7 fans churned",
     r"having lost (\d+)k", Y7["fans_churned"] / 1e3, 1.0),

    # --- the preliminary full draft ---------------------------------------
    # A draft is exactly where a figure goes stale, and this one repeats numbers
    # from six other documents. The infrastructure pair is pinned because the
    # first version of it was wrong: it quoted a EUR 3.9M naive cost from the 9x
    # egress *rate*, when total infrastructure differs by 2.4x — compute and
    # storage are unaffected by the egress decision. The 3.6x that replaced it
    # was itself left behind by the slower ramp, which is why the ratio and both
    # euro figures are pinned below rather than described in a comment.
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
    # The corridor table. Every cell is the model run at that take rate, so a
    # paragraph arguing about price cannot quietly disagree with the arithmetic
    # underneath it -- which is exactly what happened when this was one
    # sentence: it said EUR 0.92M a point and EUR 5.3M for five of them.
    ("01-revenue-model.md", "Y7 revenue at a 20% fan take",
     r"\| 20% \| €([\d.]+)M", TAKE_20["revenue"] / 1e6, 0.05),
    ("01-revenue-model.md", "Y7 EBITDA at a 20% fan take",
     r"\| 20% \| €[\d.]+M \| €([\d.]+)M", TAKE_20["ebitda"] / 1e6, 0.05),
    ("01-revenue-model.md", "Y7 revenue at the proposed 15%",
     r"\| \*\*15%\*\* \| \*\*€([\d.]+)M\*\*", Y7["revenue"] / 1e6, 0.05),
    ("01-revenue-model.md", "Y7 EBITDA at the proposed 15%",
     r"\| \*\*15%\*\* \| \*\*€[\d.]+M\*\* \| \*\*€([\d.]+)M\*\*", Y7["ebitda"] / 1e6, 0.05),
    ("01-revenue-model.md", "Y7 revenue at a 10% fan take",
     r"\| 10% \| €([\d.]+)M", TAKE_10["revenue"] / 1e6, 0.05),
    ("01-revenue-model.md", "Y7 EBITDA at a 10% fan take",
     r"\| 10% \| €[\d.]+M \| €([\d.]+)M", TAKE_10["ebitda"] / 1e6, 0.05),
    ("01-revenue-model.md", "revenue given up by matching Patreon",
     r"costs €([\d.]+)M of Y7\s+revenue", (Y7["revenue"] - TAKE_10["revenue"]) / 1e6, 0.05),
    ("01-revenue-model.md", "EBITDA given up by matching Patreon",
     r"revenue and €([\d.]+)M of EBITDA", (Y7["ebitda"] - TAKE_10["ebitda"]) / 1e6, 0.05),
    ("01-revenue-model.md", "the share of EBITDA a price war costs",
     r"EBITDA falls (\d+)%", 100 * (Y7["ebitda"] - TAKE_10["ebitda"]) / Y7["ebitda"], 0.6),

    # --- the two headline tables, cell by cell -----------------------------
    # Generated from ROWS so adding a year cannot leave a stale column behind,
    # and so no row of either table is left unwatched while its neighbour moves.
    *[("stride-business-plan-draft.md", f"seven-year table, Y{y['year']} EBITDA",
       r"\| EBITDA \|" + r" €-?[\d.]+M \|" * (y["year"] - 1) + r" €(-?[\d.]+)M",
       y["ebitda"] / 1e6, 0.02) for y in ROWS[:7]],
    # Paying-fan counts are deliberately not pinned here: they are targets the
    # model solves toward rather than anything a pricing assumption can move,
    # and the row label appears in two tables with different column counts, so
    # a regex for one matches the other. EBITDA is the row that drifted.

    ("stride-business-plan-draft.md", "summary table, Y3 net revenue",
     r"\| Net revenue \| €([\d.]+)M \| €[\d.]+M \|", ROWS[2]["revenue"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "summary table, Y7 net revenue",
     r"\| Net revenue \| €[\d.]+M \| €([\d.]+)M \|", ROWS[6]["revenue"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "summary table, Y3 EBITDA",
     r"\| EBITDA \| €(-?\d+)k \| €[\d.]+M \|", ROWS[2]["ebitda"] / 1e3, 2.0),
    ("stride-business-plan-draft.md", "summary table, Y7 EBITDA",
     r"\| EBITDA \| €-?\d+k \| €([\d.]+)M \|", ROWS[6]["ebitda"] / 1e6, 0.02),
    ("stride-business-plan-draft.md", "summary table, Y3 gross margin",
     r"\| Gross margin \| (\d+)% \|", 100 * ROWS[2]["gross"] / ROWS[2]["revenue"], 0.6),
    ("stride-business-plan-draft.md", "summary table, Y7 gross margin",
     r"\| Gross margin \| \d+% \| (\d+)% \|", 100 * ROWS[6]["gross"] / ROWS[6]["revenue"], 0.6),

    # --- derived prose that drifted when the growth curve changed -----------
    # Each of these was written out of the model once and then left behind by a
    # model change. Review caught them, not this file, which is the argument for
    # pinning them: a figure nothing watches is a figure that goes stale.
    ("01-revenue-model.md", "revenue mix, Y7 fan take",
     r"\| Fan take \| .*\| €([\d.]+)M \(\d+%\) \|", ROWS[6]["rev_fan"] / 1e6, 0.05),
    ("01-revenue-model.md", "revenue mix, Y7 sponsorship take",
     r"\| Sponsorship take \| .*\| €([\d.]+)M \(\d+%\) \|", ROWS[6]["rev_sponsorship"] / 1e6, 0.05),
    ("01-revenue-model.md", "revenue mix, Y7 SaaS",
     r"\| Sponsor SaaS \| .*\| €([\d.]+)M \(\d+%\) \|", ROWS[6]["rev_saas"] / 1e6, 0.05),

    ("03-financial-model.md", "Y2 revenue growth",
     r"Growth: Y2 \+(\d+)%", 100 * (ROWS[1]["revenue"] / ROWS[0]["revenue"] - 1), 1.0),
    ("03-financial-model.md", "Y7 revenue growth",
     r"Y6 \+\d+%, Y7 \+(\d+)%", 100 * (ROWS[6]["revenue"] / ROWS[5]["revenue"] - 1), 1.0),

    ("04-capital-and-valuation.md", "the blended exit multiple quoted in prose",
     r"the blended exit multiple says €([\d.]+)M", 6.5 * ROWS[9]["revenue"] / 1e6, 0.5),

    ("11-admission-and-matching.md", "Y10 blended admission rate",
     r"admission rate climbs from 20% to (\d+)%", Y10["admit_rate"] * 100, 0.6),

    # --- section 8, VAT now that it is modelled -----------------------------
    # These moved from sizing an exposure to pinning an assumption. The plan
    # carries Spanish VAT on fan prices, so what a reader needs is the size of
    # what that costs -- which is also the upside if the deemed-supplier reading
    # turns out to be wrong.
    ("stride-business-plan-draft.md", "Y7 revenue if we were not the deemed supplier",
     r"Y7 revenue would be €([\d.]+)M", NO_VAT_Y7["revenue"] / 1e6, 0.05),
    ("stride-business-plan-draft.md", "Y7 EBITDA if we were not the deemed supplier",
     r"and Y7 EBITDA €([\d.]+)M", NO_VAT_Y7["ebitda"] / 1e6, 0.05),
    ("stride-business-plan-draft.md", "what carrying VAT costs Y7 EBITDA, as a share",
     r"carrying it costs (\d+)% of Y7 EBITDA",
     100 * (NO_VAT_Y7["ebitda"] - Y7["ebitda"]) / NO_VAT_Y7["ebitda"], 0.6),
]

WORDS = {"five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "twenty": 20}


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
        # U+2212 MINUS SIGN is what the documents actually print; float()
        # only parses ASCII hyphen. Normalising here keeps the sign in the
        # capture, so a flipped sign fails loudly instead of being dropped.
        cleaned = raw.replace(",", "").replace("−", "-").rstrip(".")
        found = float(WORDS.get(raw, cleaned))
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
