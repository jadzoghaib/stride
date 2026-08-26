# 07 — Decisions & Open Questions

---

## Settled

| # | Question | Decision | Consequence |
|---|---|---|---|
| **E** | Creator platform, or sponsorship marketplace? | **Creator platform with a sponsorship feature** | Fan revenue leads and funds the early years; sponsorship compounds behind it. Build order in [05](05-product-gaps.md#sequenced-build) follows from this |
| **A1** | Take rate on fan revenue | **15% flat, no monthly creator fee** | Benchmarked in [01](01-revenue-model.md#take-rate--benchmarked). Beats Passes for any athlete under €1,380/month — i.e. the whole long tail |
| **B2** | Minimum age | **16 for accounts**, tiered above that | Aligned with Spain's draft law. Fan subscriptions stay 18+ in v1 — see [05](05-product-gaps.md#the-age-model) for the one place I would push back |
| **C2** | Which sport first? | **Wrong question.** Segment by whether an intermediary exists | Niche sports first (market creation), popular sports second (disintermediation). Full reasoning in [06](06-market-strategy.md) |

### What those decisions cost

Each was the right call, and each closed off something worth naming:

- **15% flat** forfeits €4.6M of Y7 revenue versus 20%. Bought: a pricing
  argument that survives contact with the exact athlete we target.
- **18+ for fan subscriptions** forfeits the 16–17 cohort's fan revenue for the
  first year or two. Bought: distance from the risk that has produced litigation
  against creator platforms. The cohort still builds the analytics pool and
  converts automatically at 18.
- **Niche-first** forfeits early volume. Bought: a proof point that generalises
  upward, and no incumbent fighting back while the model is still fragile.

---

## Still open

### A2 — Free for athletes forever?

Free for the core is right for acquisition. The question is whether paid athlete
tools ever appear (deeper analytics, competitor benchmarking, media-kit export).

**My recommendation: free forever for the core**, paid tools only if athletes
ask unprompted. Charging the supply side before the marketplace is dense is how
marketplaces die — and a monthly athlete fee is precisely the Passes mistake we
are pricing against. **This is close to settled; flag it if you disagree.**

### A3 — Minimum tier price and annual billing

€4.99 retains 54% of our take after payment costs; €9.99 retains 71%; a €89
season pass retains 85%.

**Recommendation: €9.99 default, €4.99 available but unsuggested, and push the
season pass hard.** Worth more than a take-rate change and costs nothing.
Needs a decision before P1 ships because it shapes the tier UI.

### B1 — Video, or text and photo first?

**Recommendation: text and photo in P1.** It answers the only question that
matters — *will fans pay?* — without a transcoding pipeline, a CDN decision, or
video's moderation exposure. Commit to video only once P1 has three months of
churn data. See [05](05-product-gaps.md#sequenced-build).

### B3 — Sponsorship payments through Stride, or record-only?

Today the product records deals but moves no money. **Recommendation: through
Stride, with invoicing above ~€5k.** Record-only take rates leak to zero.

Open sub-question: in the disintermediation pitch we claim 10% against an
agent's 10–20%. If sponsors pay outside the platform, that claim is
unenforceable — which makes this decision load-bearing for
[06](06-market-strategy.md), not just for revenue.

### C1 — Spain only through the pre-seed gate?

**Recommendation: yes.** One market, one language, one tax regime. Portugal in
Y2 as the cheapest test of whether the model travels.

### C3 — Anchor athlete: equity or cash?

**Recommendation: 1% advisory equity, 2-year vest, 6-month cliff, +0.5%
performance trigger.** Now with an added filter from [06](06-market-strategy.md):
they should come from a **niche sport, and be over 18**. A famous name would
prove the wrong thing and cost more.

### C4 — Agencies: compete or partner?

**Recommendation: partner.** They serve the top 1% and ignore our segment.
Scout Agency at €999/mo turns them into a channel.

Tension worth resolving: this sits slightly against the disintermediation pitch
in popular sports. The honest reconciliation is that we disintermediate the
*deal-finding*, not the *representation* — an agent still negotiates, we just
make the introduction on evidence instead of on their contact list.

### D1 — Raise €558k, or the €2.4M the rounds imply?

**Recommendation: non-dilutive stack first** (ENISA + Neotec, €300–500k), then a
smaller pre-seed. Every grant euro is equity retained.

### D2 — Founder salary in Y1?

The model assumes unpaid Y1 — €50k of forgone earnings. Given the plan's modest
capital need, €24k of Y1 salary changes little in the model and quite a lot in
sustainability. **Worth deciding deliberately rather than by default.**

### D3 — Which valuation do we present?

**Recommendation: lead with the exit multiple discounted back (€25–56M), present
the DCF (€22.5M) as the conservative floor**, and explain why they differ. An
examiner who spots a perpetuity-growth DCF applied to a company still growing
22% in the terminal year will discount everything else.

---

## New questions raised by the decisions just made

### F1 — Does the 16–17 cohort get fan monetisation in Y2, or later?

They convert automatically at 18, so the question is whether to build the heavy
safeguards (identity-verified subscribers, pre-publication review, no DMs) to
unlock them sooner. **My instinct: not before there is a moderation team**, so
Y3 at the earliest. But it is a real cohort with real revenue.

### F2 — Which two or three niche sports, specifically?

The filter is in [06](06-market-strategy.md#which-niche-sports-concretely);
endurance and padel score highest. **This is the one call where your knowledge
of which federations will take a meeting beats any analysis I can do.**

### F3 — Should the sport index ship *inside the product*?

`model.py` is now segmented and `sport_index.py` classifies sports — so the
business question is answered. The **product** question is not: today
`audience_scale` is `logband(followers, 2, 7)` with no sport input at all, so a
trail runner with 25k followers scores identically to a footballer with 25k.
The engine currently under-rates exactly the athletes the strategy targets.
Fixing it means a sport-relative percentile alongside the absolute score — see
[05](05-product-gaps.md). **My view: yes, and it is the highest-leverage product
change in the plan**, because it makes the algorithm agree with the strategy.

### F4 — What happens to the sponsorship marketplace if fans don't pay?

The fallback is good and should be stated: **the product already works as a
sponsorship marketplace today.** If P1 shows fans won't pay, the company becomes
a smaller, viable, analytics-led B2B business rather than a failure. Worth
naming explicitly in any investor conversation — it is a genuine floor under the
downside, and few pre-seed companies have one.
