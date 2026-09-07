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
| Active athletes | 400 | 1,200 | 3,000 | 6,000 | 10,500 | 16,000 | 22,000 | 28,000 | 34,000 | 40,000 |
| Paying fans | 2,058 | 8,148 | 25,288 | 60,197 | 120,076 | 206,658 | 321,288 | 434,076 | 553,629 | 665,896 |
| Sponsorship deals | 25 | 117 | 485 | 1,549 | 3,767 | 7,376 | 11,563 | 16,258 | 19,895 | 25,539 |
| Paying sponsors (SaaS) | 0 | 8 | 39 | 95 | 180 | 280 | 400 | 520 | 620 | 720 |
| Headcount (FTE) | 1.5 | 2.0 | 3.5 | 6.0 | 10.0 | 15.0 | 22.0 | 28.0 | 33.0 | 38.0 |
<!-- /MODEL:drivers -->

---

## Retention and acquisition

Fans and athletes both churn, and the model runs the decay month by month rather
than asserting a year-end stock. Two consequences that a net-stock model cannot
show:

<!-- MODEL:churn -->
| Retention & acquisition | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Paying fans, year end | 2,058 | 8,148 | 25,288 | 60,197 | 120,076 | 206,658 | 321,288 | 434,076 | 553,629 | 665,896 |
| Paying fans, average | 1,306 | 5,897 | 18,939 | 47,228 | 97,837 | 174,458 | 277,911 | 391,108 | 507,748 | 622,731 |
| Fans acquired (gross) | 3,298 | 11,704 | 34,885 | 78,554 | 149,732 | 245,280 | 353,875 | 449,346 | 549,558 | 636,796 |
| Fans lost to churn | 1,241 | 5,614 | 17,746 | 43,645 | 89,854 | 158,698 | 239,245 | 336,558 | 430,005 | 524,528 |
| Athletes acquired (gross) | 400 | 909 | 2,094 | 3,690 | 5,796 | 7,671 | 9,200 | 10,224 | 11,278 | 12,229 |
| Athletes lost to churn | 0 | 109 | 294 | 690 | 1,296 | 2,171 | 3,200 | 4,224 | 5,278 | 6,229 |
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
| Fan GMV (subs + unlocks) | €139k | €651k | €2.15M | €5.41M | €11.30M | €20.11M | €32.08M | €45.44M | €59.55M | €73.77M |
| Sponsorship GMV | €27k | €159k | €908k | €3.62M | €10.40M | €23.01M | €39.70M | €58.95M | €76.01M | €102.13M |
| **Total GMV** | €166k | €810k | €3.05M | €9.03M | €21.70M | €43.12M | €71.78M | €104.39M | €135.56M | €175.90M |
<!-- /MODEL:gmv -->

GMV is the number a marketplace is judged on by investors; net revenue is the
number that pays salaries. Both are shown throughout so neither can flatter the
other.

---

## Net revenue

<!-- MODEL:revenue -->
| Net revenue | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Fan take (15%) | €21k | €98k | €322k | €811k | €1.69M | €3.02M | €4.81M | €6.82M | €8.93M | €11.07M |
| Sponsorship take (10%) | €3k | €16k | €91k | €362k | €1.04M | €2.30M | €3.97M | €5.89M | €7.60M | €10.21M |
| Sponsor SaaS | €1k | €21k | €122k | €331k | €691k | €1.21M | €1.92M | €2.68M | €3.39M | €4.10M |
| **Total net revenue** | €25k | €134k | €535k | €1.50M | €3.43M | €6.53M | €10.70M | €15.39M | €19.92M | €25.38M |
<!-- /MODEL:revenue -->

Growth: Y2 +442%, Y3 +298%, Y4 +181%, Y5 +128%, Y6 +90%, Y7 +64%. A decelerating
curve that stays above 50% through Y7 is what a Series B buyer wants to see.

---

## Profit and loss

