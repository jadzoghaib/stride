# 03 — Seven-Year Financial Model

Every table here is emitted by [`model.py`](model.py). Y1 = 2027, EUR.

```bash
python business-plan/model.py
```

---

## Drivers

<!-- MODEL:drivers -->
| Driver | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Active athletes | 400 | 1,800 | 5,500 | 13,000 | 25,000 | 38,000 | 52,000 | 65,000 | 76,000 | 85,000 |
| Paying fans | 2,058 | 12,217 | 46,333 | 130,165 | 285,069 | 490,646 | 759,408 | 1,007,675 | 1,237,523 | 1,415,029 |
| Sponsorship deals | 25 | 176 | 889 | 3,356 | 8,970 | 17,518 | 27,331 | 37,742 | 44,472 | 54,271 |
| Paying sponsors (SaaS) | 0 | 14 | 58 | 152 | 300 | 480 | 700 | 920 | 1,120 | 1,280 |
| Headcount (FTE) | 1.5 | 3.0 | 7.0 | 14.0 | 24.0 | 36.0 | 50.0 | 62.0 | 72.0 | 80.0 |
<!-- /MODEL:drivers -->

---

## Retention and acquisition

Fans and athletes both churn, and the model runs the decay month by month rather
than asserting a year-end stock. Two consequences that a net-stock model cannot
show:

<!-- MODEL:churn -->
| Retention & acquisition | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Paying fans, year end | 2,058 | 12,217 | 46,333 | 130,165 | 285,069 | 490,646 | 759,408 | 1,007,675 | 1,237,523 | 1,415,029 |
| Paying fans, average | 1,306 | 8,461 | 33,681 | 98,964 | 227,425 | 414,208 | 657,722 | 913,140 | 1,149,376 | 1,346,877 |
| Fans acquired (gross) | 3,298 | 18,093 | 65,403 | 174,501 | 362,576 | 582,238 | 835,123 | 1,035,072 | 1,206,017 | 1,316,405 |
| Fans lost to churn | 1,241 | 7,934 | 31,287 | 90,668 | 207,672 | 376,662 | 566,362 | 786,805 | 976,169 | 1,138,899 |
| Athletes acquired (gross) | 400 | 1,509 | 4,141 | 8,765 | 14,808 | 18,170 | 21,600 | 22,984 | 23,252 | 22,923 |
| Athletes lost to churn | 0 | 109 | 441 | 1,265 | 2,808 | 5,170 | 7,600 | 9,984 | 12,252 | 13,923 |
<!-- /MODEL:churn -->

**Revenue accrues on the average fan count, not the year-end count.** Charging
twelve months at the December number overstates revenue by roughly a third
during fast growth — the previous version of this model did exactly that.

**Gross adds dwarf net adds.** At 9%/month a cohort retains 32% over a year, so
most of next year's fans are replacements for this year's. In Y7 we acquire
831k fans to finish with 759k, having lost 570k. That is the real acquisition
machine, and it was invisible until churn was modelled explicitly.

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

<!-- MODEL:gmv -->
| Marketplace volume | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Fan GMV (subs + unlocks) | €169k | €1.13M | €4.62M | €13.71M | €31.78M | €57.77M | €91.87M | €128.38M | €163.11M | €193.09M |
| Sponsorship GMV | €27k | €238k | €1.66M | €7.85M | €24.77M | €54.64M | €93.82M | €136.85M | €169.90M | €217.03M |
| **Total GMV** | €195k | €1.37M | €6.28M | €21.56M | €56.55M | €112.42M | €185.70M | €265.23M | €333.01M | €410.11M |
<!-- /MODEL:gmv -->

GMV is the number a marketplace is judged on by investors; net revenue is the
number that pays salaries. Both are shown throughout so neither can flatter the
other.

---

## Net revenue

<!-- MODEL:revenue -->
| Net revenue | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Fan take (15%) | €25k | €170k | €692k | €2.06M | €4.77M | €8.67M | €13.78M | €19.26M | €24.47M | €28.96M |
| Sponsorship take (10%) | €3k | €24k | €166k | €785k | €2.48M | €5.46M | €9.38M | €13.68M | €16.99M | €21.70M |
| Sponsor SaaS | €1k | €38k | €180k | €529k | €1.15M | €2.07M | €3.36M | €4.75M | €6.12M | €7.30M |
| **Total net revenue** | €29k | €231k | €1.04M | €3.37M | €8.40M | €16.20M | €26.52M | €37.69M | €47.57M | €57.96M |
<!-- /MODEL:revenue -->

