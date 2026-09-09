# 13 — Organization and Human Resources Plan

*ESADE outline §8. Headcount, loaded costs and the hiring sequence are generated
by [`model.py`](model.py); the doc guard fails the build if the prose drifts
from it.*

The plan reaches **€10.7M of revenue at Y7 with 22 people.** That ratio is the
central organisational claim, and it is only credible if the org design explains
*why* it holds. It holds because the only human step in the value chain is
admission review (see [12](12-operations-plan.md)), and admission review scales
with applications rather than with transactions.

This section sets out the structure, the roles, the policies that fill them, and
who decides what.

---

## 13.1 Organizational structure

### Headcount trajectory

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Headcount (FTE) | 1.5 | 2.0 | 3.5 | 6.0 | 10.0 | 15.0 | 22.0 |
| People cost | €57k | €104k | €210k | €384k | €660k | €1.02M | €1.54M |

Growth to 38 FTE by Y10. The shape is deliberate: **the team stays below five
people until fan revenue is proven**, because the pre-seed gate tests an
assumption, and testing an assumption does not need an organisation.

### Functional structure by stage

```
  Y1–Y2  ── FOUNDER / CEO ──┬── Full-stack engineer
  (2 FTE)                   └── Community / athlete lead

  Y3–Y5  ── FOUNDER / CEO ──┬── ENGINEERING ── senior eng · full-stack
  (3.5→10)                  ├── GROWTH ────── BD/partnerships · athlete success
                            ├── OPERATIONS ── moderation lead · review
                            └── FINANCE & COMPLIANCE ── finance/ops · DPO (frac.)

  Y6+    ── FOUNDER / CEO ──┬── VP ENGINEERING ── platform · data · mobile
  (15→38)                   ├── VP GROWTH ────── sales · partnerships · marketing
                            ├── HEAD OF OPS ──── trust & safety · support · review
                            └── HEAD OF FINANCE ─ finance · legal · DPO (hired)
```

**Three functions, not five.** Engineering, Growth and Operations carry the
business; Finance & Compliance is fractional until Y4 and a function only from
Y5. There is no separate marketing team before Y6 — acquisition runs through the
Growth function, because at this stage marketing *is* partnerships.

> [!note] Why the org chart is flat for longer than is comfortable
> The temptation in a marketplace is to hire sales ahead of supply. We
> deliberately do not: until the admission gate is producing athletes a sponsor
> actually wants, a salesperson has nothing differentiated to sell. Supply first,
> demand second, and the hiring sequence encodes that.

---

## 13.2 Job descriptions

Roles are listed in hiring order. Gross and loaded costs reflect Spanish
employer social security at **~30–32%** on top of gross.

### Founder / CEO — Y1
**Gross €0 → €45k · Loaded €0 → €59k**
Unpaid in Y1; the opportunity cost is modelled explicitly rather than hidden.
Owns strategy, fundraising, the anchor-athlete relationship and the sponsor
pipeline until a BD hire exists. Writes code in Y1–Y2.
*Requires:* the venture's core insight, and enough technical depth to ship.

### Senior engineer — Y2
**Gross €55k · Loaded €72k**
Owns the platform end to end: API, data model, the analytics engine, deployment.
Second pair of hands on a codebase that already exists and already has a test
suite running on two databases.
*Requires:* Python/TypeScript, Postgres, cloud deployment. Payments integration
experience is the single most valuable specialism at this stage.

### BD / partnerships — Y2
**Gross €38k + commission · Loaded €50k+**
Opens the club channel and the first sponsor accounts. Commission-weighted
because the role is measurable and the early pipeline is the company's riskiest
unknown after fan churn.
*Requires:* Spanish sports ecosystem relationships. Federation or club-side
experience preferred over agency experience.

### Athlete success — Y3
**Gross €30k · Loaded €39k**
Onboards admitted athletes, coaches content strategy, holds retention. The
counterpart to BD on the supply side, and the role closest to the churn
assumption the whole plan rests on.
*Requires:* credibility with athletes. Competitive background strongly preferred.

### Content moderation lead — Y3
**Gross €34k · Loaded €45k**
Owns the review queue, the trust and safety policy, the age-gate enforcement and
the escalation path. Also owns the admission-review service level (< 48 hours).
*Requires:* trust and safety experience on a UGC platform; judgement under
ambiguity.

### Finance / operations — Y4
**Gross €42k · Loaded €55k**
Payouts, reconciliation, VAT across markets, investor reporting, the working
capital cycle. The first hire whose absence would become a control weakness
rather than a workload problem.
*Requires:* multi-jurisdiction VAT, marketplace payment flows.

### Data protection officer — Y3 fractional → Y5 hired
**Fractional €18k → Hired gross €60k / loaded €79k**
GDPR Article 37 exposure arrives with scale, not with launch. Fractional until
the athlete base and the media pipeline justify a full-time appointment.
*Requires:* GDPR practice, ideally with platform or minors experience given the
16–18 age model.

---

## 13.3 HR policies

### Selection

**Hire for the constraint, not for the org chart.** Every role above exists
because a specific bottleneck arrives at a specific time; none is a
"nice-to-have at this stage" hire.

