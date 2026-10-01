# 03: Seven-Year Financial Model

Every table here is emitted by [`model.py`](model.py). Y1 = 2027, EUR.

```bash
python business-plan/model.py
```

---

## Drivers

<!-- MODEL:drivers -->
| Driver | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Active athletes | 250 | 750 | 1,700 | 2,800 | 4,000 | 5,200 | 6,300 | 7,200 | 7,900 | 8,500 |
| Paying fans | 1,286 | 5,093 | 14,334 | 28,169 | 46,066 | 67,882 | 92,005 | 111,619 | 128,637 | 141,503 |
| Sponsorship deals | 15 | 73 | 275 | 723 | 1,435 | 2,397 | 3,311 | 4,181 | 4,623 | 5,427 |
| Paying sponsors (SaaS) | 0 | 3 | 18 | 46 | 76 | 102 | 124 | 142 | 158 | 170 |
| Headcount (FTE) | 1.0 | 1.0 | 1.5 | 2.0 | 4.0 | 7.0 | 10.0 | 12.5 | 14.5 | 16.0 |
<!-- /MODEL:drivers -->

---

## Retention and acquisition

Fans and athletes both churn, and the model runs the decay month by month rather
than asserting a year-end stock. Two consequences that a net-stock model cannot
show:

<!-- MODEL:churn -->
| Retention & acquisition | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Paying fans, year end | 1,286 | 5,093 | 14,334 | 28,169 | 46,066 | 67,882 | 92,005 | 111,619 | 128,637 | 141,503 |
| Paying fans, average | 816 | 3,686 | 10,913 | 23,047 | 39,464 | 59,832 | 82,915 | 104,178 | 122,124 | 136,574 |
| Fans acquired (gross) | 2,062 | 7,315 | 19,515 | 35,368 | 54,613 | 76,887 | 96,227 | 109,972 | 121,242 | 128,698 |
| Fans lost to churn | 775 | 3,509 | 10,274 | 21,533 | 36,716 | 55,071 | 72,104 | 90,358 | 104,225 | 115,832 |
| Athletes acquired (gross) | 250 | 568 | 1,134 | 1,491 | 1,805 | 2,027 | 2,140 | 2,110 | 2,057 | 2,047 |
| Athletes lost to churn | 0 | 68 | 184 | 391 | 605 | 827 | 1,040 | 1,210 | 1,357 | 1,447 |
<!-- /MODEL:churn -->

**Revenue accrues on the average fan count, not the year-end count.** Charging
twelve months at the December number overstates revenue by roughly a third
during fast growth: the previous version of this model did exactly that.

**Gross adds dwarf net adds.** At 9%/month a cohort retains 32% over a year, so
most of next year's fans are replacements for this year's. In Y7 we acquire
96k fans to finish with 92k, having lost 72k. That is the real acquisition
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
| **Niche: athletes** | 238 | 690 | 1,360 | 1,904 | 2,320 | 2,600 | 2,835 |
| **Niche: paying fans** | 1,252 | 4,858 | 12,580 | 21,858 | 30,624 | 38,272 | 46,267 |
| **Niche: net revenue** | €14k | €64k | €184k | €361k | €555k | €737k | €916k |
| **Popular: athletes** | 12 | 60 | 340 | 896 | 1,680 | 2,600 | 3,465 |
| **Popular: paying fans** | 35 | 235 | 1,754 | 6,311 | 15,442 | 29,610 | 45,738 |
| **Popular: net revenue** | €1k | €6k | €48k | €184k | €474k | €947k | €1.50M |
| Niche share of athletes | 95% | 92% | 80% | 68% | 58% | 50% | 45% |
| **Niche share of total revenue** | **91%** | **82%** | **64%** | **51%** | **42%** | **35%** | **30%** |

**Niche funds the company; popular scales it.** Niche sports carry
91% of total revenue in Y1 and 82% in Y2,
the entire period before the second tranche, and fall to 30% by
Y7 despite still being 45%
of athletes, because popular-sport
deals are 2.4× larger. Neither segment alone produces this plan: without niche
there is no Y1, and without popular the Y7 number is a third smaller.

### How the fan number is built

Paying fans are **not** a top-down market share. Per segment:

```
athletes × share who monetise × paying fans per monetising athlete
```

