# 09 — Analytics Strategy

**Yes, phase it — and the phasing is not optional, because the data you need
does not exist yet.** Most of what an analytics team would want to know about
Stride can only be learned by operating Stride.

The one thing that *is* urgent costs no headcount at all.

---

## The rule

> **Capture early. Measure when there is something to measure. Explain before
> you predict. Hire last.**

The expensive mistake is not lacking analysts. It is failing to record an event
you cannot reconstruct later. Analysts hired before there is data build
dashboards nobody opens; instrumentation skipped in year one is unrecoverable
because the past does not come back.

---

## Four phases

| Phase | When | Data you have | Headcount | What it answers |
|---|---|---|---|---|
| **0 — Borrowed** | Now → pre-seed | Public datasets, your own schema | **0** | Which sports and countries look promising, and what content to advise |
| **1 — Observed** | Pre-seed → seed | Real engagement from connected platforms | **0** (engineering) | What actually converts, per sport and market |
| **2 — Outcome** | Seed → Series A | Deal outcomes, churn cohorts, campaign results | **1** analyst-engineer | Which matches convert, and what a match is really worth |
| **3 — Intelligence** | Series A+ | Everything above, at scale | **3–5** | Prediction, and data as a product |

### Phase 0 — Borrowed data (now)

Everything in [08](08-sport-index.md) is this phase: Eurobarometer for
participation, FIP for padel, reasoned estimates elsewhere, each carrying a
confidence flag. Cost: zero. Enough to rank 714 country × sport pairs and drive
the athlete content guidance.

**The only urgent work is instrumentation**, and the product is already unusually
well set up for it:

| Already built | Why it matters later |
|---|---|
| `score_snapshots` store inputs *and* coverage per computation | Every score is reproducible after the fact — you can re-derive history when the formula changes |
| Versioned `formula_version` on every snapshot | Cohorts stay comparable across scoring changes |
| `events` audit log with arbitrary object types | New event types need no migration |
| Consent recorded with policy version | The lawful basis for analysing behaviour is already documented |

**What to add now, while it is cheap:** an event for every fan subscribe, cancel,
unlock, tip and paywall view, with the athlete, sport, country and tier attached.
Those five events are the entire Phase-2 dataset, and adding them costs an
afternoon during P1. Adding them in Y3 means a year of blind cohorts.

### Phase 1 — Observed data (pre-seed → seed)

Once connectors are live, Stride measures what it currently estimates. The
fandom layer of the sport index — its weakest input — gets replaced by real
engagement per sport per country, drawn from the athletes already on the
platform.

**This is the phase where the index stops being a spreadsheet and starts being a
moat.** Anyone can copy the method in `sport_index.py`. Nobody can copy a
measured dataset of what athlete audiences actually do.

Still no analytics hire. This is instrumentation and queries, done by whoever
built the pipeline.

### Phase 2 — Outcome data (seed → Series A)

Now the interesting questions become answerable, because you have outcomes:

- Which matches converted into deals, at what price, against what score?
- Do the eight matching weights in `matching.py` predict conversion, or are they
  a plausible guess that happens to be stable?
- Which fan cohorts retain, by sport, tier, price and content type?
- Does the content guidance in [08](08-sport-index.md) actually raise conversion?

**First analytics hire, and it should be one person who both models and ships** —
an analyst-engineer, not a data scientist and not a BI contractor. The job is to
turn `matching.py`'s hand-set constants into learned weights and to build the
cohort reporting the board will ask for.

The matching engine was deliberately built as a transparent weighted sum. That
was the right call for launch and it stays the explainable baseline: any learned
model has to beat it, and if it cannot be decomposed for a sponsor it does not
ship.

### Phase 3 — Intelligence as product (Series A+)

Three to five people. Predicted campaign lift, dynamic pricing guidance for rate
cards, and **market intelligence sold to brands** — revenue stream 8 in
[01](01-revenue-model.md), deliberately excluded from the base model so the plan
never depended on it.

---

## The trap nobody warns you about

**Your platform data is not a sample of the market. It is a sample of who
joined.**

If padel athletes convert well on Stride, that may be because padel audiences
pay — or because the padel athletes who joined early were unusually good at
content, or because you recruited them personally and they tried harder.
Concluding "padel converts" from platform data alone is selection bias, and it
is the specific way this company would fool itself.

Three defences, none expensive:

| Defence | Cost |
|---|---|
| Record acquisition channel and recruiter on every athlete | One column |
| Hold out a small unmanaged cohort — onboarded, then left alone | Discipline only |
| Compare against public benchmarks before believing an internal number | An afternoon per claim |

This matters more than any modelling sophistication. A biased dataset analysed
brilliantly produces a confident wrong answer, which is worse than an honest
"we don't know yet."

---

## Build versus buy

| Data | Recommendation |
|---|---|
| Sport participation | **Public** — Eurobarometer, federation licences. Free, periodic, sufficient |
| Sports fandom / media panels | **Do not buy before Series A.** Nielsen/YouGov-class panels cost more than the whole Y1–Y2 analytics budget and are replaced by your own data in Phase 1 |
| Social platform metrics | **Already yours** via connectors — the reason the engine was built first |
| BI tooling | Postgres and a notebook until Phase 2. The warehouse can wait for the data to justify it |

---

## What this costs

| Phase | Headcount | Tooling | Annual |
|---|---|---|---|
| 0 | 0 | Existing stack | **€0** |
| 1 | 0 | Existing stack | **€0** |
| 2 | 1 analyst-engineer | Warehouse + BI | **~€75k loaded + €6k** |
| 3 | 3–5 | Warehouse, orchestration, experimentation | **~€260k + €25k** |

Phase 2 lands in Y4 and Phase 3 around Y6 on the plan's headcount curve, so this
is already inside the model's people line rather than an addition to it.

---

## The honest summary

**Analytics is not a phase-one investment for this company, but instrumentation
is.** The five events listed in Phase 0 are the whole difference between a
Phase-2 team that can answer questions and one that spends its first six months
backfilling.

And the reason to care beyond operations: the index in
[08](08-sport-index.md) is copyable as a method and not as a dataset.
**Every month of operating makes it less copyable** — which is the most durable
competitive argument in this plan, and it accrues automatically as long as the
events are being written.