- **Structured, evidence-based process.** A work sample for every technical
  role: a real pull request against a scoped issue, paid at market rate.
  Consistent with a product whose own admission gate refuses to accept
  self-verification.
- **Two-stage reference check** for the athlete-facing roles, because those
  relationships are the asset.
- **Non-discrimination.** Selection criteria are written before candidates are
  seen and applied identically. This is both a legal requirement in Spain and a
  stated commitment (§13.5).

### Management

- **Remote-first, asynchronous by default.** The company is distributed from Y1
  and hires from a wider pool than Barcelona from Y4.
- **Quarterly objectives tied to the gates**, not to the calendar. The pre-seed,
  seed and Series A gates in [04](04-capital-and-valuation.md) are evidence
  thresholds; team objectives are the components of those thresholds.
- **One-to-ones fortnightly, written.** Small teams lose context faster than
  they lose alignment.

### Compensation

| Element | Policy |
|---|---|
| **Base** | Benchmarked to Barcelona market, at or slightly below median, with equity making up the difference |
| **Employer cost** | Spanish social security at ~30–32%; every figure in the plan is loaded, not gross |
| **Equity** | ESOP topped to **10%** by the Series A. All employees participate; four-year vesting, one-year cliff |
| **Commission** | BD only, and only on closed sponsorship revenue |
| **Relocation** | Beckham Law (24% flat IRPF) actively used for senior hires from Y4 |
| **Founder salary** | €0 in Y1, rising to €45k. Deliberately below market; the return is equity, and the opportunity cost is disclosed in [04](04-capital-and-valuation.md) |

> [!note] Why below-median base with real equity
> The plan's whole argument is that a small team can reach €10.7M of revenue.
> If that is true, equity is worth more than the salary gap — and if a candidate
> does not believe it, they are the wrong hire for a company whose central
> claim is exactly that.

---

## 13.4 Governance structure

### Legal form
**Sociedad Limitada (S.L.)**, incorporated in Spain. Rationale and the
alternatives considered are in [14](14-legal-and-growth.md).

### Board composition by stage

| Stage | Board | Founder control |
|---|---|---|
| Pre-incorporation | Founder only | 100% |
| **Pre-seed** (€600k) | Founder + 1 investor observer | 79% held after the 2% advisory grant |
| **Seed** (€2.0M, optional) | Founder + 1 investor director + 1 independent | 66% |
| **Series A** (€8.0M) | Founder + 2 investor directors + 1 independent | 55% |
| Post-ESOP | As above | **~49%** |

### Reserved matters
From the pre-seed onward, the following require investor consent: new share
issuance, sale of the company, changes to the take rate, incurring debt above a
threshold, and any change to the athlete age policy. **The last one is on the
list deliberately** — it is the decision most likely to be pressured commercially
and least reversible reputationally.

### Advisory
An **advisory grant of 1%** is made at the pre-seed, vesting over two years, in
line with the 0.5–1.5% range and performance trigger recommended in
[04](04-capital-and-valuation.md). The dilution table above models the 2%
ceiling, so the cap table is stated at the conservative end of that range. The
intended profile is sports-industry rather than technology: the plan's weakest
external dependency is the anchor athlete and the club channel, not the code.

---

## 13.5 Sustainability and responsible business

*Addressing the programme learning objective on the UN Sustainable Development
Goals. These are not decorative — each maps to a decision already taken in the
plan and visible in the product.*

| SDG | How the business model addresses it | Where it is decided |
|---|---|---|
| **8 — Decent Work and Economic Growth** | The core purpose: creating an income stream for semi-professional athletes who currently have none. A trail runner's alternative to Stride is nothing | [06](06-market-strategy.md) |
| **5 — Gender Equality** | Women's sport is systematically under-monetised by agent-mediated models, precisely because agents chase the largest audiences. An evidence-based matching engine that scores on engagement rather than on name recognition is structurally fairer to it | [11](11-admission-and-matching.md) |
| **10 — Reduced Inequalities** | The 15% flat take with **no monthly athlete fee** means the athlete earning €200 a month pays the same rate as the one earning €5,000. A subscription fee would have been regressive | [01](01-revenue-model.md) |
| **16 — Peace, Justice and Strong Institutions** | Nothing self-verifies. A club above the verification bar still waits for a human; a rejected proof cannot be cleared by re-submitting. Consent is versioned and audited | [11](11-admission-and-matching.md) |
| **12 — Responsible Consumption** | The zero-egress architecture is chosen on cost, and the same decision cuts billed cross-network transfer by an order of magnitude. We do **not** claim a measured energy saving: the 9.4× in [02](02-cost-model.md) is a price ratio, and no energy measurement sits behind it | [02](02-cost-model.md) |

**Two commitments that cost us money**, stated because they are the test of
whether the above is real:

1. **18+ for fan subscriptions.** This forfeits the 16–17 cohort's fan revenue
   for a year or two. Adults paying for private access to a minor is a
   categorically different risk from a sponsor paying for a post, and we treat
   it that way.
2. **15% flat, no athlete fee.** This forfeits **€1.6M of Y7 revenue** against a
   20% take. It buys a pricing argument that survives contact with the exact
   athlete we target.

Each of these is a decision we would rather explain than have found.
