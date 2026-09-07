# 04 — Capital & Valuation

---

## Internal capital, priced honestly

You asked for the starting cash to be treated on an opportunity-cost basis. It
should be, and the answer is larger than the cash figure — because the scarce
input is not the money.

### What is actually committed

| Input | Amount | Opportunity cost basis | Annual cost |
|---|---|---|---|
| Founder cash | €80,000 | Alternative return 7% (diversified equity; Spanish 10Y is 3.2%, ECB deposit ~2%) | €5,600 |
| Founder time, Y1 | Unpaid | Forgone salary for this skill set in Barcelona/Madrid | €50,000 |
| Founder time, Y2 | €45k salary vs €70k market | Forgone differential | €25,000 |
| Co-founder / CTO time, Y1–Y2 | Equity only | Forgone salary, 50% weight | €35,000 |

| Cumulative economic commitment | Amount |
|---|---|
| Cash at risk | €80,000 |
| Forgone earnings, Y1–Y2 | €110,000 |
| Opportunity cost on cash, Y1–Y2 | €11,600 |
| **Total before any external euro** | **€201,600** |

**The founder's time is 55% of the real investment.** A plan that treats
founder labour as free understates the capital committed by more than double,
and it produces a hurdle rate that is far too low.

### The hurdle this sets

To beat the alternative — take the job, invest the €80k — the venture must
return more than €201,600 compounded at 7%, plus a premium for the risk of total
loss. At a 70% failure probability, the surviving case must return roughly
**€1.5–2M to the founder** for the decision to have been rational ex ante.

The model delivers that: a founder retaining ~49% through the Series A holds
that share of the enterprise value — **€4.11M against the DCF floor of €8.36M**,
and €5.4–12.1M against the exit multiples discounted back. **Even the floor
clears the hurdle twice over**, which is the honest justification for doing it
at all.

---

## Funding stages, gated on evidence

You were right to want raises gated on something concrete. Each gate below is a
fact you can demonstrate, not a milestone you can assert.

| Stage | Amount | Pre-money | Gate — what must be true before raising | Use of funds |
|---|---|---|---|---|
| **Internal** | €80k cash + time | — | Product exists (it does) | Payments, subscriptions, one anchor athlete live |
| **Pre-seed** | **€600k** | €2.5M | 400 athletes · €10k MRR · anchor athlete public · payments processing real money · fan churn measured for 3 months | 2 hires, Spain go-to-market, club channel |
| **Seed** *(optional)* | €2.0M | €10M | €80k MRR · fan churn < 8%/mo · CAC payback < 9mo · 2nd market opened · 30+ paying sponsors | Team to 15, second and third market, moderation infrastructure |
| **Series A** | €8.0M | €40M | €300k MRR · net revenue retention > 110% · sponsorship take > 25% of revenue · unit economics stable across 3 markets | EU-wide, sales org, managed services |

**The plan needs €655k. The rounds above raise €2.6M before Series A.** The
difference is deliberate: raising only what the model needs leaves no room for
the assumption that turns out wrong, and a company that runs out of cash at the
trough dies with a working product. Raise the buffer; do not spend it unless
the conservative case materialises.

The pre-seed alone covers the **€468k trough in Y4** with €132k to spare, which
is why the seed is marked optional above. It is growth capital — a second market
sooner — not rescue capital. A plan whose survival does not depend on the next
round arriving on schedule is a materially stronger one to raise against.

### Why the pre-seed gate is the one that matters

Every gate after it is a scaling question. The pre-seed gate is the **only** one
that tests the thesis: *will fans of a semi-professional athlete actually pay?*

Nothing in the product proves that today. Three months of real subscription data
from one anchor athlete answers it definitively — and if the answer is no, you
have spent €80k and a year, not €2.6M and four.

**That is the single most important sequencing decision in this plan.**

---

## Spanish instruments — non-dilutive capital first

Spain has unusually good public financing for early-stage technology companies.
Taking dilution before exhausting these is leaving money on the table.

| Instrument | Amount | Cost | Fit |
|---|---|---|---|
| **ENISA Jóvenes Emprendedores** | €25k–€75k | Participative loan, ~Euribor + spread, **no equity** | Y1 — designed exactly for this |
| **ENISA Crecimiento** | up to €300k | Participative loan, no equity | Y2–Y3 |
| **CDTI Neotec** | up to €250k (70% of budget) | **Grant**, no equity | Y2 — requires R&D framing; the analytics engine qualifies |
| **Startup Capital (regional, Catalunya)** | €25k–€100k | Grant / soft loan | Y1–Y2 |
| **Ley de Startups** tax regime | — | **15% corporate tax** for the first four taxable years vs 25% | Modelled — worth €1.56M across Y6–Y9 |
| Beckham Law | — | 24% flat IRPF for relocated hires | Recruiting senior talent from abroad |

**A realistic non-dilutive stack is €300–500k**, which covers most of the €468k
trough on its own. Combined with a smaller pre-seed, the founder could reach the
Seed gate holding materially more equity.