The defensible input is the last term: **34 paying fans per niche athlete at
maturity.** A trail runner with 20,000 followers converting 0.17% of them is not
heroic: OnlyFans creators routinely convert 1–3% of smaller followings and
Patreon's benchmark is ~2%. The model sits an order of magnitude below both,
because sport fandom is less parasocial than the categories those platforms
serve. In the popular segment it is lower still as a share of following, which
is the point of splitting them.

---

## Marketplace volume (GMV)

<!-- MODEL:gmv -->
| Marketplace volume | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Fan GMV (subs + unlocks) | €87k | €407k | €1.24M | €2.64M | €4.56M | €6.90M | €9.57M | €12.11M | €14.32M | €16.18M |
| Sponsorship GMV | €17k | €99k | €515k | €1.69M | €3.96M | €7.48M | €11.37M | €15.16M | €17.66M | €21.70M |
| **Total GMV** | €104k | €506k | €1.75M | €4.33M | €8.52M | €14.37M | €20.94M | €27.27M | €31.99M | €37.88M |
<!-- /MODEL:gmv -->

GMV is the number a marketplace is judged on by investors; net revenue is the
number that pays salaries. Both are shown throughout so neither can flatter the
other.

---

## Net revenue

<!-- MODEL:revenue -->
| Net revenue | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Fan take (15%) | €13k | €61k | €185k | €396k | €684k | €1.03M | €1.44M | €1.82M | €2.15M | €2.43M |
| Sponsorship take (blended by plan) | €2k | €9k | €46k | €149k | €346k | €649k | €982k | €1.30M | €1.52M | €1.86M |
| Sponsor SaaS | €537 | €8k | €56k | €159k | €292k | €441k | €595k | €733k | €863k | €969k |
| **Total net revenue** | €15k | €78k | €288k | €704k | €1.32M | €2.12M | €3.01M | €3.85M | €4.53M | €5.25M |
<!-- /MODEL:revenue -->

Growth: Y2 +414%, Y3 +268%, Y4 +144%, Y5 +88%, Y6 +61%, Y7 +42%. A decelerating curve that stays above 50% through
Y6 is the shape a marketplace should have.

---

## Profit and loss

<!-- MODEL:pl -->
| P&L | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Net revenue | €15k | €78k | €288k | €704k | €1.32M | €2.12M | €3.01M | €3.85M | €4.53M | €5.25M |
| Payment processing | €5k | €25k | €79k | €180k | €331k | €528k | €752k | €967k | €1.14M | €1.32M |
| Payouts | €403 | €2k | €6k | €15k | €29k | €48k | €69k | €90k | €106k | €124k |
| Infrastructure (AWS) | €2k | €6k | €14k | €28k | €45k | €62k | €78k | €92k | €105k | €117k |
| Moderation | €792 | €2k | €5k | €9k | €13k | €16k | €20k | €23k | €25k | €27k |
| Athlete verification | €466 | €1k | €3k | €3k | €4k | €4k | €4k | €4k | €4k | €4k |
| **Gross profit** | €6k | €42k | €181k | €468k | €900k | €1.47M | €2.09M | €2.68M | €3.15M | €3.66M |
| Gross margin | 42% | 54% | 63% | 67% | 68% | 69% | 69% | 69% | 70% | 70% |
| People | €38k | €52k | €90k | €128k | €264k | €476k | €700k | €900k | €1.07M | €1.22M |
| Marketing / CAC | €20k | €51k | €117k | €220k | €313k | €344k | €344k | €317k | €307k | €276k |
| Legal & compliance | €18k | €45k | €90k | €150k | €200k | €235k | €270k | €300k | €325k | €345k |
| Other opex | €1k | €6k | €23k | €56k | €106k | €170k | €241k | €308k | €362k | €420k |
| **EBITDA** | €-71k | €-111k | €-140k | €-86k | €17k | €240k | €535k | €852k | €1.08M | €1.40M |
| Tax | €0 | €0 | €0 | €0 | €0 | €0 | €7k | €97k | €122k | €163k |
| Working capital movement | €-11k | €-24k | €-61k | €-112k | €-175k | €-233k | €-260k | €-247k | €-191k | €-219k |
| Capex (capitalised development) | €11k | €16k | €27k | €38k | €79k | €143k | €210k | €270k | €322k | €365k |
| **Free cash flow** | €-72k | €-103k | €-105k | €-12k | €113k | €330k | €578k | €733k | €828k | €1.10M |
<!-- /MODEL:pl -->

