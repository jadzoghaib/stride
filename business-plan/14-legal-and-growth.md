# 14 — Legal Form, Intellectual Property, and Growth Strategy

*ESADE outline §10 (Legal aspects) and §12 (Company growth and business
development strategy). The regulatory analysis — VAT, GDPR, the age model and
sponsorship rules — is in [§8 of the full plan](stride-business-plan-draft.md)
and is not repeated here; this section covers the corporate and IP questions
that document does not, and then the growth path.*

---

## 14.1 Legal form and structure

### The choice: Sociedad Limitada (S.L.)

| Form | Minimum capital | Fit |
|---|---|---|
| **Sociedad Limitada (S.L.)** | **€1** since the Ley de Startups (2022) | **Chosen.** Standard for Spanish venture-backed startups; investors expect it |
| Sociedad Anónima (S.A.) | €60,000, 25% paid up | Rejected. Capital requirement and formality serve no purpose pre-Series A |
| Autónomo (sole trader) | — | Rejected. No limited liability; cannot issue shares, so cannot raise |
| Foreign holding (Delaware, Estonia) | — | Rejected for now. See below |

**Why S.L.** Limited liability, share issuance for the pre-seed, eligibility for
the **Ley de Startups** regime (15% corporate tax for the first four taxable
years, worth €1.57M across Y6–Y9 in the model), and eligibility for ENISA
participative loans and CDTI Neotec grants, which are the non-dilutive stack in
[04](04-capital-and-valuation.md).

**Why not a foreign holding company yet.** A Delaware or Dutch holding above a
Spanish operating company is the standard structure *if* US venture capital
leads a round. Doing it now would forfeit the Ley de Startups rate and the
Spanish grant eligibility, for an outcome that may never happen. The decision
point is the Series A, and the structure is designed to be flippable: a clean
cap table with one share class and no convertible instruments makes a later
reorganisation mechanical rather than fraught.

### Capital structure

- **One class of ordinary shares** through the pre-seed. No preference stacking,
  no convertible notes, no SAFEs — an S.L. handles them badly under Spanish law
  and they complicate the very reorganisation above.
- **Founder vesting**: four years, one-year cliff, applied to the founder's own
  shares. Unusual to self-impose, and exactly what a pre-seed investor will ask
  for.
- **ESOP to 10%** by the Series A, via a Spanish *plan de incentivos*. Note the
  friction honestly: Spain has no equivalent of a US-style option pool held at
  the company, so the pool is contractual and its tax treatment for employees is
  less favourable than in the UK or US. The Ley de Startups improved this
  (deferred taxation and a €50,000 annual exemption) but did not eliminate it.

### Registration and compliance calendar

| Item | When |
|---|---|
| Name reservation (*denominación social*), notarial deed, Registro Mercantil | Pre-raise |
| NIF, IAE registration, social security as employer | At incorporation |
| Startup certification with ENISA (for the Ley de Startups regime) | Immediately after incorporation |
| Quarterly VAT (Modelo 303), OSS registration for cross-border B2C | From first fan revenue |
| DPO appointment (fractional) | Y3 |

---

## 14.2 Intellectual and industrial property

The honest position first: **the defensibility of this business is not its
patents.** There are none, and there will not be. It is the data position, the
athlete relationships, and the accumulated scoring history. The IP work below
protects the surface, not the substance.

### What we own and how it is protected

| Asset | Protection | Status |
|---|---|---|
| **Marketability scoring engine, admission gate, matching algorithm** | Trade secret + copyright in the source | Held. The repository is currently public for academic assessment; it goes private before commercial launch |
| **"Stride" word mark** | EU trade mark (EUIPO), Nice classes 9, 35, 41, 42 | **To file.** ~€850 for one class, €50 per additional |
| Domain and handles | Registration | To secure alongside the mark |
| **Athlete engagement database** | *Sui generis* database right (Directive 96/9/EC) | Arises automatically from substantial investment in obtaining and verifying the data. This is the most valuable and least discussed protection we have |
| Platform content (athlete posts, media) | Licensed from athletes, not owned | Terms grant a limited licence to host, display and promote; the athlete retains ownership |
| Sponsor campaign data | Contractual confidentiality | Per-deal terms |

