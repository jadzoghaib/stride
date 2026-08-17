# 03 — Seven-Year Financial Model

Every table here is emitted by [`model.py`](model.py). Y1 = 2027, EUR.

```bash
python business-plan/model.py
```

---

## Drivers

| Driver | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Active athletes | 400 | 1,800 | 5,500 | 13,000 | 25,000 | 38,000 | 52,000 |
| Paying fans | 2,201 | 12,368 | 47,740 | 134,971 | 295,140 | 497,800 | 759,408 |
| Sponsorship deals | 25 | 176 | 889 | 3,356 | 8,970 | 17,518 | 27,331 |
| Paying sponsors (SaaS) | 2 | 15 | 58 | 152 | 300 | 480 | 700 |
| Headcount (FTE) | 1.5 | 3.0 | 7.0 | 14.0 | 24.0 | 36.0 | 50.0 |

---

## The two segments

The model runs **niche** and **popular** as separate cohorts, because they differ
in kind rather than in size. Sports are assigned by
[`sport_index.py`](sport_index.py); the strategy is in
[06](06-market-strategy.md).

| Assumption at Y7 | Niche | Popular | Why |
|---|---|---|---|
| Share who monetise fans | 48% | 30% | Niche athletes have no other channel; the need is acute |
| Paying fans per monetising athlete | 34 | 44 | Popular athletes have far larger followings but convert worse |
| Fan ARPU / month | €9.20 | €8.00 | Niche fans are participants buying knowledge, not spectators |
| Share landing a sponsorship deal | 16% | 30% | Sponsors are already active in popular sports |
| Average deal | €1,700 | €4,000 | The whole reason to enter popular sports |
| Athlete CAC | €32 | €78 | Displacing an agent costs more than reaching someone with none |

| Segment | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| **Niche — athletes** | 380 | 1,656 | 4,400 | 8,840 | 14,500 | 19,000 | 23,400 |
| **Niche — paying fans** | 2,128 | 11,658 | 40,700 | 101,483 | 191,400 | 279,680 | 381,888 |
| **Niche — net revenue** | €43k | €250k | €912k | €2.37M | €4.64M | €6.96M | €9.68M |
| **Popular — athletes** | 20 | 144 | 1,100 | 4,160 | 10,500 | 19,000 | 28,600 |
| **Popular — paying fans** | 73 | 710 | 7,040 | 33,488 | 103,740 | 218,120 | 377,520 |
| **Popular — net revenue** | €2k | €22k | €231k | €1.21M | €3.99M | €8.88M | €15.58M |
| Niche share of athletes | 95% | 92% | 80% | 68% | 58% | 50% | 45% |
| **Niche share of revenue** | **95%** | **92%** | **80%** | **66%** | **54%** | **44%** | **38%** |

**Niche funds the company; popular scales it.** Niche sports carry 95% of
revenue through Y2 — the entire period before the first external raise — and
fall to 38% by Y7 despite still being 45% of athletes, because popular-sport
deals are 2.4× larger. Neither segment alone produces this plan: without niche
there is no Y1, and without popular the Y7 number is a third smaller.

### How the fan number is built

Paying fans are **not** a top-down market share. Per segment:

```
athletes × share who monetise × paying fans per monetising athlete
```

The defensible input is the last term: **34 paying fans per niche athlete at
maturity.** A trail runner with 20,000 followers converting 0.17% of them is not
heroic — OnlyFans creators routinely convert 1–3% of smaller followings and
Patreon's benchmark is ~2%. The model sits an order of magnitude below both,
because sport fandom is less parasocial than the categories those platforms
serve. In the popular segment it is lower still as a share of following, which
is the point of splitting them.

---

## Marketplace volume (GMV)

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Fan GMV (subs + unlocks) | €284k | €1.65M | €6.51M | €18.59M | €41.01M | €69.15M | €105.84M |
| Sponsorship GMV | €27k | €238k | €1.66M | €7.85M | €24.77M | €54.64M | €93.82M |
| **Total GMV** | **€311k** | **€1.89M** | **€8.18M** | **€26.44M** | **€65.78M** | **€123.79M** | **€199.67M** |

GMV is the number a marketplace is judged on by investors; net revenue is the
number that pays salaries. Both are shown throughout so neither can flatter the
other.

---

## Net revenue

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Fan take (15%) | €43k | €248k | €977k | €2.79M | €6.15M | €10.37M | €15.88M |
| Sponsorship take (10%) | €3k | €24k | €166k | €785k | €2.48M | €5.46M | €9.38M |
| Sponsor SaaS | €6k | €42k | €180k | €529k | €1.15M | €2.07M | €3.36M |
| **Total net revenue** | **€51k** | **€314k** | **€1.32M** | **€4.10M** | **€9.78M** | **€17.91M** | **€28.62M** |

