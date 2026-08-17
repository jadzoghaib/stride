# Stride — Business Plan

A seven-year operating plan for a Spanish company.

> **Stride is a creator platform with a sponsorship feature.**
>
> Athletes are creators with a second payer. OnlyFans proved that direct fan
> monetisation beats ad-share. No one has built it for athletes — who, unlike
> lifestyle creators, also have sponsors, clubs, and a competitive record that
> makes their audience measurable.

That sentence is a decision, not a description, and it settles the sequencing of
everything else: fan revenue leads, sponsorship compounds behind it, and the
analytics engine earns its keep by making the second payer possible — which is
precisely the thing a general creator platform cannot do.

**The market position is disintermediation on one side and market creation on
the other.** In popular sports, agents take 10–20% of an endorsement to make
introductions; Stride takes 10% and matches on evidence. In niche sports there
are no agents at all, and the athlete's alternative to Stride is nothing. See
[06](06-market-strategy.md).

---

## Read in this order

| # | Document | What it settles |
|---|---|---|
| 01 | [Revenue model](01-revenue-model.md) | The eight streams, the OnlyFans comparison, take rates, tier design |
| 02 | [Cost model](02-cost-model.md) | AWS build-up, people, compliance, and the two costs that decide viability |
| 03 | [Financial model](03-financial-model.md) | Seven-year P&L, drivers, scenarios |
| 04 | [Capital & valuation](04-capital-and-valuation.md) | Internal capital on an opportunity-cost basis, raise gates, Spanish instruments, DCF and exit multiples |
| 05 | [Product gaps](05-product-gaps.md) | What the app must gain before a euro can move — assessed against the actual codebase, including the age model |
| 06 | [Market strategy](06-market-strategy.md) | Two segments: disintermediation in popular sports, market creation in niche sports |
| 07 | [Open questions](07-open-questions.md) | What is settled, and what still needs a founder |

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
| Niche share of revenue | 95% | 80% | 54% | 38% |
| Paying fans | 2,201 | 47,740 | 295,140 | 759,408 |
| Marketplace GMV | €311k | €8.18M | €65.78M | €199.67M |
| **Net revenue** | **€51k** | **€1.32M** | **€9.78M** | **€28.62M** |
| Gross margin | 58% | 63% | 64% | 66% |
| EBITDA | −€79k | −€168k | €2.02M | €9.71M |
| Headcount | 1.5 | 7 | 24 | 50 |

**Capital required to fund it: €558k**, against a deepest cumulative cash
position of −€399k in Y3. EBITDA turns positive in Y4.

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
CloudFront, egress alone costs **€1.1M more in Y7** than the same bytes behind
a zero-egress CDN. This is an architecture decision with a seven-figure price
tag.

**3. The age model is tiered, not a single number.** 16 is the floor for an
account, and that choice is forward-compatible: Spain's draft Organic Law on
the Protection of Minors in Digital Environments would raise the digital
consent age from 14 to **16** and make age verification mandatory. But three
things do not follow from it — Stripe's Express/Custom Connect requires **18**
for payouts, a minor's image cannot be commercially exploited without guardian
consent, and adults paying for private access to a 16-year-old is a
categorically different risk from a sponsor paying for a post. See
[05](05-product-gaps.md#the-age-model).

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