> [!important] The name needs clearing before it needs filing
> "Stride" is a common English word in an active sector — there are existing
> marks in apparel and in fitness software. A clearance search across classes 9,
> 35, 41 and 42 in the EUIPO register comes **before** any brand spend, and a
> rebrand is far cheaper now than after the anchor athlete launch. This is
> flagged as an open item, not a solved one.

### IP ownership hygiene

- **Assignment clauses in every employment and contractor agreement.** Under
  Spanish law, employee-created works generally vest in the employer, but
  contractor-created works do not by default. Every contractor agreement
  assigns explicitly.
- **Open-source compliance.** The stack is permissively licensed (MIT/Apache/BSD).
  No copyleft dependency ships in the served product. This is checked, not
  assumed.
- **No third-party data scraped.** All platform analytics arrive through
  authenticated, athlete-consented API connections. That is a product decision
  with a legal dividend: there is no scraping exposure and no terms-of-service
  breach in the data position.

---

## 14.3 Growth and business development strategy

Growth is sequenced along three axes, and only one moves at a time.

### Axis 1 — Market

| Stage | Markets | Trigger to move |
|---|---|---|
| Pre-seed | **Spain only** | — |
| Seed | +1 market (Portugal or Italy) | 3 months of fan churn data; €80k recurring MRR |
| Series A | +3–4 markets, EU-wide | Unit economics stable across 3 markets |
| Y8+ | Selective non-EU | Regulatory review per market |

The second market is chosen for **sport-mix similarity, not size**: the sport
index in [08](08-sport-index.md) scores 714 country × sport pairs, and the right
second market is the one whose niche-sport profile most resembles Spain's, so the
admission model and the scoring weights transfer without recalibration.

### Axis 2 — Product

Fan monetisation deepens before sponsorship widens. The sequence is in
[12.11](12-operations-plan.md): tiers and billing, then one-off unlocks, then
video, then events and the club revenue split.

### Axis 3 — Channel

| Channel | Role | When |
|---|---|---|
| Direct athlete acquisition | The base. Community-led, sport by sport | Y1 |
| **Club partnerships** | The compounding one. A club brings a roster, not an athlete, and clubs have a reason to care about their athletes' income | Y2 |
| Federation relationships | Credibility and licence data at national scale | Y3 |
| Sponsor self-serve | Lowers the cost of the long-tail sponsor | Y4 |
| Managed services / agency | Higher take, higher touch, for the largest campaigns | Y6 |

> [!note] The club channel is the growth strategy, not a channel within it
> A single club with 40 athletes replaces 40 individual acquisitions, and it
> arrives with the verification problem already solved — the club vouches for its
> own roster. That is why club nomination exists in the admission model, and why
> the B2B2C motion is where the plan expects operating leverage to come from
> after Y3.

### What we will not do

Stated because growth plans are judged as much by their exclusions:

- **No expansion into popular-sport representation.** That is the agents'
  business, and competing there means competing on relationships we do not have.
- **No paid social acquisition of fans.** Fans are acquired by athletes, not by
  us. The model does not spend on fan acquisition, which is disclosed as
  understating the risk rather than presented as efficiency.
- **No white-label of the analytics engine.** It is the moat; licensing it to a
  federation or an agency would rent out the one thing that is hard to copy.

### Long-term options

The plan is built to reach profitability without an exit, which is what makes
the options real rather than hopeful:

1. **Independent operation.** EBITDA-positive in Y5, €10.8M EBITDA by Y10.
2. **Strategic acquisition.** The natural acquirers are creator platforms buying
   a vertical, sports-data companies buying a consumer surface, or a sponsorship
   agency buying disintermediation before it happens to them.
3. **Financial exit.** The valuation range and the reasoning behind it are in
   [04](04-capital-and-valuation.md).

No exit assumption is baked into the financial model. The valuation section
presents the DCF as the conservative floor precisely so that the plan does not
depend on one.