The 15% startup tax rate is already in the model. The others are excluded —
they are upside, and grant timelines are unreliable enough that no plan should
depend on them.

---

## Valuation

Two methods, because they answer different questions and disagree for a reason.

### Discounted cash flow

<!-- MODEL:valuation -->
| Valuation (DCF) | Value |
|---|---|
| PV of explicit FCF, Y1–Y10 | €3.90M |
| Terminal value (g=3%) | €41.50M |
| PV of terminal value | €4.46M |
| **Enterprise value (WACC 25%)** | **€8.36M** |
<!-- /MODEL:valuation -->

### Exit multiple


<!-- MODEL:multiples -->
| Exit method (Y10) | Multiple | Value at Y10 | Discounted to today |
|---|---|---|---|
| Marketplace comparables | 4.0x revenue | €101.53M | €10.90M |
| Blended marketplace + SaaS | 6.5x revenue | €164.99M | €17.72M |
| High-growth SaaS mix | 9.0x revenue | €228.45M | €24.53M |
| EBITDA multiple | 14x EBITDA | €151.03M | €16.22M |
<!-- /MODEL:multiples -->

### Why they disagree, and which to believe

The DCF says €8.4M; the blended exit multiple says €165.0M. **This is not an
error in either — it is the standard failure of perpetuity-growth DCF applied to
a company that has not finished growing.**

The DCF's terminal value assumes growth collapses to 3% the day after Y10, from
a year that still grew 27%. For a marketplace that has just reached €25M revenue
at a 71% gross margin with a network effect, that is not a neutral assumption —
it is a pessimistic one. The terminal value is 53% of the DCF's total, so that
single assumption carries half the answer.

**For a venture-stage company, the exit-multiple method discounted back is the
more informative number.** The DCF is worth presenting precisely because it is
the conservative floor: *even if growth stops dead after Y10*, the business is
worth €8.4M today.

<!-- MODEL:sensitivity -->
| Enterprise value | WACC 20% | WACC 25% | WACC 30% |
|---|---|---|---|
| Terminal growth 2% | €13.65M | €8.13M | €5.13M |
| Terminal growth 3% | €14.22M | **€8.36M** | €5.24M |
| Terminal growth 4% | €14.85M | €8.62M | €5.36M |
<!-- /MODEL:sensitivity -->

**Defensible headline: €11–25M enterprise value, the Y10 exit multiples
discounted to today at the same 25% WACC**, with an €8.4M floor under a
no-growth-after-Y10 assumption.

---

## The anchor athlete

You want to start with one partner and one key athlete. That partnership is the
pre-seed gate, so its structure matters more than its cost.

| Structure | What they get | What you get | Verdict |
|---|---|---|---|
| Ambassador fee | €15–30k/yr cash | Name, no alignment | ✗ Burns scarce cash on the least aligned option |
| Revenue share on their vertical | 2–5% of their sport's GMV | Aligned, but complicates the cap table of every future deal | ◐ Workable, messy at scale |
| **Advisory equity** | **0.5–1.5%, 2-year vest, 6-month cliff** | **Aligned to exit, costs no cash** | **✓ Recommended** |
| Co-founder equity | 5–15% | Total alignment | ✗ Only if they are genuinely operational |

**Recommended: 1% advisory equity, two-year vest, six-month cliff, with a
performance trigger** — an extra 0.5% if they bring three clubs or 25 athletes.
The cliff protects you if they lose interest after the launch photos.

### What the anchor athlete must actually be

Not the most famous available. The right profile:

| Criterion | Why |
|---|---|
| 20k–150k engaged followers | Large enough to prove conversion, small enough that the result generalises to the long tail |
| Semi-professional or nationally competitive | The segment you are actually serving; a global star proves nothing about your market |
| A sport with a defined season | Recurring content and natural subscription renewal moments |
| Attached to a club | Brings the second-order channel with them |
| Over 18 | Removes the safeguarding blocker from the launch path entirely |

That last row is a hard filter, not a preference. See
[05](05-product-gaps.md#minors).

---

## Dilution path

| Round | Raised | Pre-money | Post-money | New investor % | Founder(s) after |
|---|---|---|---|---|---|
| Internal | — | — | — | — | 100% |
| Pre-seed | €600k | €2.5M | €3.1M | 19.4% | 79% (after 2% advisory) |
| Seed *(optional)* | €2.0M | €10M | €12M | 16.7% | 66% |
| Series A | €8.0M | €40M | €48M | 16.7% | 55% |
| ESOP (cumulative) | — | — | — | 10% | **~49%** |

Retaining ~49% through Series A is a good outcome, and it depends on the
non-dilutive stack being used before equity rather than after it.

> [!note] This table used to be typed by hand, and did not add up
> The previous version raised €400k and still ended at ~45%, because each row
> was written independently rather than carried forward from the one above it.
> Every cell here is now generated by `model.dilution()` and pinned by the doc
> guard: the pre-seed grew by €200k and retention went **up**, because the
> arithmetic was wrong before, not because the round got cheaper.
