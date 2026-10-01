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
    """Share of our commission we keep after the payment rail, on the model's
    own basis.

    The take is charged on the VAT-EXCLUSIVE price, because `fan_gmv` is net of
    VAT and `rev_fan = fan_gmv * take_fan`. Taking 15% of the gross price here
    inflated the commission by 21% and reported 54% and 71% retention where the
    model says 44% and 64% -- and because the guard reproduced the error, it
    could not catch it. `model.unit_economics()` is the authority.
    """
    take = (price / (1 + A.vat_rate_fan)) * A.take_fan
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
#: model.scenario_table() keyed by name, so a pin reads the run
#: rather than a number copied out of it.
SCEN = {r["scenario"]: r for r in model.scenario_table()}


#: The blended cost of acquiring one athlete, at the Y1 and Y10 segment mix.
#: 16.2 quotes both ends to show the mix shift is what moves it.
def _weighted_cac(i: int) -> float:
    ns = model.A.niche_share[i]
    return ns * model.A.segments[0].cac_eur[i] + (1 - ns) * model.A.segments[1].cac_eur[i]


NICHE_CAC_Y1 = _weighted_cac(0)
NICHE_CAC_Y10 = _weighted_cac(9)


#: What the average sponsor puts through the platform, and the commission on it.
#: The entry-tier argument in 01 rests on the ratio between that and the plan
#: price, so both ends of it are read from the model.
def _gmv_per_sponsor(i: int) -> float:
    return ROWS[i]["sponsorship_gmv"] / model.A.sponsors[i]


#: Cumulative free cash flow, year by year. The raiseability argument in 04
#: quotes the first two, and they are the same series the funding table uses.
CUM_FCF = []
_c = 0.0
for _r in ROWS:
    _c += _r["fcf"]
    CUM_FCF.append(_c)


def peak_funding() -> float:
    cum = trough = 0.0
    for r in ROWS:
        cum += r["fcf"]
        trough = min(trough, cum)
    return -trough


def workbook_formulas() -> int:
    """How many formula cells the workbook actually has.

    Hard-coding this made the pin useless in one direction: it could tell that
    the prose disagreed with a number typed into the guard, but not that the
    workbook itself had changed. Counting the artefact closes that.
    """
    from openpyxl import load_workbook

    wb = load_workbook(ROOT / "business-plan" / "Stride_Financial_Model.xlsx")
    return sum(1 for ws in wb for row in ws.iter_rows() for c in row
               if isinstance(c.value, str) and c.value.startswith("="))


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


def rounds_total() -> float:
    """Every tranche in the plan, including the optional growth round.

    Was `rounds_before_series_a`, which answered "how much before the round the
    plan depends on". With the Series A gone there is no such round: the plan
    depends on the two pre-seed tranches and nothing after them, so the only
    interesting total is all of it.
    """
    return sum(rd["amount"] for rd in model.ROUNDS)


DILUTION = {d["stage"]: d for d in model.dilution()}


def _trough_year() -> int:
    """The year cumulative free cash flow is at its lowest."""
    cum = low = 0.0
    year = 1
    for r in ROWS:
        cum += r["fcf"]
        if cum < low:
            low, year = cum, r["year"]
    return year


TROUGH_YEAR = _trough_year()

