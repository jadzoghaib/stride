# 01 — Revenue Model

## Why OnlyFans is the right reference, and where the analogy stops

OnlyFans' insight was not adult content. It was that **a creator with 1,000 real
fans earns more from 1,000 subscriptions than from 10 million ad impressions.**
Ad-share pays for attention; subscription pays for relationship.

| Platform | Creator keeps | Model | Median creator outcome |
|---|---|---|---|
| YouTube | ~55% | Ad share on views | Needs ~1M views/mo to matter |
| Instagram | ~0% direct | Brand deals only | Nothing without a brand deal |
| Twitch | ~50% | Subs + ads | Needs live-hours scale |
| Patreon | ~88–92% | Subscription | Works at small scale |
| **OnlyFans** | **80%** | Subs + PPV + tips | Works at very small scale |
| **Stride (proposed)** | **85%** | Subs + unlocks + tips **+ sponsorship** | Works at small scale, plus a second payer |

**Where the analogy holds:** recurring subscription, creator-set pricing, direct
relationship, power-law outcomes, one-off unlocks and tips on top of the base.

**Where it stops, in ways that matter:**

| Difference | Consequence for Stride |
|---|---|
| Athlete content is brand-safe | Better card-scheme terms, no high-risk processor premium, sponsors will co-exist with it |
| Athletes have a **second payer** (sponsors) | Two revenue engines from one audience — OnlyFans has one |
| Performance is objectively measured | The analytics engine is a real moat; "audience quality" is provable, not asserted |
| Athletes are often minors | A safeguarding obligation OnlyFans solved by banning under-18s outright |
| Careers are seasonal | Subscription revenue smooths what sponsorship spikes |
| Clubs exist | A B2B2C distribution channel: sign a club, acquire a roster |

---

## The eight revenue streams

| # | Stream | Payer | Mechanism | Take | Built? |
|---|---|---|---|---|---|
| 1 | Fan subscriptions | Fan | Recurring monthly tier, athlete sets price | 15% | ✗ |
| 2 | Content unlocks (PPV) | Fan | One-off purchase of a post or video | 15% | ✗ |
| 3 | Tips | Fan | Voluntary, often around results | 15% | ✗ |
| 4 | Sponsorship deals | Sponsor | Take on deal value | 10% | ◐ records only |
| 5 | Club packages | Sponsor | Take on package value | 10% | ◐ records only |
| 6 | Scout SaaS | Sponsor | Monthly seat/plan for matching + evidence | 100% | ◐ features exist, no billing |
| 7 | Managed matchmaking | Sponsor | Done-for-you campaign, fee or higher take | 100% | ✗ |
| 8 | Market intelligence | Brand / agency | Aggregate reports on athlete audience economics | 100% | ✗ |

Streams 1–3 are the OnlyFans core. 4–6 are the reason this is not just OnlyFans
for sport. 7–8 are later-stage margin, deliberately excluded from the base model
so the plan does not depend on them.

---

## Fan tiers