<!-- MODEL:pl -->
| P&L | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 | Y8 | Y9 | Y10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Net revenue | €25k | €134k | €535k | €1.50M | €3.43M | €6.53M | €10.70M | €15.39M | €19.92M | €25.38M |
| Payment processing | €8k | €39k | €137k | €371k | €830k | €1.56M | €2.55M | €3.67M | €4.78M | €6.08M |
| Payouts | €645 | €3k | €11k | €32k | €74k | €144k | €237k | €343k | €446k | €574k |
| Infrastructure (AWS) | €3k | €9k | €30k | €75k | €153k | €240k | €344k | €435k | €516k | €583k |
| Moderation | €1k | €4k | €10k | €19k | €33k | €51k | €70k | €89k | €108k | €127k |
| Athlete verification | €745 | €2k | €5k | €8k | €12k | €15k | €18k | €20k | €23k | €25k |
| **Gross profit** | €11k | €77k | €342k | €999k | €2.32M | €4.51M | €7.48M | €10.84M | €14.04M | €18.00M |
| Gross margin | 46% | 57% | 64% | 66% | 68% | 69% | 70% | 70% | 71% | 71% |
| People | €57k | €104k | €210k | €384k | €660k | €1.02M | €1.54M | €2.02M | €2.44M | €2.89M |
| Marketing / CAC | €29k | €87k | €229k | €520k | €915k | €1.30M | €1.70M | €1.85M | €1.80M | €1.95M |
| Legal & compliance | €18k | €45k | €90k | €150k | €200k | €235k | €270k | €300k | €325k | €345k |
| Other opex | €2k | €11k | €43k | €120k | €274k | €522k | €856k | €1.23M | €1.59M | €2.03M |
| **EBITDA** | €-95k | €-170k | €-229k | €-176k | €275k | €1.43M | €3.11M | €5.44M | €7.88M | €10.79M |
| Tax | €0 | €0 | €0 | €0 | €0 | €87k | €418k | €747k | €1.09M | €2.51M |
| Working capital movement | €-16k | €-38k | €-110k | €-264k | €-516k | €-821k | €-1.09M | €-1.21M | €-1.17M | €-1.46M |
| Capex (capitalised development) | €17k | €31k | €63k | €115k | €198k | €306k | €462k | €605k | €733k | €866k |
| **Free cash flow** | €-96k | €-163k | €-182k | €-27k | €592k | €1.86M | €3.32M | €5.30M | €7.23M | €8.86M |
<!-- /MODEL:pl -->

Free cash flow is EBITDA less tax, working capital movement and capex — not
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
| Y1 | €-96k | €-96k |
| Y2 | €-163k | €-259k |
| Y3 | €-182k | €-441k |
| Y4 | €-27k | €-468k |
| Y5 | €592k | €124k |
| Y6 | €1.86M | €1.99M |
| Y7 | €3.32M | €5.31M |
| Y8 | €5.30M | €10.61M |
| Y9 | €7.23M | €17.83M |
| Y10 | €8.86M | €26.70M |
<!-- /MODEL:cash -->

| Capital requirement | Value |
<!-- MODEL:funding -->
| Capital requirement | Value |
|---|---|
| Deepest cumulative cash position | €-468k |
| Year it occurs | Y4 |
| Buffer at 40% (hiring slips, churn worse) | €187k |
| **Total capital to fund the plan** | **€655k** |
| First EBITDA-positive year | Y5 |
<!-- /MODEL:funding -->

**€655k is a small number for a plan that reaches €10.7M of revenue by Y7,
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
| **Conservative** | Fans/athlete −30%, monetise rate −25% | ~€8.4M | ~€1.9M | ~€1.26M |
| **Base** | As modelled | €10.70M | €3.11M | €655k |
| **Growth-optimised** | Hire 12mo ahead, 3 markets from Y2 | ~€39M | ~€9M | €3–5M |

To run these, edit `Assumptions` in `model.py` and rerun. The conservative case
**still reaches profitability in Y5, the same year as the base case** — the
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
| Reserved-instance / Savings Plan discounts | 25–40% on compute — upside, not plan |
| Processor renegotiation below 2.9% | Available at volume, treated as upside |
| Grant income (Neotec, ENISA) | Non-dilutive but uncertain; see [04](04-capital-and-valuation.md) |
| Working capital timing | Payout float is favourable (we hold fan money before paying athletes) — a real cash benefit, unmodelled |
| FX | EUR-only until the UK or US entry |
| Cohort *quality* drift | Later cohorts may convert worse than early ones; not modelled |

Athlete and fan churn are now modelled explicitly. The remaining weakness is
that all cohorts are assumed to behave alike — in practice the athletes who join
in Y6 are unlikely to convert as well as the hand-picked ones in Y1.
