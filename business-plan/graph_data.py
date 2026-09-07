"""CSV series for the graph slots marked in the business plan.

The plan carries `> [!example] GRAPH Gn` callouts wherever a chart would say
something a table cannot. Each one names a file this script writes, so drawing
the chart is an import rather than a re-derivation -- and so a chart can never
quietly disagree with the model it came from, which is the failure mode of every
deck whose numbers were retyped into a spreadsheet once and then diverged.

    python business-plan/graph_data.py

Writes to business-plan/attachments/chart-data/ -- `data/` is gitignored for the
runtime database, so the charts get their own directory. Re-run it after any
change to model.py;
the numbers move, the files move with them.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import model                                    # noqa: E402
import sport_index                              # noqa: E402

OUT = HERE / "attachments" / "chart-data"


def write(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {path.relative_to(HERE.parent)}  ({len(rows)} rows)")


def eur_m(x: float) -> float:
    return round(x / 1e6, 3)


RAISE_EUR_M = {rd["year"]: round(rd["amount"] / 1e6, 3) for rd in model.ROUNDS}
RAISE_STAGE = {rd["year"]: rd["stage"] for rd in model.ROUNDS}


def main() -> None:
    rows = model.build()
    seven = rows[:7]
    ten = rows

    # G1 -- executive summary. Revenue as bars, EBITDA as a line crossing zero
    # in Y4. The whole plan in one frame.
    write("g1-revenue-ebitda.csv",
          ["year", "revenue_eur_m", "ebitda_eur_m", "ebitda_margin_pct"],
          [[r["year"], eur_m(r["revenue"]), eur_m(r["ebitda"]),
            round(100 * r["ebitda"] / r["revenue"], 1) if r["revenue"] else ""]
           for r in seven])

    # G3 -- the market funnel. A log axis, or the last bar is invisible.
    write("g3-market-funnel.csv",
          ["step", "people", "basis"],
          [["EU-27 + UK population", 520_000_000, "Eurostat"],
           ["Participate in organised sport", 104_000_000, "~20%, estimate"],
           ["Compete at club level or above", 8_300_000, "~8%, estimate"],
           ["In niche sports", 4_600_000, "~55%, sport index segmentation"],
           ["With >=5,000 following (TAM)", 138_000, "~3%, softest number in the plan"],
           ["SAM -- six launch markets", 55_000, "~40% of TAM"],
           # From the model, not typed: the old 52,000 was 95% of the SAM
           # one row above it, which is the contradiction section 3.3 now
           # discloses. The slower ramp lands at 40% of SAM by Y7.
           ["SOM -- what the plan claims by Y7", seven[6]["athletes"],
            "model athlete target"]])

    # G4 -- the sport index. All 714 pairs, so the chart can show the whole
    # cloud with Spain picked out rather than only the winners' table.
    pairs = sport_index.all_pairs()
    write("g4-sport-index.csv",
          ["country", "region", "sport", "segment", "score", "supply", "demand",
           "appetite", "agent_density", "country_confidence"],
          [[p["country"], p["region"], p["sport"], p["segment"], round(p["score"], 1),
            round(p["supply"], 3), round(p["demand"], 3), round(p["appetite"], 3),
            round(p["agent_density"], 3), p["country_confidence"]]
           for p in pairs])

    # G5 -- the competitive square. Two axes, six players, one empty corner.
    # Coordinates are editorial placements of the §3.5 table, not measurements;
    # the CSV exists so the chart is reproducible, not so it looks quantitative.
    write("g5-competitive-map.csv",
          ["player", "fan_monetisation_0_10", "long_tail_reach_0_10", "note"],
          [["Stride", 9, 9, "self-serve, long tail, both revenue sides"],
           ["TEKTA (Publicis/Kelce)", 0, 1, "human-mediated, excludes the tail by design"],
           ["Traditional agents", 0, 1, "10-20% for introductions"],
           ["Patreon / Substack", 9, 9, "no sport context, no sponsor side"],
           ["Passes / Fanfix", 8, 5, "monthly creator fee"],
           ["Influencer SaaS (Aspire, Grin)", 0, 4, "brand-side discovery only"],
           ["NIL collectives (US)", 1, 3, "US college, different legal frame"]])

    # G6 -- revenue composition. The point is the shape changing, not the total:
    # a subscription business in Y1 becoming a two-sided one by Y7.
    write("g6-revenue-mix.csv",
          ["year", "fan_eur_m", "sponsorship_eur_m", "saas_eur_m", "fan_share_pct"],
          [[r["year"], eur_m(r["rev_fan"]), eur_m(r["rev_sponsorship"]),
            eur_m(r["rev_saas"]), round(100 * r["rev_fan"] / r["revenue"], 1)]
           for r in seven])

    # G7 -- unit economics, both segments, ten years. The niche/popular gap is
    # the thesis; the convergence at the right-hand edge is the honesty.
    niche, popular = model.NICHE, model.POPULAR
    write("g7-unit-economics.csv",
          ["year", "niche_cac_eur", "popular_cac_eur",
           "niche_monetise_pct", "popular_monetise_pct",
           "niche_athlete_churn_pct", "popular_athlete_churn_pct",
           "niche_share_of_athletes_pct"],
          [[r["year"], niche.cac_eur[i], popular.cac_eur[i],
            round(100 * niche.monetise_rate[i], 1), round(100 * popular.monetise_rate[i], 1),
            round(100 * niche.athlete_churn_year[i], 1), round(100 * popular.athlete_churn_year[i], 1),
            round(100 * r["niche_share"], 1)]
           for i, r in enumerate(ten)])

    # G8 -- capital. The trough is the number that decides the raise, so the
    # chart needs the cash line and the rounds on the same axis.
    cash, balance = [], 0.0
    for r in ten:
        balance += r["fcf"]
        cash.append(balance)
    write("g8-cash-and-capital.csv",
          ["year", "fcf_eur_m", "cumulative_cash_before_raises_eur_m", "raise_eur_m", "stage"],
          [[r["year"], eur_m(r["fcf"]), eur_m(c),
            # From model.ROUNDS. G8 exists to show the pre-seed clearing the
            # trough, and when this was a literal it once drew the company
            # running out of cash -- the opposite of the section it illustrates.
            RAISE_EUR_M.get(r["year"], ""),
            # Placed where each gate is actually met rather than on the old
            # schedule. MRR here is recurring revenue -- fan subscriptions plus
            # sponsor SaaS, excluding one-off deals -- which is the basis
            # section 6.4 states. On that basis EUR 80k lands in Y4 and EUR 300k
            # in Y6 -- as they also do counting total revenue. Only the narrowest
            # reading differs: fan subscriptions alone would put them in Y5 and
            # Y7, which is why the plan defines the term rather than leaving it
            # implied.
            RAISE_STAGE.get(r["year"], "")]
           for r, c in zip(ten, cash)])

    # G9 -- the take-rate corridor. Both ends are real competitor rates, so this
    # is a range chart rather than a sensitivity nobody checks.
    import copy
    corridor = []
    for rate, against in ((0.10, "Patreon, published, all-in"),
                          (0.15, "our proposal"),
                          (0.20, "OnlyFans, derived from filed accounts")):
        alt = copy.deepcopy(model.A)
        alt.segments = model.A.segments      # deepcopy detaches the segment objects
        alt.take_fan = rate
        original, model.A = model.A, alt
        try:
            y7 = model.build()[6]
        finally:
            model.A = original
        corridor.append([f"{rate:.0%}", eur_m(y7["revenue"]), eur_m(y7["ebitda"]), against])
    write("g9-take-rate-corridor.csv",
          ["fan_take", "y7_revenue_eur_m", "y7_ebitda_eur_m", "against"], corridor)

    # G10 -- valuation. A football-field bar, DCF against the multiples, so the
    # disagreement between the two methods is visible rather than argued.
    y10 = ten[9]
    ev = model.valuation(ten)["enterprise_value"]
    write("g10-valuation.csv",
          ["method", "value_eur_m", "basis"],
          [["DCF", round(ev / 1e6, 1), "WACC 25%, terminal growth 3%"],
           ["4.0x revenue", round(4.0 * y10["revenue"] / 1e6, 1), "Y10 revenue"],
           ["6.5x revenue", round(6.5 * y10["revenue"] / 1e6, 1), "Y10 revenue"],
           ["9.0x revenue", round(9.0 * y10["revenue"] / 1e6, 1), "Y10 revenue"],
           ["14x EBITDA", round(14.0 * y10["ebitda"] / 1e6, 1), "Y10 EBITDA"]])

    # G11 -- COGS. The chart exists to kill an assumption: engineers read
    # "content platform" and picture a bandwidth bill. It is a payments bill.
    write("g11-cogs-composition.csv",
          ["year", "payments_eur_k", "infrastructure_eur_k", "moderation_eur_k",
           "verification_eur_k", "infrastructure_naive_eur_k"],
          [[r["year"], round(r["psp"] / 1e3), round(r["infra"] / 1e3),
            round(r["moderation"] / 1e3), round(r["verification"] / 1e3),
            round(r["infra_naive"] / 1e3)]
           for r in seven])


if __name__ == "__main__":
    main()