Growth: Y2 +516%, Y3 +321%, Y4 +210%, Y5 +139%, Y6 +83%, Y7 +60%. A decelerating
curve that stays above 50% through Y7 is what a Series B buyer wants to see.

---

## Profit and loss

<!-- MODEL:pl -->
| P&L | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Net revenue | €29k | €231k | €1.04M | €3.37M | €8.40M | €16.20M | €26.52M | €37.69M | €47.57M | €57.96M |
| Payment processing | €8k | €57k | €245k | €783k | €1.94M | €3.71M | €6.04M | €8.55M | €10.78M | €13.07M |
| Payouts | €645 | €4k | €20k | €67k | €174k | €341k | €561k | €798k | €1.00M | €1.23M |
| Infrastructure (AWS) | €3k | €10k | €33k | €87k | €181k | €289k | €419k | €534k | €634k | €713k |
| Moderation | €1k | €6k | €17k | €41k | €79k | €120k | €165k | €206k | €241k | €269k |
| Athlete verification | €745 | €3k | €9k | €19k | €30k | €37k | €43k | €46k | €47k | €47k |
| **Gross profit** | €16k | €151k | €714k | €2.37M | €5.99M | €11.70M | €19.30M | €27.56M | €34.86M | €42.63M |
| Gross margin | 54% | 65% | 69% | 70% | 71% | 72% | 73% | 73% | 73% | 74% |
| People | €57k | €156k | €420k | €896k | €1.58M | €2.45M | €3.50M | €4.46M | €5.33M | €6.08M |
| Marketing / CAC | €29k | €120k | €395k | €975k | €1.82M | €2.59M | €3.42M | €3.68M | €3.65M | €3.36M |
| Legal & compliance | €18k | €45k | €90k | €150k | €200k | €235k | €270k | €300k | €325k | €345k |
| Other opex | €2k | €19k | €83k | €270k | €672k | €1.30M | €2.12M | €3.02M | €3.81M | €4.64M |
| **EBITDA** | €-91k | €-188k | €-274k | €81k | €1.72M | €5.13M | €9.99M | €16.10M | €21.75M | €28.21M |
| Tax | €0 | €0 | €0 | €12k | €258k | €770k | €1.50M | €2.42M | €3.26M | €4.23M |
| **Free cash flow** | €-91k | €-188k | €-274k | €69k | €1.46M | €4.36M | €8.49M | €13.69M | €18.49M | €23.98M |
<!-- /MODEL:pl -->

**Gross margin of 58–66% is the honest number for a payments-heavy marketplace.**
Pure SaaS would be 80%+; the difference is the payment rail, and no amount of
engineering removes it. Investors who benchmark this against SaaS comparables
should be pointed at Etsy (~70%), Fiverr (~80% but higher take), and OnlyFans'
parent (~85% at a 20% take on far larger tickets).

---

## Cash

| Year | Free cash flow | Cumulative |
<!-- MODEL:cash -->
| Year | Free cash flow | Cumulative |
|---|---|---|
| Y1 | €-91k | €-91k |
| Y2 | €-188k | €-279k |
| Y3 | €-274k | €-553k |
| Y4 | €69k | €-484k |
| Y5 | €1.46M | €977k |
| Y6 | €4.36M | €5.34M |
| Y7 | €8.49M | €13.83M |
| Y8 | €13.69M | €27.52M |
| Y9 | €18.49M | €46.01M |
| Y10 | €23.98M | €69.99M |
<!-- /MODEL:cash -->

| Capital requirement | Value |
<!-- MODEL:funding -->
| Capital requirement | Value |
|---|---|
| Deepest cumulative cash position | €-553k |
| Year it occurs | Y3 |
| Buffer at 40% (hiring slips, churn worse) | €221k |
| **Total capital to fund the plan** | **€774k** |
| First EBITDA-positive year | Y4 |
<!-- /MODEL:funding -->

**€952k is a small number for a plan that reaches €26.6M of revenue,
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
| **Conservative** | Fans/athlete −30%, monetise rate −25% | ~€15M | ~€3.4M | ~€1.3M |
| **Base** | As modelled | €26.57M | €8.20M | €952k |
| **Growth-optimised** | Hire 12mo ahead, 3 markets from Y2 | ~€39M | ~€9M | €3–5M |

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
| Cohort *quality* drift | Later cohorts may convert worse than early ones; not modelled |

Athlete and fan churn are now modelled explicitly. The remaining weakness is
that all cohorts are assumed to behave alike — in practice the athletes who join
in Y6 are unlikely to convert as well as the hand-picked ones in Y1.
