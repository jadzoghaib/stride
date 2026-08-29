"""The derivation the MarketModel sheet displays, written once, in code.

    Comparables (published facts) -> MarketModel (derives ours) -> Assumptions

The workbook has shown this chain since it was built, and the README claimed you
could follow any assumption backwards to a cited number. That was very nearly
true and not quite: the MarketModel sheet computes each figure from
`comparables_data.py`, and the Assumptions sheet then carries a *typed* number
that happens to match. No cell in the workbook references MarketModel, so
nothing enforced the match — change a published figure and the derivation would
move while every assumption downstream stayed exactly where it was.

Measuring the gap is what settled how to close it. Every literal in `model.py`
is this derivation rounded to the precision it is written at: 37.026 fans is
written 37, EUR 9.490 is written 9.50, and 0.054993 churn is written 0.055. Not
"close to" — equal, once you round to the number of digits actually shown. (In
raw terms the largest difference is 0.53%, on popular ARPU, which is what
rounding 8.256 to one decimal costs.) So the literals are not an independent
guess that happens to land nearby.

That rounding is also what rules out the obvious fix. Pointing the workbook's
Assumptions cells at MarketModel would replace 37 with 37.026 and set the
workbook a hair away from the Python everywhere, which the Check sheet exists to
forbid. So the judgement factors live here instead, the workbook renders them,
and `scripts/doc_consistency.py` asserts the derivation still rounds to the
literals — exactly, using `PRECISION` below, because a percentage tolerance
would let the chain drift by a little bit forever. Nothing moves, and it can no
longer rot in silence.

Every constant below is a judgement, not a fact — the facts are all in
`comparables_data.py`. Each is annotated with what it claims and how confident
that claim is, because these are the numbers an investor should argue with.
"""

from __future__ import annotations

from comparables_data import PLATFORM_FACTS

# ── our judgement, applied to published benchmarks ──────────────────────────

#: +6% on the Patreon members-per-creator benchmark. Sport audiences are smaller
#: but convert better, because the fan usually does the sport themselves.
NICHE_FPA_ADJUSTMENT = 1.06
#: +37%. Much larger followings, much weaker conversion — more paying fans in
#: absolute terms even though a smaller share of them converts.
POPULAR_FPA_ADJUSTMENT = 1.37

#: Subscription tiers and the assumed distribution across them. Replace the mix
#: with the real one the moment there is one; the prices are a product decision.
TIER_PRICES = (4.99, 9.99, 24.99)
TIER_MIX = (0.40, 0.50, 0.10)

#: The annual tier, priced at roughly nine months of Insider. It lives here with
#: the others because it kept drifting when it did not: `model.py` had its own
#: copy at EUR 99 while every document and the retention guard said EUR 89.
SEASON_PASS_EUR = 89.00

#: Niche fans buy knowledge and sit at the tier mix above.
NICHE_ARPU_FACTOR = 1.00
#: -13%: popular-sport fans skew to the cheapest tier.
POPULAR_ARPU_FACTOR = 0.87

#: Target share of subscribers on the season pass. The one lever that improves
#: churn without changing the product.
ANNUAL_PLAN_SHARE = 0.30

#: THE MOST OPTIMISTIC JUDGEMENT IN THE MODEL, AND UNTESTED: niche fans churn
#: 45% slower than the Patreon benchmark, because training content is habitual
#: and competitive seasons create renewal moments.
#:
#: This carried the note "if this is wrong, Y10 revenue falls by roughly EUR 7M"
#: for a long time, and that was wrong by two orders of magnitude. Re-run at
#: benchmark churn, Y10 revenue moves by +0.07M — it goes slightly *up*, and Y10
#: paying fans are identical to the digit.
#:
#: They are identical because `fans_per_athlete` is a target this model solves
#: backwards from, and marketing is driven by athlete adds rather than fan adds.
#: Churn therefore does not change how many fans exist; it changes how many must
#: be acquired to stand still — 1.32M gross adds a year becomes 1.65M, a 25%
#: heavier acquisition burden, for EUR 0.86M of cumulative free cash flow.
#:
#: So the risk is real and this model understates it by construction. Being
#: wrong here does not dent the revenue line; it means the fan targets the whole
#: plan is built on need a quarter more acquisition than budgeted to hold.
NICHE_ENGAGEMENT = 0.55
#: 15% better than benchmark: impulse follows a result, with many free
#: substitutes — but still a sport fan rather than a general creator audience.
POPULAR_ENGAGEMENT = 0.85


def fact(company: str, metric: str) -> float:
    """One published figure, by the name it is cited under."""
    for name, value, _unit, firm, *_ in PLATFORM_FACTS:
        if firm == company and name == metric:
            return value
    raise KeyError(f"comparables_data.py has no {metric!r} for {company!r}")


def members_per_creator() -> float:
    """The single most useful benchmark in the file: measured, not modelled."""
    return (fact("Patreon", "Active paying members")
            / fact("Patreon", "Creators with >=1 paying member"))


def weighted_arpu() -> float:
    """Monthly ARPU implied by our own tier prices and assumed mix.

    Cross-check: Patreon publishes $6.10 average support and an $8–12 typical
    band. Landing inside that band from an independent tier build is a good sign.
    """
    return sum(price * share for price, share in zip(TIER_PRICES, TIER_MIX))


def blended_churn() -> float:
    """Benchmark monthly churn, adjusted for our annual-plan mix."""
    low = fact("Patreon", "Monthly churn (low)")
    high = fact("Patreon", "Monthly churn (high)")
    annual_multiplier = fact("Patreon", "Annual-plan churn multiplier")
    midpoint = (low + high) / 2
    return (midpoint * (1 - ANNUAL_PLAN_SHARE)
            + midpoint * annual_multiplier * ANNUAL_PLAN_SHARE)


#: Digits each quantity is written to in `model.py`. The literals are the
#: derivation rounded to these, so a check can be exact — with a percentage
#: tolerance instead, a comparable could move a little at a time and never trip
#: it, which is precisely the silent drift the guard exists to stop.
PRECISION = {
    "niche_fans_per_athlete": 0,
    "popular_fans_per_athlete": 0,
    "niche_fan_arpu_month": 1,
    "popular_fan_arpu_month": 1,
    "niche_fan_churn_month": 3,
    "popular_fan_churn_month": 3,
}


def derived() -> dict[str, float]:
    """The six numbers the MarketModel sheet hands to Assumptions, at maturity."""
    mpc, arpu, churn = members_per_creator(), weighted_arpu(), blended_churn()
    return {
        "niche_fans_per_athlete": mpc * NICHE_FPA_ADJUSTMENT,
        "popular_fans_per_athlete": mpc * POPULAR_FPA_ADJUSTMENT,
        "niche_fan_arpu_month": arpu * NICHE_ARPU_FACTOR,
        "popular_fan_arpu_month": arpu * POPULAR_ARPU_FACTOR,
        "niche_fan_churn_month": churn * NICHE_ENGAGEMENT,
        "popular_fan_churn_month": churn * POPULAR_ENGAGEMENT,
    }


if __name__ == "__main__":
    print(f"members per paying creator: {members_per_creator():.3f}")
    print(f"weighted ARPU: EUR {weighted_arpu():.2f}   blended churn: {blended_churn():.4f}\n")
    for name, value in derived().items():
        print(f"  {name:28} {value:9.3f}")
