# 00 — Executive Summary

**Stride is a creator platform with a sponsorship feature.**

Athletes are creators with a second payer. OnlyFans proved that direct fan
monetisation beats ad-share; no one has built it for athletes — who, unlike
lifestyle creators, also have sponsors, clubs, and a competitive record that
makes their audience measurable. Fan revenue leads and funds the early years.
Sponsorship compounds behind it, and the analytics engine earns its keep by
making the second payer possible, which a general creator platform cannot do.

---

## The wedge: the athletes nobody serves

The segmentation that matters is not *which sport* but **whether an intermediary
already exists.**

|  | Popular sports | Niche sports |
|---|---|---|
| Does an agent exist? | Yes, for the top. The tail is ignored | **No** |
| The athlete's alternative | An agent taking 10–20%, if one will take them | **Nothing** |
| What we sell | Disintermediation — 10%, matched on evidence | Market creation — monetise at all |
| CAC | Higher: an incumbent relationship to beat | Lower: no incumbent |

We start where there is no incumbent. A trail runner with 25,000 followers has
an inbox of unanswered brand DMs and no idea what a fair rate is. Nobody is
fighting us for her, and what we learn there generalises upward. Football does
not generalise downward.

## Why now

**TEKTA launched on 19 August 2026** — Publicis Sports, 3 Arts, Travis Kelce.
A major agency has just validated that athlete monetisation is a category worth
building for.

It also built the thing this thesis exists to remove: a human-mediated
consultancy, gated to "a select group of Publicis Sports clients", 45,000
Division I athletes, US college NIL, **no fan monetisation at all.** They are
the incumbent in our disintermediation pitch, not a competitor in our
marketplace one. Their economics exclude precisely the athlete we start with.

## What exists today

A working product, not a prototype: connected platform analytics, versioned
marketability scoring, an admission gate, campaign matching with explainable
ranking, offers, deals, and delivery measurement — end to end, with an audit
log, a resilience drill, and a test suite that runs on two databases in CI.

**The demo shows the sponsorship engine.** Fan monetisation is the revenue
leader and the next build; what you can click today is the half that proves the
analytics are real. That ordering is deliberate — the matching engine is what
makes an athlete's audience legible to a sponsor, and the same measurement is
what will price a subscription.

Three things in it are worth two minutes of a technical diligence call:

- **Every match score decomposes.** A ranked athlete shows all eight components,
  each weighted, with the arithmetic visible — `audience fit 72 × 32% = 23.1`.
- **Missing data is `null`, never `0`.** An unmeasured campaign reads as
  unmeasured, not as free. A dimension we could not measure is excluded from the
  score rather than counted as zero.
- **Nothing self-verifies.** A club scoring above the verification bar still
  waits for a human to open its roster page. A rejected proof cannot be cleared
  by re-submitting the form.

## The shape of the plan

<!-- MODEL:summary -->
|  | Y3 | Y7 |
|---|---|---|
| Net revenue | €1.04M | €26.52M |
| EBITDA | €-274k | €9.99M |
| Active athletes | 5,500 | 52,000 |
| Paying fans | 46,333 | 759,408 |
| Gross margin | 69% | 73% |
<!-- /MODEL:summary -->

EBITDA turns positive in **Y4**. Take rates are published and fixed: **15% on
fan revenue, 10% on sponsorship**, no monthly athlete fee. Gross margin sits in
the low 70s rather than a SaaS 80%+ because the payment rail is real and no
amount of engineering removes it.

Every figure here is generated from the model, and a guard in the repository
fails the build if any of them drift from it.

## What this rests on

One assumption carries the plan: **niche-sport fans churn 45% slower than the
Patreon benchmark**, because training content is habitual and competitive
seasons create renewal moments. If that is wrong and we are merely at benchmark,
roughly €7M of Y10 revenue disappears.

Nothing in the product proves it today, and no amount of further engineering
will. Three months of real subscription data from one anchor athlete answers it
definitively — which is why that, and not a feature, is the pre-seed gate.

## The ask

**€400k pre-seed at €2.5M pre-money.**

The gate is evidence, not a milestone we can assert: 400 athletes, €10k MRR, an
anchor athlete public, payments processing real money, and **fan churn measured
for three months.** Use of funds: three hires, Spain go-to-market, the club
channel.

The plan needs €625k. The staged rounds raise €2.4M before Series A, and the
difference is deliberate — raising only what the model needs leaves no room for
the assumption that turns out wrong, and a company that runs out of cash in Y3
at the trough dies with a working product.

## What our decisions cost

Each of these was the right call, and each closed something off. We would rather
say so than be asked.

- **15% flat, no athlete fee** forfeits €4.6M of Y7 revenue against a 20% take.
  Bought: a pricing argument that survives contact with the exact athlete we
  target — we beat the nearest comparable for anyone under €1,380/month, which
  is the whole long tail.
- **18+ for fan subscriptions** forfeits the 16–17 cohort's fan revenue for a
  year or two. Bought: distance from the risk that has produced litigation
  against creator platforms. That cohort still builds the analytics pool and
  converts automatically at 18.
- **Niche sports first** forfeits early volume. Bought: a proof point that
  generalises upward, and no incumbent fighting back while the model is fragile.

---

*Full reasoning: [01](01-revenue-model.md) revenue and take rates ·
[03](03-financial-model.md) the seven-year model · [04](04-capital-and-valuation.md)
capital and valuation · [05](05-product-gaps.md) what the product still needs ·
[06](06-market-strategy.md) the two segments · [07](07-open-questions.md) what is
settled and what is not · [10](10-competitor-tekta.md) the competitive read.*
