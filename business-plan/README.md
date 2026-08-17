# Stride — Business Plan

A seven-year operating plan for a Spanish company, built around one thesis:

> **Athletes are creators with a second payer.** OnlyFans proved that direct
> fan monetisation beats ad-share for creators. No one has built it for
> athletes — who, unlike lifestyle creators, also have sponsors, clubs and a
> competitive record that makes their audience measurable.

Stride monetises both sides: fans subscribe, sponsors buy access to a measured
athlete pool. The analytics that already exist in the product are the asset
that makes the sponsor side defensible.

---

## Read in this order

| # | Document | What it settles |
|---|---|---|
| 01 | [Revenue model](01-revenue-model.md) | The eight streams, the OnlyFans comparison, take rates, tier design |
| 02 | [Cost model](02-cost-model.md) | AWS build-up, people, compliance, and the two costs that decide viability |
| 03 | [Financial model](03-financial-model.md) | Seven-year P&L, drivers, scenarios |
| 04 | [Capital & valuation](04-capital-and-valuation.md) | Internal capital on an opportunity-cost basis, raise gates, Spanish instruments, DCF and exit multiples |
| 05 | [Product gaps](05-product-gaps.md) | What the app must gain before a euro can move — assessed against the actual codebase |
| 06 | [Open questions](06-open-questions.md) | The decisions I cannot make for you |

Every number in 03 and 04 is produced by [`model.py`](model.py). Change an
assumption there and rerun — nothing is hand-typed:

```bash
python business-plan/model.py
```

---

## The plan in one table

| | Y1 | Y3 | Y5 | Y7 |
|---|---|---|---|---|
| Active athletes | 400 | 5,500 | 25,000 | 52,000 |
| Paying fans | 1,584 | 37,950 | 259,000 | 665,600 |
| Marketplace GMV | €239k | €6.82M | €54.20M | €153.13M |
| **Net revenue** | **€39k** | **€1.11M** | **€8.33M** | **€23.31M** |
| Gross margin | 58% | 64% | 65% | 66% |
| EBITDA | −€87k | −€280k | €1.35M | €6.94M |
| Headcount | 1.5 | 7 | 24 | 50 |

**Capital required to fund it: €777k**, against a deepest cumulative cash
position of −€555k in Y3. EBITDA turns positive in Y4.

---

## The four things that decide whether this works

**1. The fixed payment fee, not the take rate.** At a €4.99 tier we keep 47% of
our own commission because Stripe's €0.25 lands on a €0.75 take. At €9.99 we
keep 64%. This single mechanic should set the minimum tier price and push hard
toward annual billing — it moves more margin than any plausible take-rate
change. See [02](02-cost-model.md#the-fixed-fee-problem).

**2. Media egress, not compute.** The current product is deterministic
analytics: compute is a rounding error, which `docs/costs.md` correctly says.
The moment fans pay for video, that stops being true. Served naively from
CloudFront, egress alone costs **€963k more in Y7** than the same bytes behind
a zero-egress CDN. This is an architecture decision with a seven-figure price
tag.

**3. Minors.** Athletes are frequently under 18 and the product already models a
13–17 audience band. Paid fan content plus minors is the combination that ends
platforms — through card-scheme rules, not just regulators. This is a launch
blocker, not a backlog item. See [05](05-product-gaps.md).

**4. Nothing can be paid for today.** The product has no payment, subscription,
tier, payout or wallet entity of any kind, and a fan's only available action is
to follow. The entire revenue model in this plan is unbuilt. That is not a
criticism of the product — it was built as an analytics-led marketplace and it
is good at that — but the gap between what exists and what this plan monetises
is the honest starting point.

---

## What already exists and counts as an asset

| Asset | State | Why it matters commercially |
|---|---|---|
| Marketability analytics | Built, tested | The sponsor-side moat; nobody else scores the long tail |
| Explainable matching | Built, tested | Sponsors buy against evidence, which shortens sales cycles |
| Campaign → offer → deal flow | Built (records, no money) | The take-rate rail is half-built already |
| Club packages & rosters | Built | A B2B2C channel most creator platforms lack |
| Consent + audit trail | Built | Regulatory posture ahead of most seed-stage platforms |
| Aggregate-only audience data | Built by schema design | Removes an entire class of privacy risk |

---

*Currency is EUR throughout. Y1 = 2027. Assumptions are stated where they are
used, and are arguable by design — the point of the model is that you can move
them.*
