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
| 12 | **Campaign measurement** | Sponsor renewal; learned matching | **M** | See below — mostly a join table, because the metrics already exist |

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

## Campaign measurement — the gap TEKTA made table stakes

A deal can reach `status = 'completed'`, and nothing anywhere records **what the
sponsor got**. There is no `completed_at`, no deliverable, and no row linking a
deal to the content that fulfilled it.

This matters more since TEKTA launched selling "identify, activate and
**measure**" ([10](10-competitor-tekta.md)). Stride does the first and half the
second.

**It is cheaper than it sounds, because the measurement layer already exists.**
`posts` and `post_metrics` already hold reach, likes, comments, shares and watch
time per post per capture, and `engagement_rate()` already computes from them.
What is missing is the link.

### The change

```sql
ALTER TABLE deals ADD COLUMN completed_at      TEXT;
ALTER TABLE deals ADD COLUMN projected_reach   INTEGER;   -- stored at offer time

CREATE TABLE deal_deliverables (
    id         INTEGER PRIMARY KEY,
    deal_id    INTEGER NOT NULL REFERENCES deals(id),
    post_id    INTEGER NOT NULL REFERENCES posts(id),
    added_at   TEXT NOT NULL,
    UNIQUE (deal_id, post_id)
);
```

| Endpoint | Who | Does |
|---|---|---|
| `POST /api/athlete/deals/{id}/deliverables` | athlete | Attaches the post that fulfilled the deal |
| `POST /api/athlete/deals/{id}/complete` | athlete | Sets `completed_at`; requires ≥1 deliverable |
| `GET /api/sponsor/deals/{id}/performance` | sponsor | Delivered reach, engagement, cost per engagement, actual vs projected |

`projected_reach` is captured **when the offer is sent**, from the athlete's
median reach × the number of deliverables. Without it there is nothing to
measure against, and it cannot be reconstructed later once the athlete's
following has moved.

### Why this is the highest-value product change in the plan

1. **Sponsors renew on evidence.** Today a sponsor's second campaign is a leap
   of faith. Renewal rate is the difference between the base and conservative
   cases.
2. **It is the Phase-2 analytics dataset.** Learned matching weights need deal
   outcomes ([09](09-analytics-strategy.md)); today there are none to learn
   from, so the weights can never stop being a guess.
3. **It is the decomposable version of what an agency asserts.** TEKTA's "fan
   intelligence" is a claim. Ours would open to the posts behind it — the same
   discipline already applied to marketability scores.

### Two smaller changes from the same reading

**Time to first offer.** TEKTA advertises 50–70% faster than a traditional
agency. Both timestamps already exist (`campaigns.created_at`,
`deals.created_at`), so this is a query and a stat tile, not a feature. Measure
it before claiming it.

**Disclosure text per deal.** Paid posts must be disclosed, and the duty is the
athlete's. Generating the correct tag for the market (`#ad`, `#publicidad`) on
the deal card is trivial, removes a real legal risk from the athlete, and is the
kind of thing that makes a platform feel like it is on their side.

---

## The age model

**Decision: 16 is the minimum age for an account.** That is defensible, and it
is forward-compatible with where Spanish law is going. But three constraints do
not move with it, so the age model has to be tiered rather than a single number.

### What the law actually says

| Point | Position | Source |
|---|---|---|
| Digital consent age in Spain **today** | **14** — below that, guardian consent required | LOPDGDD Art. 7 |
| GDPR default | 16, member states may lower to 13 | GDPR Art. 8 |
| Spain's direction of travel | A draft Organic Law on the Protection of Minors in Digital Environments (Council of Ministers, March 2025) would raise digital consent **back to 16** and impose **mandatory age verification** on platforms | Draft bill, in Parliament |
| Stripe Express / Custom Connect | **18 minimum.** Sign-up is refused below it | Stripe Connect docs |
| Stripe Standard Connect | 13+, but a **legal guardian must own the account**, and payouts need a verified bank account in the owner's name | Stripe support |
| Commercial use of a minor's image | Guardian consent required in Spain | LO 1/1982 — *confirm scope with counsel* |

**Choosing 16 is well-aligned with the draft law**, and if that bill passes, age
verification becomes a legal obligation rather than a design choice. Building
age assurance is therefore not optional under either outcome — only the deadline
is uncertain.

### The distinction that actually matters

Not age, but **who is paying and for what**:

| | A sponsor pays for a post | An adult pays for private access |
|---|---|---|
| Precedent for minors | Universal — minors sign endorsement deals in every sport | Essentially none on reputable platforms |
| Counterparty | A company, contractually identified | An individual, pseudonymous |
| Relationship | Mediated by a contract and a guardian | Direct, recurring, and private |
| Risk if it goes wrong | Contractual dispute | Safeguarding failure |

A 16-year-old gymnast with a kit sponsor is normal. A 16-year-old selling
monthly subscriptions with direct messaging to adult subscribers is the pattern
that has produced litigation against creator platforms. **The content being
entirely innocent does not change the shape of the risk**, and card schemes act
on the shape.

### Proposed tiers

| Age | Profile & analytics | Club roster | Sponsorship deals | Fan subscriptions | Direct messaging | Payouts |
|---|---|---|---|---|---|---|
| **Under 16** | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **16–17** | ✓ | ✓ | ✓ *guardian co-signs* | ✗ *(v1)* | ✗ | Guardian-owned Standard Connect |
| **18+** | ✓ | ✓ | ✓ | ✓ | ✓ | Express Connect, own account |

**The one place I would push back on 16 is fan subscriptions**, and only there.
Everything else the platform does is safe at 16 and industry-normal.

If you want 16–17 fan monetisation in v1 anyway, the minimum safeguards are:
no direct-messaging tier at any price, no pay-per-view unlocks, guardian-owned
payout account, identity-verified subscribers, and human review of every post
before it goes behind a paywall. That is a materially heavier moderation
operation than the model budgets, and it is the version I would revisit after
the platform has a moderation team rather than before.

### Consequences for the plan

- **Age assurance is a P2 build, not optional** — see the sequencing below.
- The anchor athlete filter in [04](04-capital-and-valuation.md#the-anchor-athlete)
  stays: **the first partner should be over 18**, because the pre-seed gate tests
  fan subscriptions and that surface is 18+ in v1.
- Under-18 athletes are still worth onboarding from day one. They build the
  analytics pool, they attract sponsors, and they convert to fan monetisation
  automatically on their eighteenth birthday. **The cohort is an asset that
  matures on a known date.**

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