#: Scout Pro's annual list price, for the entry-tier argument in 01.
SCOUT_PRO_YEAR = model.SCOUT_PRO * 12

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
     r"At €9\.99 we keep (\d+)%", retained(9.99) * 100, 0.5),

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
     r"\| \*\*Base\*\* \| As modelled \| €[\d.]+M \| €([\d,]+)k", Y7["ebitda"] / 1e3, 1.0),
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
     r"By Y7 it is €([\d,]+)k of the", Y7["rev_saas"] / 1e3, 1.0),
    ("01-revenue-model.md", "Y7 total revenue",
     r"By Y7 it is €[\d,]+k of the €([\d.]+)M", Y7["revenue"] / 1e6, 0.02),
    ("01-revenue-model.md", "SaaS as share of Y7 gross profit",
     r"which\s+is roughly ([\d.]+)% of gross profit", Y7["rev_saas"] / Y7["gross"] * 100, 0.6),
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
     r"worth \*\*€(\d+)k across Y7–Y10\*\*", startup_tax_saving() / 1e3, 1.0),
    ("12-operations-plan.md", "Y7 payment processing",
     r"\| Payment processing \| €([\d,]+)k \|", Y7["psp"] / 1e3, 1.0),
    ("12-operations-plan.md", "Y7 infrastructure",
     r"\| Infrastructure \| €(\d+)k \|", Y7["infra"] / 1e3, 0.5),
    ("12-operations-plan.md", "infrastructure as a share of Y7 revenue",
     r"Infrastructure is ([\d.]+)% of revenue",
     100 * Y7["infra"] / Y7["revenue"], 0.05),
    ("12-operations-plan.md", "what a €4.99 tier retains",
     r"\| €4\.99 \| €4\.12 \| €0\.62 \| €0\.25 \+ 1\.9% \| \*\*(\d+)%\*\*",
     retained(4.99) * 100, 0.5),
    ("12-operations-plan.md", "what a €9.99 tier retains",
     r"\| €9\.99 \| €8\.26 \| €1\.24 \| €0\.25 \+ 1\.9% \| \*\*(\d+)%\*\*",
     retained(9.99) * 100, 0.5),

    # --- 13 Organization and HR (ESADE section 8) -------------------------
    *[("13-organization-and-hr.md", f"HR table, Y{y} headcount",
       r"\| Headcount \(FTE\) \|" + r" [\d.]+ \|" * (y - 1) + r" ([\d.]+)",
       ROWS[y - 1]["headcount"], 0.05) for y in range(1, 8)],
    # All seven years read in thousands now. The leaner hiring ramp keeps Y6
    # and Y7 people cost under a million, where they used to cross it and
    # needed a second pattern.
    *[("13-organization-and-hr.md", f"HR table, Y{y} people cost",
       r"\| People cost \|" + r" €[\d.]+[kM] \|" * (y - 1) + r" €(\d+)k",
       ROWS[y - 1]["people"] / 1e3, 0.5) for y in range(1, 8)],

    ("13-organization-and-hr.md", "Y10 headcount",
     r"Growth to (\d+) FTE by Y10", ROWS[9]["headcount"], 0.5),
    ("13-organization-and-hr.md", "Y7 revenue against the Y7 team",
     r"reaches \*\*€([\d.]+)M of revenue at Y7", Y7["revenue"] / 1e6, 0.05),
    ("13-organization-and-hr.md", "Y7 headcount in prose",
     r"of revenue at Y7 with (\d+) people", ROWS[6]["headcount"], 0.5),
    ("13-organization-and-hr.md", "founders held after both pre-seed tranches",
     r"(\d+)% held after the \d+% athlete partner grant",
     DILUTION["Pre-seed extension"]["held"] * 100, 0.5),
    ("13-organization-and-hr.md", "founders held after the growth round",
     r"\| \*\*Growth\*\* \(€1\.5M, optional\) \|[^|]*\| (\d+)%",
     DILUTION["Growth (optional)"]["held"] * 100, 0.5),
    # Anchored to its own row. `\*\*~(\d+)%\*\*` matched any bold ~NN% in the
    # file, so an unrelated figure added above it would have been checked
    # against the ESOP number without anyone noticing.
    ("13-organization-and-hr.md", "equity retained after the ESOP",
     r"\| Post-ESOP \|[^|]*\|\s*\*\*~(\d+)%\*\*",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("13-organization-and-hr.md", "revenue forfeited by the 15% take",
     r"forfeits \*\*€([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.05),

    ("14-legal-and-growth.md", "what the startup tax rate is worth",
     r"worth €(\d+)k across Y7–Y10", startup_tax_saving() / 1e3, 1.0),
    # The paragraph interpreting the scenario table. The table is generated and
    # moves with the model; the sentence under it was typed once and was three
    # figures out of date, including a capital need of EUR 754k against a table
    # saying EUR 827k.
    ("esade-body.md", "pessimistic revenue lost against base",
     r"the fan thesis costs\s+(\d+)% of",
     (1 - SCEN["Pessimistic"]["revenue_y7"] / SCEN["Base"]["revenue_y7"]) * 100, 0.5),
    ("esade-body.md", "pessimistic capital need as a multiple of base",
     r"multiplies the capital requirement by\s+([\d.]+),",
     SCEN["Pessimistic"]["capital_need"] / SCEN["Base"]["capital_need"], 0.05),
    ("esade-body.md", "pessimistic capital need",
     r"to €([\d,]+)k against a €400k raise",
     SCEN["Pessimistic"]["capital_need"] / 1e3, 0.5),
    ("esade-body.md", "optimistic revenue gain",
     r"optimistic case adds (\d+)% to",
     (SCEN["Optimistic"]["revenue_y7"] / SCEN["Base"]["revenue_y7"] - 1) * 100, 0.5),

    # -- 16.2 the segment progression --------------------------------------
    # The mix shift is the plan's largest strategic claim about its own future,
    # so every number stating it is read from niche_share and the two segments'
    # CAC rather than typed.
    ("16-growth-strategy.md", "niche share in Y1",
     r"\*\*(\d+)% niche in Y1", model.A.niche_share[0] * 100, 0.5),
    ("16-growth-strategy.md", "niche share by Y10",
     r"niche in Y1 to (\d+)% by Y10", model.A.niche_share[9] * 100, 0.5),
    ("16-growth-strategy.md", "weighted athlete CAC in Y1",
     r"\*\*€(\d+) to €\d+\*\*", NICHE_CAC_Y1, 0.5),
    ("16-growth-strategy.md", "weighted athlete CAC by Y10",
     r"\*\*€\d+ to €(\d+)\*\*", NICHE_CAC_Y10, 0.5),

    # Follows the growth strategy out of the legal document: the ESADE outline
    # separates legal aspects from company growth, so they are now two files.
    ("16-growth-strategy.md", "Y10 EBITDA",
     r"€([\d.]+)M EBITDA by Y10", ROWS[9]["ebitda"] / 1e6, 0.05),

    # --- 15 Primary research (ESADE section 5.1.4) -------------------------
    ("15-market-research.md", "Y7 admission rate, the value the sentence ends on",
     r"\*\*20\.0% in Y1 to ([\d.]+)% by", 100 * ROWS[6]["admit_rate"], 0.05),

    # The risk register restates two cost figures the recalibration moved and
    # nothing watched: R6 quoted PSP at Y7 and R10 infra as a share of revenue.

    # --- the ESADE submission body ----------------------------------------
    # The document that gets marked. It restates figures from fourteen other
    # files, so it is the likeliest place for a stale number to reach an
    # examiner, and it is pinned harder than any of them.
    # -- the sensitivity table in 7.6, every cell of it -------------------
    # Generated by model.scenario_table() as of this commit. Pinned on the way
    # in rather than after it drifts: the previous version of this table was
    # typed by hand, prefixed every figure with "~", and sat unchecked inside
    # the section the evaluation form weights at 15%.
    ("esade-body.md", "pessimistic Y7 revenue",
     r"\*\*Pessimistic\*\*[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Pessimistic"]["revenue_y7"] / 1e6, 0.005),
    ("esade-body.md", "pessimistic Y7 EBITDA",
     r"\*\*Pessimistic\*\*[^|]*\|[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Pessimistic"]["ebitda_y7"] / 1e6, 0.005),
    ("esade-body.md", "pessimistic cash trough",
     r"\*\*Pessimistic\*\*(?:[^|]*\|){4}[^|]*€(\d+)k", SCEN["Pessimistic"]["trough"] / 1e3, 0.5),
    ("esade-body.md", "optimistic Y7 revenue",
     r"\*\*Optimistic\*\*[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Optimistic"]["revenue_y7"] / 1e6, 0.005),
    ("esade-body.md", "optimistic Y7 EBITDA",
     r"\*\*Optimistic\*\*[^|]*\|[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Optimistic"]["ebitda_y7"] / 1e6, 0.005),
    ("esade-body.md", "optimistic capital need",
     r"\*\*Optimistic\*\*(?:[^|]*\|){5}[^|]*€(\d+)k", SCEN["Optimistic"]["capital_need"] / 1e3, 0.5),
    ("esade-body.md", "pessimistic capital need",
     r"\*\*Pessimistic\*\*(?:[^|]*\|){5}[^|]*€([\d.]+)M", SCEN["Pessimistic"]["capital_need"] / 1e6, 0.005),
    ("esade-body.md", "base Y7 revenue in the sensitivity table",
     r"\*\*Base\*\*[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Base"]["revenue_y7"] / 1e6, 0.005),
    ("esade-body.md", "base Y7 EBITDA in the sensitivity table",
     r"\*\*Base\*\*[^|]*\|[^|]*\|[^|]*\| €([\d.]+)M", SCEN["Base"]["ebitda_y7"] / 1e6, 0.005),
    ("esade-body.md", "base cash trough in the sensitivity table",
     r"\*\*Base\*\*(?:[^|]*\|){4}[^|]*€(\d+)k", SCEN["Base"]["trough"] / 1e3, 0.5),
    ("esade-body.md", "base capital need in the sensitivity table",
     r"\*\*Base\*\*(?:[^|]*\|){5}[^|]*€(\d+)k", SCEN["Base"]["capital_need"] / 1e3, 0.5),
    ("esade-body.md", "optimistic cash trough",
     r"\*\*Optimistic\*\*(?:[^|]*\|){4}[^|]*€(\d+)k", SCEN["Optimistic"]["trough"] / 1e3, 0.5),
    # -- 01 the entry-tier argument ---------------------------------------
    ("01-revenue-model.md", "Y1 deal volume per sponsor",
     r"average sponsor runs\s+about €([\d,]+) of deals", _gmv_per_sponsor(0), 0.5),
    ("01-revenue-model.md", "Y1 commission per sponsor",
     r"commission on them is\s+roughly €(\d+)", _gmv_per_sponsor(0) * model.A.take_sponsorship, 0.5),
    ("01-revenue-model.md", "Y7 deal volume per sponsor",
     r"average sponsor runs €([\d,]+) of deals", _gmv_per_sponsor(6), 0.5),
    ("01-revenue-model.md", "Y7 commission per sponsor",
     r"commission alone is €([\d,]+)", _gmv_per_sponsor(6) * model.A.take_sponsorship, 0.5),

    # -- 04 the round multiples -------------------------------------------
    # Both ends read from the model: the price from ROUNDS by stage, the gate
    # from ROUND_GATE_MRR. The gate used to be hardcoded here while living only
    # in the document's prose, so moving a milestone would have left the
    # multiple beside it stale and passing.
    *[("04-capital-and-valuation.md", f"{stage} gate MRR",
       rf"\| €(\d+)k MRR", mrr / 1e3, 0.5)
      for stage, mrr in list(model.ROUND_GATE_MRR.items())[:1]],
    ("04-capital-and-valuation.md", "growth-round multiple on the gate",
     r"\*\*([\d.]+)x ARR\*\* \| Marketplaces",
     next(r["pre"] for r in model.ROUNDS if r["stage"] == "Growth (optional)")
     / (model.ROUND_GATE_MRR["Growth (optional)"] * 12), 0.05),
    ("04-capital-and-valuation.md", "growth-round multiple on Y6 revenue",
     r"lower still, at \*\*([\d.]+)x\*\*",
     next(r["pre"] for r in model.ROUNDS if r["stage"] == "Growth (optional)")
     / ROWS[5]["revenue"], 0.05),

    # -- 04 the raiseability section --------------------------------------
    # Figures a reader will check against the cash flow, so they are read from
    # it rather than restated.
    ("04-capital-and-valuation.md", "Y1 cash need in the raiseability section",
     r"Y1 cash need of\s+€(\d+)k", -CUM_FCF[0] / 1e3, 0.5),
    ("04-capital-and-valuation.md", "cumulative need to end of Y2",
     r"cumulative need of\s+\*?\*?€(\d+)k\*?\*? to the end of Y2",
     -CUM_FCF[1] / 1e3, 0.5),
    ("04-capital-and-valuation.md", "equity tranche plus the ENISA loan",
r"Together they are €(\d+)k",
     # By stage, not by position. grant_years() documents a silent
     # divergence caused by indexing ROUNDS[0] when a round was inserted.
     (next(r["amount"] for r in model.ROUNDS if r["stage"] == "Pre-seed")
      + 75_000) / 1e3, 0.5),

    ("esade-body.md", "capital the plan needs",
     r"The plan needs €(\d+)k", peak_funding() * 1.4 / 1e3, 0.5),
    ("esade-body.md", "the cash trough",
     r"a €(\d+)k cash\s+trough in Y\d", peak_funding() / 1e3, 0.5),
    ("esade-body.md", "the pre-seed ask",
     r"\*\*The ask is €(\d+)k at €[\d.]+M pre-money",
     model.ROUNDS[0]["amount"] / 1e3, 0.5),
    ("esade-body.md", "the pre-seed price",
     r"\*\*The ask is €\d+k at €([\d.]+)M pre-money",
     model.ROUNDS[0]["pre"] / 1e6, 0.05),
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
     r"The DCF says \*\*€([\d,]+)k\*\* today", VAL["enterprise_value"] / 1e3, 1.0),
    ("esade-body.md", "revenue forfeited by the 15% take",
     r"forfeits €([\d.]+)M of Y7\s+revenue", take_rate_delta() / 1e6, 0.05),
    ("esade-body.md", "what the startup tax rate is worth",
     r"worth €(\d+)k across Y7–Y10", startup_tax_saving() / 1e3, 1.0),
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
     r"athletes, (\d+) sponsors paying SaaS",
     ROWS[2]["paying_sponsors"], 0.6),
    ("esade-body.md", "workbook formula count",
     r"evaluates all ([\d,]+) workbook\s+formulas", workbook_formulas, 0.5),

    # The pro forma cash flow the outline requires at 9.3. Read from the
    # workbook, so the body cannot disagree with the statement it came from.
    ("esade-body.md", "Y7 free cash flow",
     r"\| \*\*Free Cash Flow\*\* \|(?: \*\*−?€[\d.,]+[kM]\*\* \|){3} \*\*€([\d,]+)k\*\*",
     ROWS[6]["fcf"] / 1e3, 1.0),
    ("esade-body.md", "Y7 operating cash flow",
     r"\| \*\*Operating Cash Flow\*\* \|(?: \*\*−?€[\d.,]+[kM]\*\* \|){3} \*\*€([\d,]+)k\*\*",
     ROWS[6]["operating_cf"] / 1e3, 1.0),
    ("esade-body.md", "Y7 capital expenditure",
     r"\| Capital expenditure \|(?: −€[\d.,]+k \|){3} −€(\d+)k",
     ROWS[6]["capex"] / 1e3, 0.5),

    # The admission-review unit cost. Three model-derived figures in one line
    # of prose, none of them watched until now.
    ("12-operations-plan.md", "what a €24.99 tier retains",
     r"\| €24\.99 \| €20\.65 \| €3\.10 \| €0\.25 \+ 1\.9% \| \*\*(\d+)%\*\*",
     retained(24.99) * 100, 0.5),

    ("12-operations-plan.md", "cost of one review in Y1",
     r"\*\*€([\d.]+) in Y1, €[\d.]+ by Y7\*\*",
     ROWS[0]["review_hourly"] * A.review_minutes / 60, 0.005),
    ("12-operations-plan.md", "cost of one review by Y7",
     r"\*\*€[\d.]+ in Y1, €([\d.]+) by Y7\*\*",
     ROWS[6]["review_hourly"] * A.review_minutes / 60, 0.005),
    ("12-operations-plan.md", "loaded review rate in Y1",
     r"rising from €([\d.]+) to €[\d.]+\)", ROWS[0]["review_hourly"], 0.005),
    ("12-operations-plan.md", "loaded review rate by Y7",
     r"rising from €[\d.]+ to €([\d.]+)\)", ROWS[6]["review_hourly"], 0.005),

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
     r"\*\*€(\d+)k pre-seed at €[\d.]+M pre-money\.\*\*",
     model.ROUNDS[0]["amount"] / 1e3, 1.0),
    ("00-executive-summary.md", "the pre-seed price",
     r"\*\*€\d+k pre-seed at €([\d.]+)M pre-money\.\*\*",
     model.ROUNDS[0]["pre"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "the first tranche in the raiseability section",
     r"asks \*\*€(\d+)k at €[\d.]+M pre-money\*\*",
     model.ROUNDS[0]["amount"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the first tranche price",
     r"asks \*\*€\d+k at €([\d.]+)M pre-money\*\*",
     model.ROUNDS[0]["pre"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "the pre-seed ask",
     r"\| \*\*Pre-seed\*\* \| \*\*€(\d+)k\*\*", model.ROUNDS[0]["amount"] / 1e3, 1.0),

    ("00-executive-summary.md", "total raised across every tranche",
     r"the plan raises €([\d.]+)M in total", rounds_total() / 1e6, 0.05),
    ("07-open-questions.md", "total raised across every tranche",
     r"or the €([\d.]+)M the rounds imply", rounds_total() / 1e6, 0.05),
    ("07-open-questions.md", "capital the plan needs",
     r"Raise €(\d+)k, or the", peak_funding() * 1.4 / 1e3, 1.0),

    # The trough is the number the raise has to clear, so it is quoted in four
    # places and was right in one of them.
    ("00-executive-summary.md", "the cash trough",
     r"\*\*€(\d+)k cash trough in Y\d\*\*", peak_funding() / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the cash trough",
     r"\*\*€(\d+)k trough in Y\d\*\*", peak_funding() / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the trough the grant stack covers",
     r"covers the whole €(\d+)k", peak_funding() / 1e3, 1.0),
    # The YEAR the trough falls in, not just its size. Every pin above matched
    # the year as `Y\\d` and checked only the amount, so moving the trough from
    # Y3 to Y4 left three documents naming the wrong year while the guard passed.
    *[(doc, "the year the cash trough falls in",
       r"cash\s+trough in Y(\d)", TROUGH_YEAR, 0.1)
      for doc in ("esade-body.md", "00-executive-summary.md")],
    ("04-capital-and-valuation.md", "the year the cash trough falls in",
     r"trough in Y(\d)", TROUGH_YEAR, 0.1),

    # ── the figures cubic found stale on PR 71 ─────────────────────────────
    # Every one of these was wrong and unwatched. They are mostly derived
    # percentages and interpretive sentences, which is the class the guard was
    # thinnest on: it pinned the table and not the paragraph reading it.
    ("03-financial-model.md", "the year the pessimistic case turns profitable",
     r"\*\*reaches profitability in Y(\d) rather than", SCEN["Pessimistic"]["first_profit_year"], 0.1),
    ("03-financial-model.md", "the year the base case turns profitable",
     r"rather than Y(\d)\*\*, two years later", SCEN["Base"]["first_profit_year"], 0.1),
    ("03-financial-model.md", "pessimistic capital need in the prose",
     r"needs €([\d,]+)k rather than", SCEN["Pessimistic"]["capital_need"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "pessimistic need beside the optional round",
     r"scenario in §7\.6 needs\s+€([\d,]+)k against the €400k raised",
     SCEN["Pessimistic"]["capital_need"] / 1e3, 1.0),
    # growth rates: only Y2 was pinned, so Y3 to Y6 sat a whole trajectory stale
    *[("03-financial-model.md", f"revenue growth Y{y}",
       rf"Y{y} \+(\d+)%", (ROWS[y - 1]["revenue"] / ROWS[y - 2]["revenue"] - 1) * 100, 0.6)
      for y in (3, 4, 5, 6)],
    # the niche share row, relabelled to say which denominator it uses
    ("03-financial-model.md", "niche share of total revenue, Y1",
     r"\| \*\*Niche share of total revenue\*\* \| \*\*(\d+)%\*\*",
     ROWS[0]["segs"]["niche"]["revenue"] / ROWS[0]["revenue"] * 100, 0.6),
    ("03-financial-model.md", "niche share of total revenue in the prose, Y1",
     r"Niche sports carry\s+(\d+)% of total revenue in Y1",
     ROWS[0]["segs"]["niche"]["revenue"] / ROWS[0]["revenue"] * 100, 0.6),
    ("03-financial-model.md", "niche share of total revenue in the prose, Y7",
     r"fall to (\d+)% by\s*\n?Y7", ROWS[6]["segs"]["niche"]["revenue"] / ROWS[6]["revenue"] * 100, 0.6),
    # the review workload, quoted in three documents and wrong in all three
    *[(doc, "peak reviewer FTE in the prose", r"(0\.\d\d) of one",
       max(r["review_fte"] for r in ROWS), 0.005)
      for doc in ("02-cost-model.md", "11-admission-and-matching.md")],
    ("12-operations-plan.md", "peak reviewer FTE against total headcount",
     r"roughly \*\*(0\.\d\d) of one full-time person\*\*",
     max(r["review_fte"] for r in ROWS), 0.005),
    # verification, whose euros and share of enterprise value both moved
    ("02-cost-model.md", "verification peak",
     r"Verification peaks at\s*\n?€([\d.]+)k a year",
     max(r["verification"] for r in ROWS) / 1e3, 0.05),
    ("11-admission-and-matching.md", "verification peak",
     r"verification peaks at €([\d.]+)k a year",
     max(r["verification"] for r in ROWS) / 1e3, 0.05),
    # Y7 cost of sales as shares of revenue, the table and the sentence under it
    ("12-operations-plan.md", "payment processing as a share of Y7 revenue",
     r"\| Payment processing \| €[\d,]+k \| ([\d.]+)% \|",
     ROWS[6]["psp"] / ROWS[6]["revenue"] * 100, 0.06),
    ("12-operations-plan.md", "infrastructure as a share of Y7 revenue",
     r"Infrastructure is ([\d.]+)% of revenue", ROWS[6]["infra"] / ROWS[6]["revenue"] * 100, 0.06),
    ("12-operations-plan.md", "payments against infrastructure",
     r"nearly (\d+) times larger", ROWS[6]["psp"] / ROWS[6]["infra"], 0.6),
    # egress, which the plan quotes as petabytes
    ("02-cost-model.md", "Y7 egress in petabytes",
     r"Y7 moves ~([\d.]+) PB",
     ROWS[6]["avg_fans"] * A.gb_per_fan_month * 12 / 1e6, 0.06),
    # the entry-tier argument, whose multiple moved with the commission
    ("01-revenue-model.md", "Scout Pro against the Y1 commission",
     r"a year is\s*\n?(\d+) times that",
     SCOUT_PRO_YEAR / (ROWS[0]["sponsorship_gmv"] / A.sponsors[0] * A.take_sponsorship), 0.6),
    # the spare over the trough, quoted in three places
    *[(doc, "spare over the trough", r"with\s*\n?€(\d+)k to spare",
       (sum(rd["amount"] for rd in model.ROUNDS if "Pre-seed" in rd["stage"]) - peak_funding()) / 1e3, 0.6)
      for doc in ("00-executive-summary.md", "04-capital-and-valuation.md")],
    ("esade-body.md", "spare over the trough",
     r"covers that with €(\d+)k to spare",
     (sum(rd["amount"] for rd in model.ROUNDS if "Pre-seed" in rd["stage"]) - peak_funding()) / 1e3, 0.6),
    ("esade-body.md", "Y1 cash need in 7.5",
     r"the first covers Y1's €(\d+)k", -ROWS[0]["fcf"] / 1e3, 0.6),

    # ── the unpinned figures the fan-to-Y2 change moved ────────────────────
    # The same lesson twice: a pin matches one sentence and the same number is
    # written again elsewhere in another. "The plan needs EUR Xk" was pinned;
    # "required is EUR Xk" two hundred lines later was not.
    ("esade-body.md", "capital required, second statement",
     r"required is \*\*€([\d,]+)k\*\*", peak_funding() * 1.4 / 1e3, 1.0),
    ("esade-body.md", "the trough, second statement",
     r"cash ever goes is \*\*€([\d,]+)k", peak_funding() / 1e3, 1.0),
    ("esade-body.md", "the trough the grant stack covers",
     r"covers the whole €([\d,]+)k trough", peak_funding() / 1e3, 1.0),
    ("esade-body.md", "the DCF floor in 7.7",
     r"\*\*€([\d,]+)k floor\*\*", VAL["enterprise_value"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the DCF floor in the headline",
     r"with a\s+€([\d,]+)k floor under a no-growth", VAL["enterprise_value"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "capital required beside the equity raised",
     r"against a €([\d,]+)k requirement", peak_funding() * 1.4 / 1e3, 1.0),
    ("04-capital-and-valuation.md", "capital required, restated",
     r"on top of it\*\*, which is €([\d,]+)k", peak_funding() * 1.4 / 1e3, 1.0),
    ("13-organization-and-hr.md", "the trough in the hiring note",
     r"takes the trough to €([\d,]+)k", peak_funding() / 1e3, 1.0),
    # the scenario table in appendix C, cell by cell
    *[("03-financial-model.md", f"{name} capital need in the scenario table",
       rf"\| {lab} \|[^|]*\|[^|]*\|[^|]*\| €([\d,]+)k \|",
       SCEN[name]["capital_need"] / 1e3, 1.0)
      for name, lab in (("Pessimistic", "Pessimistic"), ("Base", r"\*\*Base\*\*"),
                        ("Optimistic", "Optimistic"))],
    ("03-financial-model.md", "base need in the paragraph under the table",
     r"rather than €([\d,]+)k\. That is the", peak_funding() * 1.4 / 1e3, 1.0),

    # ── Appendix N, the business model canvas ──────────────────────────────
    ("20-business-model-canvas.md", "Y7 fan share of revenue",
     r"15% of what the fan pays \| (\d+)%",
     ROWS[6]["rev_fan"] / ROWS[6]["revenue"] * 100, 0.6),
    ("20-business-model-canvas.md", "Y7 sponsorship share of revenue",
     r"5% on Scout Agency \| (\d+)%",
     ROWS[6]["rev_sponsorship"] / ROWS[6]["revenue"] * 100, 0.6),
    ("20-business-model-canvas.md", "Y7 SaaS share of revenue",
     r"€999 a month \| (\d+)%",
     ROWS[6]["rev_saas"] / ROWS[6]["revenue"] * 100, 0.6),
    ("20-business-model-canvas.md", "peak reviewer FTE",
     r"\*\*(0\.\d\d)\s+of one full-time reviewer\*\*",
     max(r["review_fte"] for r in ROWS), 0.005),
    ("20-business-model-canvas.md", "Y10 headcount",
     r"\*\*(\d+) people by Y10\*\*", ROWS[9]["headcount"], 0.5),
    ("20-business-model-canvas.md", "Y7 payment processing",
     r"\*\*Payment processing\*\* \| €([\d,]+)k", ROWS[6]["psp"] / 1e3, 1.0),
    ("20-business-model-canvas.md", "Y7 people cost",
     r"\| People \| €([\d,]+)k", ROWS[6]["people"] / 1e3, 1.0),
    ("20-business-model-canvas.md", "Y7 marketing",
     r"\| Marketing and acquisition \| €([\d,]+)k", ROWS[6]["marketing"] / 1e3, 1.0),
    ("20-business-model-canvas.md", "Y7 legal",
     r"\| Legal and compliance \| €([\d,]+)k", ROWS[6]["legal"] / 1e3, 1.0),
    ("20-business-model-canvas.md", "Y7 infrastructure",
     r"\| Infrastructure \| €([\d,]+)k", ROWS[6]["infra"] / 1e3, 1.0),
    ("20-business-model-canvas.md", "Y7 payment processing as a share of revenue",
     r"\*\*Payment processing\*\* \| €[\d,]+k \| (\d+)%",
     ROWS[6]["psp"] / ROWS[6]["revenue"] * 100, 0.6),
    ("20-business-model-canvas.md", "gross margin ceiling",
     r"gross margin stops at (\d+)%",
     ROWS[9]["gross"] / ROWS[9]["revenue"] * 100, 0.6),

    # The trough year is stated TWICE in esade-body and the pin above uses
    # re.search, which finds the first. The second sat unwatched and said Y4
    # after the trough moved to Y3.
    ("esade-body.md", "the trough year, second statement",
     r"cash trough in Y(\d) plus a 40% buffer", TROUGH_YEAR, 0.1),
    ("esade-body.md", "Y1 cash requirement in 3.4",
     r"to the end of Y1 is €([\d,]+)k", -ROWS[0]["fcf"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "Y1 cash need in the ENISA paragraph",
     r"Y1 cash need of €([\d,]+)k", -ROWS[0]["fcf"] / 1e3, 1.0),

    # ── the year-one block in the executive summary ────────────────────────
    ("esade-body.md", "Y1 athletes in the year-one block",
     r"recruit\s+\*\*([\d,]+) athletes\*\* in two or three niche", ROWS[0]["athletes"], 0.5),
    ("esade-body.md", "Y1 applications in the year-one block",
     r"niche Spanish sports from\s+([\d,]+) applications", ROWS[0]["applications"], 1.0),
    ("esade-body.md", "Y1 deals in the year-one block",
     r"closing\s*\n?about \*\*(\d+) deals", ROWS[0]["deals"], 0.6),
    ("esade-body.md", "Y1 commission in the year-one block",
     r"deals for €([\d,]+) of commission", ROWS[0]["rev_sponsorship"], 1.0),
    ("esade-body.md", "Y1 cash requirement in the year-one block",
     r"cash requirement is \*\*€([\d,]+)k\*\*", -ROWS[0]["fcf"] / 1e3, 1.0),
    ("esade-body.md", "Y1 need in the ENISA paragraph",
     r"against a Y1 need of\s*\n?€([\d,]+)k", -ROWS[0]["fcf"] / 1e3, 1.0),

    ("README.md", "peak burn",
     r"peak burn €(\d+)k", peak_funding() / 1e3, 1.0),

    # The dilution path, cell by cell. It was typed by hand and its later rows
    # did not follow from its earlier ones under any reading of them.
    ("04-capital-and-valuation.md", "pre-seed post-money",
     r"\| Pre-seed \| €\d+k \| €[\d.]+M \| €([\d.]+)M \|",
     DILUTION["Pre-seed"]["post"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "pre-seed pre-money in the cascade",
     r"\| Pre-seed \| €\d+k \| €([\d.]+)M \|",
     DILUTION["Pre-seed"]["pre"] / 1e6, 0.05),
    ("04-capital-and-valuation.md", "pre-seed investor stake",
     r"\| Pre-seed \|(?:[^|]*\|){3} ([\d.]+)% \|",
     DILUTION["Pre-seed"]["stake"] * 100, 0.1),
    # The advisory grant lands after the second tranche, so this row reports
    # what is held after BOTH, not after the first.
    ("04-capital-and-valuation.md", "founders held after the first tranche",
     r"\| Pre-seed \|(?:[^|]*\|){4} (\d+)% \|",
     DILUTION["Pre-seed"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after both tranches",
     r"\| Pre-seed extension \|(?:[^|]*\|){4} (\d+)% \(after \d+% athlete partner\)",
     DILUTION["Pre-seed extension"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after the growth round",
     r"\| Growth \*\(optional\)\* \|(?:[^|]*\|){4} (\d+)% \|",
     DILUTION["Growth (optional)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "founders held after the ESOP",
     # The three empty columns were em-dashes until the document dropped them;
     # matched as "whatever is between the pipes" so the pin survives a
     # formatting decision it has no stake in.
     r"\| ESOP \(cumulative\) \|[^|]*\|[^|]*\|[^|]*\| 10% \| \*\*~(\d+)%\*\* \|",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "equity retained through the growth round",
     r"Retaining ~(\d+)% through the growth round",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "equity retained without the growth round",
     r"the figure is\s+~(\d+)%",
     DILUTION["Pre-seed extension"]["held"] * (1 - model.ESOP_POOL) * 100, 0.5),

    # The founder-hurdle paragraph. Its old version multiplied a retention the
    # dilution table did not support by an enterprise value nothing produced.
    ("04-capital-and-valuation.md", "equity retained through the growth round, in prose",
     r"team retaining \*\*(\d+)%\*\* through the growth round",
     DILUTION["ESOP (cumulative)"]["held"] * 100, 0.5),
    ("04-capital-and-valuation.md", "the founder's share of the DCF",
     r"\*\*€(\d+)k against the DCF of",
     DILUTION["ESOP (cumulative)"]["held"] * VAL["enterprise_value"] / 1e3, 1.0),
    ("04-capital-and-valuation.md", "the DCF the share is taken from",
     r"against the DCF of €([\d.]+)M\*\*", VAL["enterprise_value"] / 1e6, 0.005),
    # The two ends of the founder's stake against the exit multiples. Derived
    # from the dilution cascade and a generated table, and quoted in prose --
    # which is the combination that goes stale.
    ("04-capital-and-valuation.md", "founder stake at the lowest exit multiple",
     r"\*\*€([\d.]+)M to €[\d.]+M\*\*",
     DILUTION["ESOP (cumulative)"]["held"] * min(MULTIPLES) / 1e6, 0.08),
    ("04-capital-and-valuation.md", "founder stake at the highest exit multiple",
     r"\*\*€[\d.]+M to €([\d.]+)M\*\*",
     DILUTION["ESOP (cumulative)"]["held"] * max(MULTIPLES) / 1e6, 0.08),

    # Unpinned figures that the egress correction moved and review caught:
    # the gap between the ask and the pre-seed, and G11's restatement of the
    # Y7 infrastructure number from the table three sections above it.

    ("04-capital-and-valuation.md", "what the startup tax rate is worth",
     r"worth €(\d+)k across Y7–Y10", startup_tax_saving() / 1e3, 1.0),

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
     r", €([\d.]+)M across the ten\s+years", egress_cumulative() / 1e6, 0.05),
    ("README.md", "the Y7 egress difference",
     r"costs \*\*€(\d+)k more in Y7\*\*", egress_delta(7) / 1e3, 1.0),
    ("README.md", "the egress difference across the plan",
     r"more in Y7\*\*, and €([\d.]+)M", egress_cumulative() / 1e6, 0.05),

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

    # Y5, Y6 and Y7 each anchored by position rather than by quoting their
    # neighbours. The first version hardcoded "EUR 8.40M | EUR 16.20M |" as the
    # anchor for Y7, which made two unwatched figures load-bearing: drift in Y5
    # would have failed the *Y7* claim as "not found" and named the wrong column.

    # The document describes the guard that checks it, so the guard checks that
    # description too. Self-referential on purpose: this count is exactly the
    # kind of figure that goes stale the moment anyone adds a claim.
    # Pinned in every document that states it. It was pinned in one, so the
    # other two could drift to a different number and nothing would notice.
    *[(doc, "number of pinned claims",
       r"(\d+) prose\s+claims", lambda: len(CLAIMS), 0.1)
      for doc in ("esade-body.md", "STATUS.md")],
    ("esade-body.md", "number of documents checked",
     r"prose claims across (\d+) documents", lambda: len({c[0] for c in CLAIMS}), 0.1),

    ("07-open-questions.md", "EUR 4.99 retention",
     r"€4\.99 retains (\d+)% of our take", retained(4.99) * 100, 0.5),
    ("07-open-questions.md", "EUR 9.99 retention",
     r"€9\.99 retains (\d+)%", retained(9.99) * 100, 0.5),
    ("07-open-questions.md", "season pass retention",
     r"season pass retains (\d+)%", retained(89) * 100, 0.5),
    ("07-open-questions.md", "revenue forgone by 15% vs 20%",
     r"forfeits €([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.1),
    ("07-open-questions.md", "DCF headline",
     r"the DCF \(€([\d,]+)k\)", VAL["enterprise_value"] / 1e3, 1.0),

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
    # Paying-fan counts are deliberately not pinned here: they are targets the
    # model solves toward rather than anything a pricing assumption can move,
    # and the row label appears in two tables with different column counts, so
    # a regex for one matches the other. EBITDA is the row that drifted.

    # --- derived prose that drifted when the growth curve changed -----------
    # Each of these was written out of the model once and then left behind by a
    # model change. Review caught them, not this file, which is the argument for
    # pinning them: a figure nothing watches is a figure that goes stale.
    ("01-revenue-model.md", "revenue mix, Y7 fan take",
     r"\| Fan take \| .*\| €([\d.]+)M \(\d+%\) \|", ROWS[6]["rev_fan"] / 1e6, 0.05),
    ("01-revenue-model.md", "revenue mix, Y7 sponsorship take",
     r"\| Sponsorship take \| .*\| €(\d+)k \(\d+%\) \|", ROWS[6]["rev_sponsorship"] / 1e3, 1.0),
    ("01-revenue-model.md", "revenue mix, Y7 SaaS",
     r"\| Sponsor SaaS \| .*\| €(\d+)k \(\d+%\) \|", ROWS[6]["rev_saas"] / 1e3, 1.0),

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
