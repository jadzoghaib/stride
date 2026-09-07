# 02 — Cost Model

Two costs decide whether this business works. Neither is engineering salary.

---

## The fixed-fee problem

Stripe charges a Spanish entity **1.5% + €0.25** on EEA cards, 2.5% on UK cards and 3.25%
on non-EEA — blended to **1.9% + €0.25** here. On small subscriptions the fixed component is
most of the cost, and it lands on our commission, not on the athlete's share.

<!-- MODEL:unit_economics -->
| Fan pays (monthly) | Our take (15%) | Payment cost | We keep | % of take retained |
|---|---|---|---|---|
| €4.99 | €0.62 | €0.34 | €0.27 | 44% |
| €9.99 | €1.24 | €0.44 | €0.80 | 64% |
| €24.99 | €3.10 | €0.72 | €2.37 | 77% |
| €89.00 (annual) | €11.03 | €1.94 | €9.09 | 82% |
<!-- /MODEL:unit_economics -->

**Read that first row again.** At a €4.99 tier, nearly half our commission goes to the
payment processor — almost all of it the fixed €0.25, not the percentage. The tier floor
matters more than any rate negotiation.

Three responses, in order of impact:

1. **Anchor the default tier at €9.99.** Costs nothing, worth 20 points of
   retained take — 44% survives the fee at €4.99 against 64% at €9.99.
2. **Push annual billing.** One fixed fee instead of twelve — worth ~€2.75 per subscriber
   per year. Patreon reports annual patrons churn at **one third** the rate of monthly ones,
   so the retention gain is larger than the fee saving.
3. **Renegotiate at volume.** Above ~€5M/yr processed, interchange-plus pricing is
   available. Not modelled — upside.

At Y7 the payment rail costs **€2.55M against €10.70M of revenue** — 24% of
revenue, our largest single cost line, larger than all salaries combined
(€1.54M). The share rose when VAT entered the model: the processor charges on
the price a fan pays, while the revenue it is measured against is net of the
VAT that price includes.

---

## The egress trap

`docs/costs.md` states, correctly, that the current architecture has near-zero
marginal compute cost: marketability scoring is deterministic formulas, not
model inference. **That property does not survive the pivot to paid content.**

Video served to paying fans is bandwidth, and bandwidth is where cloud providers
price aggressively.

| | Y1 | Y3 | Y5 | Y7 |
|---|---|---|---|---|
| AWS + zero-egress CDN | €2k | €28k | €149k | **€336k** |
| AWS + CloudFront list price | €4k | €56k | €290k | **€738k** |
| **Annual difference** | €2k | €27k | €142k | **€402k** |

At 1.8 GB per paying fan per month and an average of 278k paying fans through
the year, Y7 moves ~6.0 PB. At CloudFront list (~€0.075/GB after volume tiers)
**the bandwidth alone is €450k**; behind an object store with free egress
(Cloudflare R2, Backblaze B2 + Bunny) the same bytes cost **€48k**. The table
rows above are larger than both because they add the €288k of AWS compute and
storage that neither choice avoids — it is the difference between the rows, not
the rows themselves, that the egress decision moves.

> [!note] Average fans, not December's
> Bandwidth is billed for the months a fan is actually subscribed, so the
> driver is the **average** count through the year, not the year-end one. The
> model charged twelve months at the December figure until this was corrected,
> which overstated infrastructure in every year of the plan — the same error
> its own cohort model documents on the revenue side and had already fixed
> there.

**€402k a year is most of this plan's entire €464k cash trough, spent annually
and decided by one architectural choice** — €3.1M across the ten years.

The recommendation is AWS for compute and database — where its managed services
genuinely earn their premium — and a zero-egress provider for media delivery.
Hybrid, deliberately.

---

## AWS build-up

Compute and data stay on AWS. The plan below is what the current architecture
maps onto (`infra/k8s/stride.yaml` already describes this shape).

### Stage 1 — Y1–Y2 (validation → launch, ≤ 10k MAU)