Athletes set their own price; Stride supplies defaults that steer away from the
uneconomic bottom end (see [02](02-cost-model.md#the-fixed-fee-problem)).

| Tier | Suggested | What the fan gets | Why an athlete offers it |
|---|---|---|---|
| Supporter | €4.99 | Training log, results before the feed, supporter badge | Volume tier, low effort |
| Insider | €9.99 | Behind-the-scenes video, session breakdowns, monthly Q&A | **The default** — best margin per effort |
| Inner circle | €24.99 | Direct messaging, personalised video, early merch | Small cohort, high ARPU |
| Season pass | €89/yr | Insider for a competitive season | One payment fee instead of twelve |

**Recommendation: suggest €9.99 as the anchor and make €4.99 opt-in rather than
default.** The €4.99 tier retains 47% of our take after payment costs; €9.99
retains 64%. The same content at double the price is not twice as hard to sell
when the buyer is a fan of a specific athlete.

**Annual billing is worth more than a take-rate increase.** A €89 season pass
carries one €0.25 fixed fee instead of twelve — worth ~€2.75/fan/year, against
€13.35 of total take. Pushing 30% of subscribers annual is roughly equivalent to
raising the take rate by a point, without asking athletes for anything.

---

## Sponsor plans

| Plan | Price | Includes | Target |
|---|---|---|---|
| Scout Free | €0 | Public directory, 1 campaign, top-5 matches | Trial, inbound |
| Scout Pro | €249/mo | Full matching, evidence views, 5 campaigns, pipeline | Regional brands, small agencies |
| Scout Agency | €999/mo | Unlimited campaigns, multi-seat, API, saved searches | Agencies, national brands |

SaaS matters disproportionately: it is **100% margin** (no GMV, no payment
rail), and it converts the analytics engine into revenue that does not depend on
a deal closing. By Y7 it is €3.36M of the €23.31M — 14% of revenue at close to
100% gross margin, which is roughly 20% of gross profit.

---

## Take rate — benchmarked

Headline rates across the platforms an athlete could plausibly choose instead:

| Platform | Headline take | Other creator fees | Effective take, small creator |
|---|---|---|---|
| **Passes** | **10%** | **$0.30/txn + $29/mo creator fee** | **~16–25%** |
| OnlyFans | 20% | — | 20% |
| Fansly | 20% | — | 20% |
| Fanfix | 20% | — | 20% |
| Patreon | 8–12% | Payment fees passed to creator | ~12–15% |
| **Stride (proposed)** | **15%** | **none — we absorb payment costs** | **15%** |

And the middlemen the athlete is paying *on top* of the platform:

| Intermediary | Takes |
|---|---|
| Sports agent, endorsement deal | **10–20%** |
| Sports agent, playing contract | 4–10% |
| OnlyFans management agency | **20–50% of net**, on top of the platform's 20% |

### Why 15% beats Passes' 10% for the athletes we serve

Passes is the closest competitor and looks cheaper. It is not, for the long
tail, because its **$29/month creator fee is regressive** — a fixed cost is
brutal on a small creator and trivial on a large one.

An athlete earning `R` per month across `N` transactions keeps:

```
Stride   0.85 × R                          (nothing else deducted)
Passes   0.90 × R − €0.28×N − €27          (per-transaction + monthly fee)
```

At an average ticket of €9.20 those cross at **€1,380/month of fan revenue**
(`27 / (0.05 − 0.28/9.20)`).

| Athlete's monthly fan revenue | Keeps with Stride (15%) | Keeps with Passes (10% + fees) | Better off with |
|---|---|---|---|
| €100 | €85 | €60 | **Stride, by 42%** |
| €275 *(our modelled average)* | €234 | €212 | **Stride, by 10%** |
| €500 | €425 | €408 | **Stride** |
| €1,000 | €850 | €843 | **Stride**, barely |
| €1,380 | €1,173 | €1,173 | — crossover |
| €2,000 | €1,700 | €1,712 | Passes |
| €5,000 | €4,250 | €4,321 | Passes |

**Below €1,380/month, Stride's 15% pays the athlete more than Passes' 10%.**
Our modelled athlete at maturity earns €275/month — comfortably on the left of
that line, and the entire long tail with them. The athletes on the right are
the ones who already have an agent.

Note what the crossover means for our own economics: **the athletes for whom
Stride is the better deal are also the ones whose revenue Passes' pricing is not
designed to capture.** We are not undercutting a competitor on the same
customer; we are pricing for a customer they have chosen not to serve.

This is not a pricing trick; it is the opposite bet from Passes. **Their
pricing is optimised for creators who are already big. Ours is optimised for
creators who are not.** That is the same bet as serving niche sports, and the
two decisions have to agree with each other.

### The lever, quantified

At Y7 each point of take on fan GMV is worth **€927k of revenue**; 15% → 20%
adds €4.6M. It is the single biggest lever in the model.

**Recommendation: hold 15%, and never add a monthly creator fee.** The fee is
what makes Passes beatable, and copying it would forfeit the only pricing
argument that survives contact with a long-tail athlete. Revisit the percentage
at Series A, when the network — not the price — is the reason to stay.

*Sources: [Passes fee structure (Sacra)](https://sacra.com/c/passes/) ·
[Passes 10% confirmed at 2026 rebrand](https://www.prnewswire.com/news-releases/passes-rebrands-as-the-creator-accelerator-platform-302749690.html) ·
[Platform comparison](https://www.mexc.com/news/1014749) ·
[OnlyFans agency commissions 20–50%](https://arunatalent.com/blog/onlyfans-agency-commission-rates/) ·
[Sports agent endorsement commissions](https://www.oreateai.com/blog/understanding-sports-agents-commission-what-percentage-do-they-take/95c2df506ae450b9b71340b89cfcfece)*

---

## Revenue mix over time

| | Y1 | Y3 | Y5 | Y7 |
|---|---|---|---|---|
| Fan take | €29k (74%) | €738k (66%) | €5.29M (64%) | €13.91M (60%) |
| Sponsorship take | €5k (12%) | €191k (17%) | €1.90M (23%) | €6.04M (26%) |
| Sponsor SaaS | €6k (14%) | €180k (16%) | €1.15M (14%) | €3.36M (14%) |
| **Total** | **€39k** | **€1.11M** | **€8.33M** | **€23.31M** |

The mix shifts deliberately. Fans fund the early years because they can be
acquired at near-zero cost — **athletes bring their own audience**. Sponsorship
grows into it as the athlete pool becomes large enough that matching is
genuinely useful, which is when the analytics moat starts to pay.

---

## The cold-start problem, and the answer

A two-sided marketplace with a third side is three cold starts. The sequence
that avoids all three at once:

1. **One anchor athlete** brings fans on day one. Fan revenue needs no sponsors.
2. **Their club** brings a roster — ten to thirty athletes without ten to thirty
   sales conversations.
3. **Sponsors arrive when the pool is measurable**, not when it is large. Fifty
   athletes with real analytics beat five hundred unmeasured ones.

This is why the athlete partnership in [04](04-capital-and-valuation.md#the-anchor-athlete)
is a structural decision, not a marketing one.
