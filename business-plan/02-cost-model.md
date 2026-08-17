# 02 — Cost Model

Two costs decide whether this business works. Neither is engineering salary.

---

## The fixed-fee problem

Stripe charges **2.9% + €0.25**. On small subscriptions the fixed component is
most of the cost, and it lands on our commission, not on the athlete's share.

| Fan pays (monthly) | Our take (15%) | Payment cost | We keep | % of take retained |
|---|---|---|---|---|
| €4.99 | €0.75 | €0.39 | €0.35 | **47%** |
| €9.99 | €1.50 | €0.54 | €0.96 | **64%** |
| €14.99 | €2.25 | €0.68 | €1.56 | 70% |
| €24.99 | €3.75 | €0.97 | €2.77 | 74% |
| €89.00 (annual) | €13.35 | €2.83 | €10.52 | **79%** |

**Read that first row again.** At a €4.99 tier, more than half our commission
goes to the payment processor. We would be running a marketplace where Stripe
earns almost as much as we do.

Three responses, in order of impact:

1. **Anchor the default tier at €9.99.** Costs nothing, worth 17 points of
   retained take.
2. **Push annual billing.** One fixed fee instead of twelve. Worth ~€2.75 per
   subscriber per year.
3. **Renegotiate at volume.** Above ~€5M/yr processed, interchange-plus pricing
   is available; assume 2.4% + €0.20 from Y5. Not modelled — upside.

At Y7 the payment rail costs **€6.97M against €23.31M of revenue** — 30% of
revenue, our largest single cost line, larger than all salaries combined.

---

## The egress trap

`docs/costs.md` states, correctly, that the current architecture has near-zero
marginal compute cost: marketability scoring is deterministic formulas, not
model inference. **That property does not survive the pivot to paid content.**

Video served to paying fans is bandwidth, and bandwidth is where cloud providers
price aggressively.

| | Y1 | Y3 | Y5 | Y7 |
|---|---|---|---|---|
| AWS + zero-egress CDN | €2k | €32k | €177k | **€403k** |
| AWS + CloudFront list price | €5k | €87k | €552k | **€1.37M** |
| **Annual difference** | €2k | €55k | €375k | **€963k** |

At 1.8 GB per paying fan per month and 665k paying fans, Y7 moves ~14 PB. At
CloudFront list (~€0.075/GB after volume tiers) that is €1.37M. Behind an
object store with free egress (Cloudflare R2, Backblaze B2 + Bunny) it is
€403k.

**€963k a year is a Series A's worth of runway, decided by one architectural
choice.** The recommendation is AWS for compute and database — where its
managed services genuinely earn their premium — and a zero-egress provider for
media delivery. Hybrid, deliberately.

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

Legal covers entity formation, policies reviewed by counsel (`docs/costs.md`
budgets €1–5k for the first pass), the DPO function, DAC7 reporting, platform
app-review lead time, and an annual security review.

Moderation is modelled at €22 per 1,000 items at 12 items per athlete per month.
It is a hybrid: automated classification first, human review on flags. **The
cost is not the issue — the liability is.** Paid content plus a population that
includes minors is the combination that has ended platforms, usually via card
schemes rather than regulators.

---

## Customer acquisition

| | Athlete | Fan | Sponsor |
|---|---|---|---|
| Y1 CAC | €22 | ~€0 | €900 |
| Y7 CAC | €45 | ~€0 | €1,900 |
| Channel | Clubs, federations, ambassador referral | **Brought by the athlete** | Outbound, events, agency partnerships |
| Payback | ~7 months | Immediate | ~5 months at Scout Pro |

**Fan CAC is approximately zero, and that is the whole economic argument for
this model.** We do not buy the audience — the athlete already has it on
Instagram and TikTok. Stride converts an existing following into a paying one.
That is why fan revenue can lead in Y1 while sponsorship is still cold.

The corollary: **athlete CAC is the only acquisition cost that matters**, and
club partnerships are the cheapest route to it — one conversation, a whole
roster.

---

## Cost structure at maturity (Y7)

| Line | Amount | % of revenue |
|---|---|---|
| Payment processing | €6.97M | 30% |
| People | €3.50M | 15% |
| Marketing / CAC | €2.72M | 12% |
| Other opex | €1.86M | 8% |
| Payouts | €475k | 2% |
| Infrastructure | €403k | **1.7%** |
| Legal & compliance | €270k | 1.2% |
| Moderation | €165k | 0.7% |
| **EBITDA** | **€6.94M** | **30%** |

Infrastructure is 1.7% of revenue. **Payments are eighteen times larger.** Any
optimisation effort belongs there — tier pricing, annual billing, processor
negotiation — not in the AWS bill.