| Service | Configuration | Monthly |
|---|---|---|
| ECS Fargate (API) | 2 tasks × 0.5 vCPU / 1 GB | €35 |
| RDS Postgres | db.t4g.small, Multi-AZ off, 20 GB gp3 | €45 |
| ElastiCache Redis | cache.t4g.micro (rate limits, sessions) | €13 |
| S3 | 200 GB media + snapshots | €5 |
| CloudFront / R2 | low volume | €10 |
| Route 53, ACM, Secrets Manager | | €8 |
| CloudWatch | logs + metrics, 30-day retention | €25 |
| SES | transactional email | €5 |
| **Total** | | **≈ €146–650/mo** |

### Stage 2 — Y3–Y5 (growth, ≤ 250k MAU)

| Service | Configuration | Monthly |
|---|---|---|
| ECS Fargate | 4–10 tasks, autoscaled | €280 |
| RDS Postgres | db.r6g.large Multi-AZ + read replica | €520 |
| ElastiCache | cache.r6g.large | €160 |
| S3 | 20–80 TB media, lifecycle to IA | €420 |
| Media delivery | zero-egress CDN | €650 |
| MediaConvert | transcoding on upload | €180 |
| CloudWatch + X-Ray | | €140 |
| WAF + Shield Standard | | €60 |
| **Total** | | **€2,100–11,000/mo** |

### Stage 3 — Y6–Y7 (scale)

| Service | Monthly |
|---|---|
| EKS (control plane + nodes), API + workers | €4,200 |
| Aurora Postgres, writer + 2 readers | €3,100 |
| ElastiCache cluster | €700 |
| S3 (300+ TB, tiered) | €4,800 |
| Media delivery (zero-egress) | €5,600 |
| MediaConvert | €2,400 |
| Observability | €1,900 |
| WAF, Shield Advanced, backup, DR | €1,300 |
| **Total** | **≈ €24,000/mo** |

**Reserved capacity and Savings Plans are not modelled.** Committing to 1-year
compute typically saves 25–40% on the Fargate/EKS/RDS lines — worth roughly
€60–90k/yr by Y7. Treated as upside, not as plan.

---

## People (Spain)

Spanish employer social security adds **~30–32%** on top of gross salary. Every
figure below is loaded cost.

| Role | Gross | Loaded | First hired |
|---|---|---|---|
| Founder / CEO | €0 → €45k | €0 → €59k | Y1 (unpaid — see opportunity cost) |
| Senior engineer | €55k | €72k | Y2 |
| BD / partnerships | €38k + commission | €50k+ | Y2 |
| Athlete success | €30k | €39k | Y3 |
| Content moderation lead | €34k | €45k | Y3 |
| Finance / ops | €42k | €55k | Y4 |
| DPO (fractional → hired) | €18k → €60k | €18k → €79k | Y3 fractional, Y5 hired |

| | Y1 | Y2 | Y3 | Y4 | Y5 | Y6 | Y7 |
|---|---|---|---|---|---|---|---|
| Headcount (FTE) | 1.5 | 3.0 | 7.0 | 14.0 | 24.0 | 36.0 | 50.0 |
| People cost | €57k | €156k | €420k | €896k | €1.58M | €2.45M | €3.50M |

**Spain is a structural cost advantage.** A senior engineer at €72k loaded costs
roughly half the equivalent in London or Amsterdam and a third of the Bay Area,
against a talent pool that is deep in Barcelona and Madrid. On a €23M-revenue
plan that is worth several million euros cumulatively — and it is a legitimate
argument to an investor for why the company is in Spain rather than an accident
of where the founder studied.

---

## Compliance and moderation

This is the line most creator-platform plans underestimate.

| Item | Y1 | Y3 | Y5 | Y7 |
|---|---|---|---|---|
| Legal & compliance | €18k | €90k | €200k | €270k |
| Moderation (variable) | €1k | €17k | €79k | €165k |
| Athlete verification (variable) | €0.7k | €9k | €30k | €43k |

