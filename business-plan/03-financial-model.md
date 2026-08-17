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
| Paying fans | 1,584 | 9,360 | 37,950 | 114,920 | 259,000 | 444,600 | 665,600 |
| Sponsorship deals | 38 | 257 | 1,155 | 3,757 | 9,025 | 15,960 | 25,168 |
| Paying sponsors (SaaS) | 2 | 15 | 58 | 152 | 300 | 480 | 700 |
| Headcount (FTE) | 1.5 | 3.0 | 7.0 | 14.0 | 24.0 | 36.0 | 50.0 |

### How the fan number is built

Paying fans are **not** assumed as a top-down market share. They are:

```
athletes × share who monetise × paying fans per monetising athlete
```

| | Y1 | Y4 | Y7 |
|---|---|---|---|
| Athletes | 400 | 13,000 | 52,000 |
| Share who monetise fans | 22% | 34% | 40% |
| Paying fans per monetising athlete | 18 | 26 | 32 |
| **Paying fans** | **1,584** | **114,920** | **665,600** |

The defensible part is the last row of inputs: **32 paying fans per athlete at
maturity.** An athlete with 20,000 Instagram followers converting 0.16% of them
is not a heroic assumption — OnlyFans creators routinely convert 1–3% of a
smaller following, and Patreon's benchmark is ~2%. The model is deliberately
below both because sport fandom is less parasocial than the categories those
platforms serve.

---

## Marketplace volume (GMV)

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Fan GMV (subs + unlocks) | €192k | €1.18M | €4.92M | €15.27M | €35.24M | €61.22M | €92.73M |
| Sponsorship GMV | €46k | €360k | €1.91M | €7.14M | €18.95M | €35.91M | €60.40M |
| **Total GMV** | **€239k** | **€1.54M** | **€6.82M** | **€22.40M** | **€54.20M** | **€97.13M** | **€153.13M** |

GMV is the number a marketplace is judged on by investors; net revenue is the
number that pays salaries. Both are shown throughout so neither can flatter the
other.

---

## Net revenue

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Fan take (15%) | €29k | €177k | €738k | €2.29M | €5.29M | €9.18M | €13.91M |
| Sponsorship take (10%) | €5k | €36k | €191k | €714k | €1.90M | €3.59M | €6.04M |
| Sponsor SaaS | €6k | €42k | €180k | €529k | €1.15M | €2.07M | €3.36M |
| **Total net revenue** | **€39k** | **€256k** | **€1.11M** | **€3.53M** | **€8.33M** | **€14.85M** | **€23.31M** |

Growth: Y2 +556%, Y3 +334%, Y4 +217%, Y5 +136%, Y6 +78%, Y7 +57%. A decelerating
curve that stays above 50% through Y7 is what a Series B buyer wants to see.

---

## Profit and loss

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Net revenue | €39k | €256k | €1.11M | €3.53M | €8.33M | €14.85M | €23.31M |
| Payment processing | €12k | €77k | €332k | €1.07M | €2.53M | €4.49M | €6.97M |
| Payouts | €777 | €5k | €22k | €71k | €170k | €303k | €475k |
| Infrastructure (AWS) | €2k | €9k | €32k | €85k | €177k | €281k | €403k |
| Moderation | €1k | €6k | €17k | €41k | €79k | €120k | €165k |
| **Gross profit** | **€23k** | **€159k** | **€706k** | **€2.27M** | **€5.38M** | **€9.66M** | **€15.30M** |
| Gross margin | 58% | 62% | 64% | 64% | 65% | 65% | 66% |
| People | €57k | €156k | €420k | €896k | €1.58M | €2.45M | €3.50M |
| Marketing / CAC | €31k | €126k | €387k | €899k | €1.58M | €2.12M | €2.72M |
| Legal & compliance | €18k | €45k | €90k | €150k | €200k | €235k | €270k |
| Other opex | €3k | €20k | €89k | €283k | €667k | €1.19M | €1.86M |
| **EBITDA** | **−€87k** | **−€188k** | **−€280k** | **€43k** | **€1.35M** | **€3.67M** | **€6.94M** |
| Tax (15%) | €0 | €0 | €0 | €6k | €202k | €550k | €1.04M |
| **Free cash flow** | **−€87k** | **−€188k** | **−€280k** | **€36k** | **€1.15M** | **€3.12M** | **€5.90M** |

**Gross margin of 58–66% is the honest number for a payments-heavy marketplace.**
Pure SaaS would be 80%+; the difference is the payment rail, and no amount of
engineering removes it. Investors who benchmark this against SaaS comparables
should be pointed at Etsy (~70%), Fiverr (~80% but higher take), and OnlyFans'
parent (~85% at a 20% take on far larger tickets).

---

## Cash

| Year | Free cash flow | Cumulative |
|---|---|---|
| Y1 | −€87k | −€87k |
| Y2 | −€188k | −€275k |
| Y3 | −€280k | −€555k |
| Y4 | €36k | −€518k |
| Y5 | €1.15M | €628k |
| Y6 | €3.12M | €3.74M |
| Y7 | €5.90M | €9.65M |

| Capital requirement | Value |
|---|---|
| Deepest cumulative cash position | −€555k (Y3) |
| Buffer at 40% | €222k |
| **Total capital to fund the plan** | **€777k** |
| First EBITDA-positive year | **Y4** |

**€777k is a strikingly small number for a plan that reaches €23M of revenue,
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
| **Conservative** | Fans/athlete −30%, monetise rate −25% | ~€13M | ~€2.9M | ~€1.1M |
| **Base** | As modelled | €23.31M | €6.94M | €777k |
| **Growth-optimised** | Hire 12mo ahead, 3 markets from Y2 | ~€34M | ~€8M | €3–5M |

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