Growth: Y2 +516%, Y3 +321%, Y4 +210%, Y5 +139%, Y6 +83%, Y7 +60%. A decelerating
curve that stays above 50% through Y7 is what a Series B buyer wants to see.

---

## Profit and loss

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Net revenue | €51k | €314k | €1.32M | €4.10M | €9.78M | €17.91M | €28.62M |
| Payment processing | €17k | €100k | €414k | €1.27M | €3.03M | €5.48M | €8.68M |
| Payouts | €1k | €6k | €27k | €84k | €205k | €380k | €608k |
| Infrastructure (AWS) | €3k | €10k | €33k | €88k | €183k | €290k | €419k |
| Moderation | €1k | €6k | €17k | €41k | €79k | €120k | €165k |
| **Gross profit** | **€30k** | **€192k** | **€832k** | **€2.62M** | **€6.29M** | **€11.64M** | **€18.75M** |
| Gross margin | 58% | 61% | 63% | 64% | 64% | 65% | 66% |
| People | €57k | €156k | €420k | €896k | €1.58M | €2.45M | €3.50M |
| Marketing / CAC | €29k | €118k | €384k | €934k | €1.70M | €2.33M | €2.98M |
| Legal & compliance | €18k | €45k | €90k | €150k | €200k | €235k | €270k |
| Other opex | €4k | €25k | €106k | €328k | €782k | €1.43M | €2.29M |
| **EBITDA** | **−€79k** | **−€152k** | **−€168k** | **€308k** | **€2.02M** | **€5.20M** | **€9.71M** |
| Tax (15%) | €0 | €0 | €0 | €46k | €304k | €780k | €1.46M |
| **Free cash flow** | **−€79k** | **−€152k** | **−€168k** | **€262k** | **€1.72M** | **€4.42M** | **€8.25M** |

**Gross margin of 58–66% is the honest number for a payments-heavy marketplace.**
Pure SaaS would be 80%+; the difference is the payment rail, and no amount of
engineering removes it. Investors who benchmark this against SaaS comparables
should be pointed at Etsy (~70%), Fiverr (~80% but higher take), and OnlyFans'
parent (~85% at a 20% take on far larger tickets).

---

## Cash

| Year | Free cash flow | Cumulative |
|---|---|---|
| Y1 | −€79k | −€79k |
| Y2 | −€152k | −€231k |
| Y3 | −€168k | −€399k |
| Y4 | €262k | −€137k |
| Y5 | €1.72M | €1.58M |
| Y6 | €4.42M | €6.00M |
| Y7 | €8.25M | €14.25M |

| Capital requirement | Value |
|---|---|
| Deepest cumulative cash position | −€399k (Y3) |
| Buffer at 40% | €160k |
| **Total capital to fund the plan** | **€558k** |
| First EBITDA-positive year | **Y4** |

**€558k is a strikingly small number for a plan that reaches €28.6M of revenue,
and that should be interrogated rather than celebrated.** It is small because
the model hires behind revenue rather than ahead of it, and because fan
acquisition is free. A growth-optimised version — hiring 12 months earlier,
buying athlete acquisition harder, entering three markets simultaneously —
would burn €3–5M and reach Y7 revenue a year or two sooner. That is a strategy
choice, not a modelling error. See [scenarios](#scenarios).

---

## Scenarios

The base case above assumes conversion holds. The two assumptions most likely to
be wrong are **fans per athlete** and **share of athletes who monetise**.

| Scenario | Change vs base | Y7 revenue | Y7 EBITDA | Capital need |
|---|---|---|---|---|
| **Conservative** | Fans/athlete −30%, monetise rate −25% | ~€16M | ~€4.0M | ~€0.9M |
| **Base** | As modelled | €28.62M | €9.71M | €558k |
| **Growth-optimised** | Hire 12mo ahead, 3 markets from Y2 | ~€42M | ~€11M | €3–5M |

To run these, edit `Assumptions` in `model.py` and rerun. The conservative case
still reaches profitability — later, at Y5 rather than Y4 — which is the
robustness test that matters.

---

## What the model deliberately excludes

Named so nobody thinks they were forgotten:

| Excluded | Why |
|---|---|
| Managed matchmaking and market-intelligence revenue | Real, but later-stage; the plan should not depend on them |
| Reserved-instance / Savings Plan discounts | 25–40% on compute — upside, not plan |
| Processor renegotiation below 2.9% | Available at volume, treated as upside |
| Grant income (Neotec, ENISA) | Non-dilutive but uncertain; see [04](04-capital-and-valuation.md) |
| Working capital timing | Payout float is favourable (we hold fan money before paying athletes) — a real cash benefit, unmodelled |
| FX | EUR-only until the UK or US entry |
| Churn of *athletes* | Modelled only as net active count, not as a cohort decay |

That last one is the weakest part of the model and the first thing I would fix
with real data. Athlete churn compounds against every revenue stream at once.