Legal covers entity formation, policies reviewed by counsel (`docs/costs.md`
budgets €1–5k for the first pass), the DPO function, DAC7 reporting, platform
app-review lead time, and an annual security review.

Moderation is modelled at €22 per 1,000 items at 12 items per athlete per month.
It is a hybrid: automated classification first, human review on flags. **The
cost is not the issue — the liability is.** Paid content plus a population that
includes minors is the combination that has ended platforms, usually via card
schemes rather than regulators.

Verification is the same obligation on the supply side: vetting *who* is on the
platform rather than *what* they post, which is why it sits beside moderation in
cost of sales rather than in overhead. It is priced off the funnel the admission
gate creates — an athlete is the survivor of several applications, and a share of
those applications need a human to open a link
([11](11-admission-and-matching.md)).

| | Y1 | Y3 | Y5 | Y7 | Y10 |
|---|---|---|---|---|---|
| Applications behind the athlete plan | 2,000 | 16,563 | 51,958 | 70,820 | 72,199 |
| Manual reviews | 500 | 3,909 | 11,753 | 15,623 | 15,674 |
| Blended admission rate | 20% | 25% | 29% | 31% | 32% |
| **Reviewer FTE implied** | **0.02** | **0.15** | **0.46** | **0.61** | **0.61** |

**The euros are not the point and the model says so.** Verification peaks at
€25k a year and 0.33 of one person, and the whole discounted stream is worth
€63k against a €22.5M enterprise value — 0.28%. Two things follow, and they
matter more than the line item:

- **The admission rate is a real driver of marketing efficiency.** It climbs
  from 20% to 32% purely because club nominations grow as a share of applicants,
  and a nominated applicant arrives with a verified club's credibility floor
  behind them. Club partnerships are not just a cheaper channel; they are a
  *higher-yielding* one, and the model now shows the difference.
- **The reason to automate the check is latency, not labour.** An athlete
  sitting in the queue is not listed, not matchable and not earning. At 0.6 FTE
  nobody automates to save the salary; you automate so supply goes live the day
  it applies.

---

## Customer acquisition

<!-- MODEL:cac -->
|  | Athlete | Fan | Sponsor |
|---|---|---|---|
| Y1 CAC | €17 | ~€0 | €900 |
| Y7 CAC | €61 | ~€0 | €1,900 |
| Applications behind one athlete | 5.0x in Y1, 3.3x in Y7 | — | — |
| Channel | Clubs, federations, ambassador referral | **Brought by the athlete** | Outbound, events, agency partnerships |
<!-- /MODEL:cac -->

**Fan CAC is approximately zero, and that is the whole economic argument for
this model.** We do not buy the audience — the athlete already has it on
Instagram and TikTok. Stride converts an existing following into a paying one.
That is why fan revenue can lead in Y1 while sponsorship is still cold.

The corollary: **athlete CAC is the only acquisition cost that matters**, and
club partnerships are the cheapest route to it — one conversation, a whole
roster.

---

## Cost structure at maturity (Y7)

<!-- MODEL:costs_y7 -->
| Line | Y7 amount | % of revenue |
|---|---|---|
| Payment processing | €2.55M | 23.8% |
| Marketing / CAC | €1.70M | 15.9% |
| People | €1.54M | 14.4% |
| Other opex | €856k | 8.0% |
| Infrastructure | €336k | 3.1% |
| Legal & compliance | €270k | 2.5% |
| Payouts | €237k | 2.2% |
| Moderation | €70k | 0.7% |
| Athlete verification | €18k | 0.2% |
| **EBITDA** | **€3.12M** | **29.1%** |
<!-- /MODEL:costs_y7 -->

Infrastructure is 3.1% of revenue. **Payments are nearly eight times larger.** Any
optimisation effort belongs there — tier pricing, annual billing, processor
negotiation — not in the AWS bill.