Free cash flow is EBITDA less tax, working capital movement and capex, not
EBITDA less tax, which is what the table implied while those two rows were
missing. **Working capital is negative in every year, meaning it releases cash
rather than consuming it**: fan GMV is held about fifteen days before athletes
are paid, and that float is larger than sponsor receivables net of payables. It
is a real cash benefit and it is also a liability to the athletes, so it funds
growth but is not available to lose.

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
| Y1 | €-72k | €-72k |
| Y2 | €-103k | €-175k |
| Y3 | €-105k | €-280k |
| Y4 | €-12k | €-292k |
| Y5 | €113k | €-179k |
| Y6 | €330k | €151k |
| Y7 | €578k | €728k |
| Y8 | €733k | €1.46M |
| Y9 | €828k | €2.29M |
| Y10 | €1.10M | €3.39M |
<!-- /MODEL:cash -->

| Capital requirement | Value |
<!-- MODEL:funding -->
| Capital requirement | Value |
|---|---|
| Deepest cumulative cash position | €-292k |
| Year it occurs | Y4 |
| Buffer at 40% (hiring slips, churn worse) | €117k |
| **Total capital to fund the plan** | **€409k** |
| First EBITDA-positive year | Y5 |
<!-- /MODEL:funding -->

**€409k is a small number for a plan that reaches €3.01M of revenue by Y7,
and that should be interrogated rather than celebrated.** It is small because
the model hires behind revenue rather than ahead of it, and because fan
acquisition is free. A growth-optimised version: hiring 12 months earlier,
buying athlete acquisition harder, entering three markets simultaneously, would burn €3–5M and reach Y7 revenue a year or two sooner. That is a strategy
choice, not a modelling error. See [scenarios](#scenarios).

---

## Scenarios

The base case above assumes conversion holds. The two assumptions most likely to
be wrong are **fans per athlete** and **share of athletes who monetise**.

| Scenario | Change vs base | Y7 revenue | Y7 EBITDA | Capital need |
|---|---|---|---|---|
| Pessimistic | Fans/athlete −30%, monetise −25%, **niche churn at benchmark** | €2.34M | €0.19M | €827k |
| **Base** | As modelled | €3.01M | €0.53M | €409k |
| Optimistic | Fans/athlete +25%, monetise +20% | €3.59M | €0.83M | €314k |

These are the same three cases as §7.6 of the body, generated from
`model.scenario_table()`, which re-runs the whole model against changed drivers
rather than adjusting the base result. A fourth case, hiring twelve months ahead
and opening three markets from Y2, used to sit in this table with figures nothing
produced. It is a real upside and it needs capital the plan has not raised, so it
belongs in the growth section rather than in a sensitivity table.

To run these, edit `Assumptions` in `model.py` and rerun. The pessimistic case
**reaches profitability in Y7 rather than Y5**, two years later than the base
case, and needs €827k rather than €409k. That is the
honest shape of the downside: survivable on a bridge, not free. The
robustness test that matters, and a stronger result than the old "later, at Y5
rather than Y4". Carrying VAT moved the base case back a year; it did not move
the conservative one, because that case is already thin enough in Y4 that the
VAT haircut changes nothing about when it crosses.

---

## What the model deliberately excludes

Named so nobody thinks they were forgotten:

| Excluded | Why |
|---|---|
| Managed matchmaking and market-intelligence revenue | Real, but later-stage; the plan should not depend on them |
| Reserved-instance / Savings Plan discounts | 25–40% on compute: upside, not plan |
| Processor renegotiation below 2.9% | Available at volume, treated as upside |
| Grant income (Neotec, ENISA) | Non-dilutive but uncertain; see [04](04-capital-and-valuation.md) |
| Working capital timing | Payout float is favourable (we hold fan money before paying athletes), a real cash benefit, unmodelled |
| FX | EUR-only until the UK or US entry |
| Cohort *quality* drift | Later cohorts may convert worse than early ones; not modelled |

Athlete and fan churn are now modelled explicitly. The remaining weakness is
that all cohorts are assumed to behave alike, in practice the athletes who join
in Y6 are unlikely to convert as well as the hand-picked ones in Y1.
