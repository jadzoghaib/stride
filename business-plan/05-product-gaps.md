# 05 — Product Gaps

What the application must gain before this plan can earn a euro. Assessed
against the codebase as it stands, not against a description of it.

---

## The headline

```
$ grep -ric "stripe|payout|subscription|tier|invoice|wallet" apps/api packages/
stripe: 0   payout: 0   subscription: 0   tier: 0   invoice: 0   wallet: 0
```

A fan's complete set of available actions today:

| Endpoint | What it does |
|---|---|
| `GET /api/discover` | Ranked athlete discovery |
| `POST /api/follows/{id}` | Follow |
| `DELETE /api/follows/{id}` | Unfollow |
| `GET /api/feed` | Following feed |

**There is no way for anyone to pay anything.** The entire fan-monetisation
model — 60% of Y7 revenue — has no product surface at all. Deals and packages
record an `amount` and a status, but no money moves; they are contracts of
record, not transactions.

This is not a defect. The product was built as an analytics-led sponsorship
marketplace and it is genuinely good at that. But the honest starting position
for the plan is that **the marketplace rail is half-built and the creator
platform is unbuilt.**

---

## Gap register

Ordered by what blocks revenue soonest.

| # | Gap | Blocks | Effort | Notes |
|---|---|---|---|---|
| 1 | **Payments + payouts** | All 8 streams | L | Stripe Connect (Express), KYC onboarding, webhooks, reconciliation |
| 2 | **Currency: EUR** | Everything | S | Schema is `amount_usd`, `base_rate_usd`, `price_usd`, `budget_usd`. Spain launch is EUR |
| 3 | **Subscriptions + tiers** | Streams 1–3 | L | Tier entity, recurring billing, entitlement checks, grace/dunning |
| 4 | **Content + media** | Streams 1–2 | XL | Posts, upload, transcode, storage, CDN, paywalled delivery |
| 5 | **Age verification** | Legal launch | M | Hard blocker — see below |
| 6 | **Moderation** | Legal launch | L | Automated classification + human review queue + appeals |
| 7 | **Sponsor billing** | Stream 6 | M | Plan entity, entitlements, seat management |
| 8 | **DAC7 reporting** | EU legal | M | Platforms must report seller income to tax authorities |
| 9 | **Notifications** | Conversion | S | Email exists as a cost line, not as code |
| 10 | **Refunds & disputes** | Operations | M | Chargeback handling, partial refunds, deal disputes |
| 11 | **Athlete churn tracking** | The model itself | S | The weakest assumption in `model.py` is unmeasurable today |

**Effort: S ≈ days · M ≈ 2–4 weeks · L ≈ 1–2 months · XL ≈ 3+ months**, at the
Y2 team size of three.

---

## What already exists and shortens the path

The architecture makes several of these cheaper than they would be on a
greenfield codebase:

| Existing | Why it helps |
|---|---|
| `deals` with a status lifecycle | The take-rate rail needs a payment attached, not a new model |
| `package_commitments` | Same — club revenue is a payment away |
| Consent recorded per platform with policy version | The pattern extends directly to payment and content consent |
| Audit log (`events`) taking arbitrary object types | Payment and payout events need no new infrastructure |
| RLS policies written for Supabase | Multi-tenant money data has a security model already drafted |
| `require_role` on every route | Entitlement checks have somewhere obvious to live |
| Aggregate-only demographics | Removes a whole category of privacy exposure from the content pivot |

**The riskiest gap is #4, content.** Everything else is a well-understood
integration. Media is where the cost model, the moderation obligation and the
egress decision all converge — and it is the one that turns a data product into
a content platform, with the operational weight that implies.

---

## Minors

The product already models a **13–17 audience band**, and athletes in the target
segment — semi-professional, nationally competitive — are frequently under 18.

Paid fan content plus a population that includes minors is the combination that
has ended platforms. The enforcement usually arrives from **card schemes rather
than regulators**: Visa and Mastercard can withdraw processing on suspicion
alone, and a marketplace without a payment rail is not a going concern.

Obligations that apply here:

| Requirement | Source |
|---|---|
| Parental consent for under-16s (varies 13–16 by member state) | GDPR Art. 8 |
| Age assurance proportionate to risk | EU DSA, UK OSA |
| Payouts to minors require guardian-held accounts | Payment institution rules |
| Employment/image-rights limits for minors in commercial deals | Spanish labour and image-rights law |

**Recommendation: launch adults-only.** Under-18 athletes may hold a profile and
analytics — that is the product's original, safe use case — but fan
monetisation, rate cards and payouts unlock at 18 or with a verified guardian
account.

This costs some addressable market and removes the risk that ends the company.
It also makes the anchor-athlete filter in [04](04-capital-and-valuation.md#the-anchor-athlete)
non-negotiable: **the first partner must be over 18.**

---

## Sequenced build

| Phase | Ships | Unlocks | Gate it serves |
|---|---|---|---|
| **P0** — pre-revenue | EUR migration, Stripe Connect, athlete KYC | Money can move | — |
| **P1** — first revenue | Tiers, subscriptions, entitlements, simple text/photo posts | Streams 1 + 3 | **Pre-seed gate** |
| **P2** — the thesis test | Video upload, transcode, paywalled delivery, moderation queue, age gate | Stream 2, legal launch | Pre-seed → Seed |
| **P3** — second engine | Deal payments, escrow, sponsor billing plans | Streams 4, 5, 6 | Seed gate |
| **P4** — scale | DAC7, refunds/disputes, multi-currency, notifications | EU operations | Series A gate |

**P1 is the whole ballgame.** It is the cheapest possible test of the only
assumption the business cannot survive being wrong about: *will fans of a
semi-professional athlete pay €9.99 a month?*

Text and photo posts behind a paywall answer that question. They need no
transcoding pipeline, no CDN decision, and far less moderation exposure than
video. **Ship P1, get three months of churn data from one anchor athlete, and
only then commit to P2's cost structure.**

If the answer is no, the sponsorship marketplace still works and the plan
becomes a different, smaller, entirely viable business — one the product already
supports today.
