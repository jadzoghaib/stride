# 17 — Evidence Base: Where Every Assumption Comes From

*Generated from `research_data.py`, which also produces the Research
sheet of the financial model. Every driver the model runs on appears
here with its method and the comparable behind it. A driver appears*
*twice where two separate decisions rest on it.*

---

## 17.1 What the model is built on

The model runs on **32 named assumptions**. Classifying them honestly matters more than the count, because a plan that presents an estimate with the same confidence as a published figure is not being read carefully by its own author.

| Method | Count | What it means |
|---|---|---|
| **SOURCED** | 10 | A published figure, cited |
| **BENCHMARKED** | 9 | Set against named comparables |
| **DERIVED** | 3 | Computed from other assumptions or from the codebase |
| **ESTIMATE** | 10 | Reasoned, with no published figure behind it |

| Confidence | Count |
|---|---|
| High | 11 |
| Medium | 12 |
| Low | 9 |

> [!warning] 10 of 32 assumptions are estimates, and 9 carry low confidence
> These are listed below rather than buried. The weakest two are the
> athlete count trajectory, which is a target rather than a forecast,
> and sports fandom by country, which is the softest layer of the
> sport index. Both are named as such in the rows that follow.

---

## 17.2 The assumptions, in full


### Pricing & Take Rate

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Take rate on fan revenue** | BENCHMARKED | High | Passes charges 10% but adds $0.30/txn and a $29/month creator fee; OnlyFans, Fansly and Fanfix are all 20%; Patreon 8-12%. A flat 15% with no monthly fee pays an athlete more than Passes for anyone under EUR 1,380/month of fan revenue. | Sacra company profile (Passes); Passes rebrand release, Apr 2026; MEXC platform comparison 2026 |
| **Take rate on sponsorship** | BENCHMARKED | High | Sports agents take 10-20% of an endorsement and 4-10% of a playing contract. On OnlyFans, management agencies take a further 20-50% on top of the platform's 20%. | Oreate and Sapling agent-commission surveys; Aruna Talent agency rate guide 2026 |
| **Suggested tiers 4.99 / 9.99 / 24.99** | BENCHMARKED | Medium | Patreon's typical patronage is quoted at $8-12/month, so the EUR 9.99 anchor sits inside the observed band. EUR 4.99 retains only 54% of our take after payment fees, against 71% at EUR 9.99 — which is why the floor matters more than the take rate. | Patreon 2024 Transparency Report; independent audits of ~1,200 creators |
| **Season pass / annual billing** | SOURCED | High | Patreon reports that annual patrons churn at ONE THIRD the rate of monthly patrons. This is the single strongest piece of evidence in the plan for pushing annual billing. | Patreon 2024 Transparency Report |

### Fan Economics

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Fan ARPU per month** | BENCHMARKED | Medium | Patreon's average monthly support rose from $5.40 to $6.10 during 2024, with typical patronage quoted at $8-12. Our EUR 8.00-9.50 sits in the upper-middle of that range. | Patreon 2024 Transparency Report |
| **Fan churn per month** | ESTIMATE | Low | OPTIMISTIC AGAINST BENCHMARK. Patreon runs 10-15% monthly. We assume 6-9% (niche) and 9-13% (popular), arguing that training content is habitual and that competitive seasons create natural renewal moments. That argument is currently untested. | Patreon 2024 Transparency Report (10-15%/month) |
| **Paying fans per monetising athlete** | DERIVED | Medium | 20 rising to 48 over ten years. Cross-check: Patreon creators average $350/month and our modelled niche athlete at maturity earns about EUR 313/month — closely aligned, which is reassuring for an assumption built bottom-up rather than from a comparable. | Patreon 2024 Transparency Report (creator average $350/month) |
| **Share of athletes who monetise** | ESTIMATE | Low | 28% rising to 50% for niche sports. No direct comparable exists — neither Patreon nor OnlyFans publishes activation rates for creators who sign up but never charge. | None found |
| **Fan acquisition capacity** | ESTIMATE | Low | An athlete can recruit 30-69 new paying fans a year depending on segment. This ceiling is what makes churn bite in the model: without it, higher churn perversely RAISED revenue, because the year-end target was reachable at any churn rate. | None — introduced to fix a modelling flaw found by stress testing |

