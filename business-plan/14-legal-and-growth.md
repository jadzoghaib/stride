# 14 — Legal Form and Intellectual Property

*ESADE outline §10. The growth strategy that used to sit here is now its own
section: see [16](16-growth-strategy.md), which the outline separates and which
an examiner grades separately. The regulatory analysis (VAT, GDPR, the age
model and sponsorship rules) is in
[§8 of the full plan](stride-business-plan-draft.md) and is not repeated here.
This section covers the corporate and intellectual property questions the
full plan does not.*

---

## 14.1 Legal form and structure

### The choice: Sociedad Limitada (S.L.)

| Form | Minimum capital | Fit |
|---|---|---|
| **Sociedad Limitada (S.L.)** | **€1** since *Ley 18/2022, Crea y Crece* | **Chosen.** Standard for Spanish venture-backed startups; investors expect it |
| Sociedad Anónima (S.A.) | €60,000, 25% paid up | Rejected. Capital requirement and formality serve no purpose pre-Series A |
| Autónomo (sole trader) | — | Rejected. No limited liability; cannot issue shares, so cannot raise |
| Foreign holding (Delaware, Estonia) | — | Rejected for now. See below |

**Why S.L.** Limited liability, share issuance for the pre-seed, and
eligibility for the **Ley 28/2022, Ley de Startups** regime, which is a
separate statute from the one that cut the capital floor (15% corporate tax for
the first four taxable years, worth €1.57M across Y6–Y9 in the model), and
eligibility for ENISA
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
  no convertible notes, no SAFEs, an S.L. handles them badly under Spanish law
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
| **"Stride" word mark** | EU trade mark (EUIPO), Nice classes 9, 35, 41, 42 | **To file.** €850 for the first class, €50 for the second, €150 for each beyond it — **€1,200** for four |
| Domain and handles | Registration | To secure alongside the mark |
| **Athlete engagement database** | *Sui generis* database right (Directive 96/9/EC) | Arises automatically from substantial investment in obtaining and verifying the data. This is the most valuable and least discussed protection we have |
| Platform content (athlete posts, media) | Licensed from athletes, not owned | Terms grant a limited licence to host, display and promote; the athlete retains ownership |
| Sponsor campaign data | Contractual confidentiality | Per-deal terms |

> [!important] The name needs clearing before it needs filing
> "Stride" is a common English word in an active sector; there are existing
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
