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
| ~~2~~ | ~~**Currency: EUR**~~ | ~~Everything~~ | — | **Shipped** — columns are `amount_eur`, `base_rate_eur`, `price_eur`, `budget_eur_*`, the interface renders €, and existing databases are renamed in place on start-up |
| 3 | **Subscriptions + tiers** | Streams 1–3 | L | Tier entity, recurring billing, entitlement checks, grace/dunning |
| 4 | **Content + media** | Streams 1–2 | XL | Posts, upload, transcode, storage, CDN, paywalled delivery |
| 5 | **Age assurance** | Legal launch | M | Partly delivered: admission collects a date of birth and refuses under-16s outright, and cannot auto-admit without one. Nothing *verifies* the date, and the 16/18 tiering below is designed but unbuilt |
| 6 | **Moderation** | Legal launch | L | Automated classification + human review queue + appeals |
| 7 | **Sponsor billing** | Stream 6 | M | Plan entity, entitlements, seat management |
| 8 | **DAC7 reporting** | EU legal | M | Platforms must report seller income to tax authorities |
| 9 | **Notifications** | Conversion | S | Email exists as a cost line, not as code |
| 10 | **Refunds & disputes** | Operations | M | Chargeback handling, partial refunds, deal disputes |
| 11 | **Athlete churn tracking** | The model itself | S | The weakest assumption in `model.py` is unmeasurable today |
| ~~12~~ | ~~**Campaign measurement**~~ | ~~Sponsor renewal; learned matching~~ | — | **Shipped** — see below |

**Effort: S ≈ days · M ≈ 2–4 weeks · L ≈ 1–2 months · XL ≈ 3+ months**, at the
Y2 team size of three.

On the currency: the seeded demo figures were *relabelled*, not converted. They
are illustrative fixtures chosen to be readable, not amounts anyone quoted, so
putting them through an exchange rate would have manufactured precision that was
never there. The migration itself carries real data — the rename happens in
place on start-up and is covered by a regression test that rewinds a seeded
database to the old schema and checks every value back out.

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

## Campaign measurement — shipped

Until this shipped, a deal could reach `status = 'completed'` with nothing
anywhere recording **what the sponsor got**. That mattered more once TEKTA
launched selling "identify, activate and **measure**"
([10](10-competitor-tekta.md)): Stride did the first and half the second.

It was cheaper than it sounded, because the measurement layer already existed.
`posts` and `post_metrics` already held reach, likes, comments, shares and watch
time per post per capture, and `engagement_rate()` already computed from them.
What was missing was the link.

### What was built

```sql
ALTER TABLE deals ADD COLUMN completed_at    TEXT;
ALTER TABLE deals ADD COLUMN projected_reach INTEGER;   -- stored at offer time

CREATE TABLE deal_deliverables (
    id       INTEGER PRIMARY KEY,
    deal_id  INTEGER NOT NULL REFERENCES deals(id),
    post_id  INTEGER NOT NULL REFERENCES posts(id),
    added_at TEXT NOT NULL,
    UNIQUE (deal_id, post_id)
);
```

| Endpoint | Who | Does |
|---|---|---|
| `GET /api/athlete/posts` | athlete | Their own recent posts, to pick a deliverable from |
| `POST /api/athlete/deals/{id}/deliverables` | athlete | Attaches the post that fulfilled the deal |
| `POST /api/athlete/deals/{id}/complete` | athlete | Sets `completed_at`; **requires ≥1 deliverable** |
| `GET /api/deals/{id}/performance` | sponsor | Delivered reach and engagement, cost per 1k reach, cost per engagement, actual vs projected, and the posts behind each |

Two guards carry the weight. **Attribution**: an athlete can only attach a post
from one of their own accounts, checked against `platform_accounts.creator_id` —
without it an athlete could claim someone else's reach, which would poison the
one dataset sponsors are asked to trust. The same query also excludes accounts
they have disconnected, because consent is not a one-time grant: the rows are
kept so past scores stay reproducible, but a platform you have taken back should
not still be earning. Two limits on that are deliberate. Disconnecting blocks
*further* attachments; it does not retract deliverables already attached, which
remain in the sponsor's report because that report records what was delivered
rather than what is currently connected. And an account in `error` state — a
failed token refresh — stays attachable, because a broken sync is an operational
problem and not a decision the athlete made.
**Completeness**: `complete` refuses with `no_deliverables` when nothing is
attached, so no deal can *reach* `completed` through the API without something a
sponsor can open. Rows written before that guard existed are not retrofitted —
the seeded Rio event deal is deliberately one of them, because the honest
demonstration of an unmeasured deal is an unmeasured deal. A sponsor opening it
sees `—` rather than a zero, which is the rule the whole measurement view
follows: unmeasured, not free.

`projected_reach` is captured **when the offer is sent**, from the athlete's
median reach across platforms. Without it there is nothing to measure against,
and it cannot be reconstructed later once the athlete's following has moved.
Deals that predate the column read as `—` rather than as a zero variance —
unmeasured, not free, the same rule the cost figures follow.

**Interface.** The athlete's Deals page gains a *Delivering* lane between open
offers and history; the sponsor's pipeline gains an inline performance panel on
any accepted or completed deal, where every headline figure decomposes to the
posts underneath it — the discipline already applied to marketability scores.

### Why this was the highest-value product change in the plan

1. **Sponsors renew on evidence.** A sponsor's second campaign used to be a leap
   of faith. Renewal rate is the difference between the base and conservative
   cases.
2. **It is the Phase-2 analytics dataset.** Learned matching weights need deal
   outcomes ([09](09-analytics-strategy.md)); there were none to learn from, so
   the weights could never stop being a guess. They now accumulate per deal.
3. **It is the decomposable version of what an agency asserts.** TEKTA's "fan
   intelligence" is a claim. This one opens.

### The two companions from the same reading — also shipped

**Time to first offer.** TEKTA advertises 50–70% faster than a traditional
agency. Both timestamps already existed (`campaigns.created_at`,
`deals.created_at`), so this is a query and a stat tile. It now reports the
median wait on the sponsor's campaign board — **and the number of campaigns that
have produced no offer at all**, because a median taken only over the campaigns
that worked is a survivorship figure. Measured before it is claimed.

**Disclosure text per deal.** Paid posts must be disclosed and the duty is the
athlete's — the Terms already said Stride surfaces it in the deal flow, and now
it does. The *Delivering* lane and the deliverable dialog both carry the wording
for the athlete's market (`#ad`, `#publicidad`, `#werbung`, `#publicité`…),
falling back to `#ad` with an explicit note when the country is unmapped. It
costs nothing, removes a real legal risk from the athlete, and is the kind of
thing that makes a platform feel like it is on their side.

### What this deliberately does not do yet

- **Reach is captured at the latest metric, not at a fixed window.** A post that
  keeps accruing views keeps improving the deal's number. Honest, but not the
  same as a 30-day campaign measurement, and the difference should be named
  before it is sold to a sponsor.
- **Nothing verifies the attached post is actually the sponsored one.** The
  attribution guard proves the post is the athlete's, not that it mentions the
  brand. Verifying that needs the disclosure tag or a campaign hashtag matched
  against post text — cheap, and the obvious next increment.
- **No aggregate view.** Performance is per deal. A sponsor with forty deals
  wants a campaign roll-up, which is a query over the same table.

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