### Payment Rails

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **PSP percentage fee** | SOURCED | High | Stripe for a Spanish entity: 1.5% + EUR 0.25 on EEA domestic cards, 2.5% on UK cards, 3.25% on non-EEA. 1.9% is the blend for a mostly-European fan base. CORRECTION: an earlier version of this model used the US headline of 2.9% and overstated the largest cost line in the business by about a third. | Stripe published EU/EEA pricing, 2026 |
| **PSP fixed fee per transaction** | SOURCED | High | EUR 0.25 per transaction. On a EUR 4.99 tier that single fee is a third of our take, which is why the tier floor and annual billing move more margin than the take rate does. | Stripe published pricing, 2026 |
| **Payout fees** | SOURCED | Medium | Stripe Connect Express: roughly 0.25% + EUR 0.25 per payout, plus a monthly active-account fee that is not modelled as a separate line. | Stripe Connect pricing, 2026 |

### Market Sizing

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Sport participation by country** | ESTIMATE | Medium | Eurobarometer 525, share who NEVER exercise: Finland 8%, Sweden 12%, Denmark 20%, Poland 65%, Greece 68%, Portugal 73%, EU-27 average 45%. Six of the 34 countries in the index are measured; the other 28 are estimates placed inside that distribution. | Special Eurobarometer 525, Sport and Physical Activity, September 2022 |
| **Padel market size** | SOURCED | High | Spain has ~6.0M active players (12.7% of the population), 109,040 federation licences and 17,300+ courts; globally 35M+ players and 77,000+ courts. This is the clearest case for weighting a sport regionally rather than globally — padel scores 77.7 in Spain and 45.1 worldwide. | FIP World Padel Report 2025 |
| **Sports fandom by country** | ESTIMATE | Low | The weakest layer of the sport index, and it drives both the `demand` and `appetite` signals. Commercial audience panels (Nielsen Sports, YouGov) cost more than the entire Y1-Y2 analytics budget. | None — reasoned estimates only |
| **Athlete count trajectory** | ESTIMATE | Low | 400 rising to 40,000 over ten years. This is the PLAN, not a benchmark: marketing spend is derived from it at segment CAC, not the other way round. Everything in the model scales off this line. | None — it is a target |

### Costs

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Athlete CAC** | ESTIMATE | Low | EUR 16-36 for niche, EUR 40-88 for popular. The gap reflects displacing an existing agent relationship versus reaching someone with no representation at all. No published comparable exists for athlete acquisition in this segment. | None found |
| **Admission rate, direct applicants** | DERIVED | Medium | 20% of direct applicants are admitted, 25% go to a human, 40% are refused and 15% never finish the form. Not a judgement: it is the ops-load output of scripts/admission_stress.py run over the admission policy itself, so retuning a threshold moves this figure. The sweep asserts the model and the policy stay in step and fails if they drift. | scripts/admission_stress.py, section 7 — over a modelled applicant mix |
| **Admission rate, club-nominated** | ESTIMATE | Low | 45% admitted against 20% direct. A verified club's nomination confers a credibility floor of 0.75 x its own legitimacy score, which carries a completed application over the admit line that would otherwise have gone to review. It cannot carry an empty one — no club can supply someone else's date of birth — so the uplift is real but bounded. | None — the mechanism is built and tested, the conversion is not yet measured |
| **Athlete verification cost** | DERIVED | Medium | Four minutes per manual review, priced at the same loaded salary the People line uses, over 1,700 productive hours. Peaks at EUR 47k and 0.64 reviewer-FTE in Y10, which is the finding rather than the cost: verification is not a money problem at this scale. The reason to automate it is latency — an athlete sitting in the queue is not listed, not matchable and not earning. | Derived from the sweep's review volume and the model's own salary line |
| **Athlete CAC vs the funnel** | ESTIMATE | Low | Deliberately NOT multiplied by the admission funnel. Segment CAC is defined as the cost of landing one athlete ON the platform, so scaling it by 1/admission-rate would charge the same money twice. The Costs sheet carries a memo line showing what that CAC works out to per application (EUR 3.40 in Y1 rising to EUR 22) — the figure to hold against what a channel actually charges per name reached. | None — this is a definitional choice, made explicit so it is not silently reversed |
| **Loaded salary, Spain** | BENCHMARKED | Medium | EUR 38k-76k loaded. Spanish employer social security adds roughly 31% on top of gross, so a senior engineer at ~EUR 55k gross costs ~EUR 72k — around half the London equivalent, which is a real argument for being in Spain rather than an accident of geography. | Spanish Seguridad Social employer contribution rates |
| **AWS infrastructure** | BENCHMARKED | Medium | Built up per stage from list prices: Fargate, RDS then Aurora, ElastiCache, S3, MediaConvert, CloudWatch. Reserved capacity and Savings Plans (25-40%) are deliberately excluded and treated as upside. | AWS published list pricing, 2026 |
| **Media egress** | SOURCED | High | EUR 0.008/GB behind a zero-egress object store versus EUR 0.075/GB at CloudFront list price. At Y10 volumes that single architectural choice is worth over EUR 1M a year — the largest cost decision in the plan that is settled by engineering rather than negotiation. | Cloudflare R2 and Backblaze B2 pricing; AWS CloudFront list price |
| **Moderation cost** | ESTIMATE | Low | EUR 22 per 1,000 items reviewed, on a hybrid of automated classification and human review. Vendor pricing varies widely with SLA and content type. | None cited |

### Tax, Capital & Valuation

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Corporate tax rates** | SOURCED | High | 15% for the first four profitable years under the Spanish Startup Law, then the 25% standard rate. Modelled with loss carryforward against the Y1-Y4 losses. | Ley de Startups (Spain); Impuesto sobre Sociedades |
| **Risk-free rate** | SOURCED | High | Spanish 10-year sovereign yield, ~3.2% in mid-2026. Used as the floor for the founder opportunity-cost calculation rather than as the discount rate. | Spanish 10Y government bond yield |
| **WACC / discount rate** | BENCHMARKED | Medium | 25%. The conventional range for pre-revenue to early-revenue venture is 20-35% and we sit mid-range. The sensitivity grid runs 18-30% precisely because this is arguable rather than knowable. | Standard venture valuation practice |
| **Exit revenue multiple** | BENCHMARKED | Medium | 6.5x blended. Marketplace comparables trade around 4x revenue and high-growth SaaS around 9x; our Y10 mix is roughly 55% marketplace take and 12% SaaS. | Public marketplace and SaaS trading multiples |
| **Terminal growth** | BENCHMARKED | Medium | 3%, approximating long-run nominal GDP. Ten explicit forecast years were chosen partly so this assumption carries less of the valuation than it would at Y7. | Standard DCF convention |

### Compliance

| Assumption | Method | Confidence | Benchmark or comparable | Source |
|---|---|---|---|---|
| **Payout age floor** | SOURCED | High | Stripe Express and Custom Connect require 18. Standard Connect allows 13+, but a legal guardian must own the account and hold the bank account the money lands in. | Stripe Connect documentation |
| **Digital consent age, Spain** | SOURCED | High | 14 today under LOPDGDD Art. 7. A draft Organic Law on the Protection of Minors in Digital Environments would raise it to 16 and make age verification mandatory — which is why 16 is the forward-compatible floor for an account. | LOPDGDD Art. 7; draft Organic Law, Council of Ministers, March 2025 |

---

## 17.3 How this table is kept true

This appendix is generated, not maintained. `research_data.py` is the single source for both this table and the workbook's Research sheet, so the document and the model cannot disagree about where a number came from. What it records is provenance, not value: the numbers themselves live in the Assumptions sheet, which the workbook references live, and the prose figures are pinned separately by `scripts/doc_consistency.py`. Changing a driver therefore updates the model and the pinned prose, and leaves this table's method and source columns standing, which is correct only for as long as the reasoning behind them still holds. That judgement is not automatable.

