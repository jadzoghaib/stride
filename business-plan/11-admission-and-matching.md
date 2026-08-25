# 11 — Admission, Club Eligibility and Matching

Who is allowed onto the platform, whose word carries whom, and how a campaign
ranks the people who got in. Cold start is the problem all three solve: before
there are outcomes to learn from, the only evidence is what an applicant
submits and what their public accounts show.

Implemented in `apps/api/stride_api/admission.py` and `matching.py`. Swept
adversarially by `scripts/admission_stress.py`.

---

## The decision everything else follows from

**Credibility and commercial value are two different scores, and only one of
them is a gate.**

| | Credibility | Social score |
|---|---|---|
| Asks | is this entity what it claims to be? | how valuable is it to a sponsor? |
| Source | evidence the applicant supplies | measurement the platform takes |
| Setting | adversarial — applicants lie | non-adversarial — data is what it is |
| Shape | a gate | a ranking |
| Failure mode | fraud gets in | ordering is wrong |
| Role | **admission** | **listing and matching** |

The tempting move is to blend them: `A = 0.6·C + 0.4·S`, admit above 60. Work
it through and the gate does the opposite of what the product promises.

| Applicant | C | S | Blended A | Blended verdict | Ours |
|---|---|---|---|---|---|
| Fitness influencer: local club claim, 5 years, **no proof** | 40 | 95 | **62** | admitted | **rejected** |
| Regional athlete, federation roster verified, no socials yet | 56 | 0 | **34** | rejected | **admitted** |

A compensatory gate lets reach buy legitimacy, which admits exactly the person
Stride exists not to be, and rejects exactly the person it exists to serve.
Worse, it does the second by treating *unmeasured* analytics as a zero — the
error `matching.py` already refuses to make.

So: **credibility decides admission. The social score can only route a case to
human review, never raise it.** What the social score actually governs is
listing: an admitted athlete with nothing to show starts as `draft` until they
connect a platform. Gate on legitimacy, tier on value.

---

## Three rules the arithmetic enforces

**1. Evidence multiplies, it does not add.** In the original rubric proof links
were a required field worth zero points, so a self-declared `international`
claim with a dead link outscored a verified `regional` one. As a multiplier it
cannot: the strongest possible unevidenced application scores **24.0** and is
rejected — just under the 25 review floor, by construction.

**2. Missing is zero here — the opposite of `matching.py`, on purpose.** That
module renormalises weights over the analytics it could measure, because the
athlete does not control whether Instagram returned data. Everything on an
application form is the reverse: the applicant chooses what to supply.
Renormalising over self-reported fields makes *withholding raise the score* — a
blank competition level handed its whole weight to tenure and scored 100 in the
first draft. **Renormalise over what the system could not measure; never over
what the applicant chose not to write down.**

**3. Competition level is read against its own sport.** "Regional" in football
sits under several professional tiers; in padel it is near the competitive
ceiling. The tilt uses the agent-density column from [08](08-sport-index.md).

---

## Formulas

### Athlete credibility

```
level    = LEVEL_BASE[l] × (1 + 0.12 × (0.45 − agent_density(sport)))
           LEVEL_BASE = { local .35, regional .58, national .78, international .92 }

tenure   = min(1, max( years / 8 , years / (age − 10) ))

E        = 1.15 verified | 0.70 pending | 0.55 unverified | 0.10 rejected
           0.25 when no proof was supplied at all
           (a rejected check dominates the absence of one — see stress test #2)

C        = min(100, 100 × (0.85·level + 0.15·tenure) × E)
```

`tenure` takes the kinder of two readings because the failure modes point
opposite ways: raw years is an age proxy that penalises the 16- and
17-year-olds the platform deliberately onboards ([05](05-product-gaps.md)),
while pure share penalises the adult who started late. Eight seasons is full
marks either way. The start age of 10 has to sit above `MIN_AGE − 8` or the
share reading never binds for anyone old enough to hold an account.

### Decision

Order matters — disqualifications cannot be outscored, and the social score
runs last and only ever moves a case towards a human.

```
checked = own proof verified  OR  nominated by a verified club

proof rejected                          → rejected     ┐ hard disqualifications,
age < 16                                → rejected     ┘ and they run first
competition level missing               → pending      (not a decision at all)
max(C, club_floor) ≥ 55, age known:
        and checked                     → admitted
        and not checked                 → review       (evidence_not_checked)
                                  ≥ 25  → review
S ≥ 70 and C ≥ 25                       → review       (never higher)
otherwise                               → rejected
```

The order of the first three lines is load-bearing. `pending` used to sit above
the age gate, so a known 15-year-old who left one box blank was held on file
rather than refused (stress finding 6).

Nothing auto-admits on evidence nobody has opened. `pending` means a link was
supplied, not that it says what the applicant says it says — and at 0.70 a large
enough claim clears the line unaided (see stress finding 3).

### Club legitimacy

Scored on what makes a club *real*, not on what makes it marketable. A club
with a large Instagram is more valuable, not more legitimate; reach belongs in
package pricing.

```
w = { registration .30, federation .30, longevity .15, structure .15, roster_proof .10 }
L = min(100, 100 × Σ wᵢ·vᵢ × E)

verified ≥ 65 AND own proof checked · review ≥ 35 · else rejected
nomination_floor = 0.75 × L, and only when verified
```

The `AND` is load-bearing. Every field on a club application is a self-reported
string; filled in perfectly they reach claim 100, which at the `pending`
multiplier is 70 — over the bar. Without it a fabricated club verifies itself and
starts nominating (stress finding 4).

### Nomination — a floor, not a bypass

"Verified club nominates → athlete auto-accepted" makes the club a fraud
multiplier: verify one club, mint five hundred athletes. Three properties stop
that:

- **A nomination raises credibility; it cannot supply identity.** No club can
  state someone else's date of birth, so the 16+ gate still cannot be cleared by
  a third party and a nominated athlete who submitted nothing stays `pending`.
  Minting a thousand athletes costs a thousand completed forms.
- **Bounded by the roster the club declared.** `registered_athletes` is also the
  nomination budget, which makes inflating it a checkable claim rather than free
  headroom.
- **Revocable, because `admitted_via` is recorded.** De-verifying a club returns
  to `review` exactly those athletes whose own credibility was below the admit
  line. Anyone who stood on their own evidence is untouched. Review, not
  rejection: losing your supporting evidence is not being caught lying.

At a 0.75 transfer only clubs scoring ~73+ can carry an athlete over the line
unaided, so club strength propagates proportionally rather than as a switch.

A nomination is also a **ratchet**: it can raise a listing, never lower one.
Without that, a club vouching for a healthy listed athlete would knock them to
`draft` on a `pending` verdict — a third party's action costing someone their
standing.

---

## Matching

The existing eight-component model in `matching.py` is unchanged. What changed
is the shape around it.

**Hard constraints moved into retrieval.** A weighted blend is compensatory by
construction, so a strong audience fit would outscore a failed brand-safety or
verification check — the one trade no brand wants made on its behalf. Anything a
sponsor states as a *must* is now a filter in `candidates()`, where it cannot be
outscored. `require_verified_athletes` is the first instance and it is what ties
admission to matching: a risk-averse brand can require athletes whose
participation was actually checked.

**Congestion is surfaced, not silently corrected.** The problem "stable matching"
reaches for is real — the top few athletes absorb most offers — but Gale–Shapley
solves two-sided preference with quotas and exclusivity, and sponsorship has
none of those properties: a sponsor offers to many, an athlete accepts many, the
binding constraint is budget rather than exclusivity, and the market clears
asynchronously. Imposing it would mean batching offers and forbidding an athlete
a second deal. Instead a match now carries `open_offers`, and at three or more
says so in its caveats. Telling the sponsor lets them diversify; quietly
reordering their results decides for them.

**The slate is logged.** This is the highest-value recommender work available
today, and it is not a model.

> Offers on their own are a biased sample: they record what a sponsor chose
> without recording what they chose *from*. Nothing recovers, later, the
> candidates that were never written down.

`matching.ran` now records every candidate shown, its rank, its score, its
component vector, and the weights in force. One row per matching run, and
unrecoverable if skipped — the classic selection-bias trap, and the reason most
in-house rankers cannot be evaluated off-policy after the fact.

---

## Why there is no learned ranker yet

Learning-to-rank needs labels. Until the measurement work in
[05](05-product-gaps.md#campaign-measurement--shipped) shipped there were
literally zero recorded campaign outcomes; there are now non-zero and they will
stay small for a while. Proposing an LTR model today is proposing a model with
an empty training set, and [09](09-analytics-strategy.md) already sequences this
correctly: Phase 2, seed → Series A, one analyst-engineer.

What is being accumulated in the meantime, and what it becomes:

| Logged now | Event | Becomes |
|---|---|---|
| Candidate slate: who was shown, rank, score, components, weights | `matching.ran` | Features + exposure, for off-policy evaluation |
| Offer sent | `deal.created` | Positive label (sponsor chose) |
| Accept / decline / no answer | `deal.responded` | Response-likelihood label |
| Delivered reach, engagement, variance vs projection | `deal.completed` | The **outcome** label that actually matters |
| Admission inputs and verdict, with `policy_version` | `admission.decided` | Back-test set for retuning the gate |

**The trigger to move from rules to a model** is roughly 500 completed
(campaign, athlete, outcome) triples with at least 50 distinct sponsors — below
that a learned ranker fits one buyer's taste and calls it a market. The first
version should be a gradient-boosted ranker on the components already logged,
shipped behind an A/B against the current weights, judged on realised delivered
reach per euro rather than on offer rate.

Until then the hand-set weights have one property a model would not: every score
decomposes, in the UI, to the inputs behind it. That is worth keeping for as
long as sponsors are being asked to trust a marketplace they have no history
with.

---

## Stress test

`scripts/admission_stress.py` sweeps the discrete input space exhaustively
rather than spot-checking: 8,960 applications × the questions below. It found
two failures that the hand-written test cases did not — two more turned up only
by driving the running API, and a sixth appeared the moment the harness itself
was widened to cover what those escapees had exposed. The honest reading is that
sweeps, live runs and hand-written cases each catch a different class, and none
of the three substitutes for the others.

| Sweep | Checks | Result |
|---|---|---|
| Monotonicity | 21,120 ordered pairs | more evidence, a higher level or a longer career never lowers a score |
| Withholding | 89,600 blanked variants | no field, alone or in pairs, is better left blank |
| Clubs | 35,840 applications and variants | monotonic, withholding-proof, and no club verifies itself |
| Decision surface | 7,200 joint points | every invariant holds across credibility × proof × age × social × floor |
| Bounds | 8,960 scores | in range, and stable across repeated evaluation |
| Forgery cost | 8,960 applications | **0** admitted on anything short of a *checked* proof |
| Nomination | floors, laundering, compounding | a club's word never compounds and never admits alone |
| Social score | 8,960 applications | never turns a non-admission into an admission |

The middle three rows were added *after* findings 3 and 4, because a harness
that misses the class of bug it exists to find is itself the defect. Clubs had
six hand-picked cases where athletes had thousands, and the decision function
was only ever swept one axis at a time — which is exactly where both escapees
lived. Widening it immediately produced finding 6.

### Finding 1 — an incomplete form was a softer landing than an honest one

13,992 combinations where blanking a field *improved* the outcome. Routing an
unanswerable form to `review` made it strictly better than an honest weak claim,
because a queued case can still be admitted by a human and a rejected one
cannot. That hands every applicant heading for rejection a strategy: leave a box
empty.

**Fix:** an incomplete application returns `pending` — not a lenient decision but
the *absence* of one. It occupies no reviewer and confers nothing, so stalling
gains nothing.

### Finding 2 — deleting failed evidence scored better than leaving it

With a rejected check at 0.10 and no proof at all at 0.25, withdrawing a link
that had been checked and failed *raised* credibility. Combined with the
endpoint resetting `proof_status` on every re-submission, that made "get caught,
then delete the evidence" a strictly better move than never having lied.

**Fix, in two places:** a rejected status now dominates the absence of proof
inside the scoring function itself, and a failed check is sticky across
re-submission. A failed verification is a finding about the applicant, not about
the URL, so only a reviewer can clear it.

### Findings 3 and 4 — nothing required the evidence to have been *looked at*

These two came from driving the running API rather than from the sweep, which
had missed them because its own definition of "unevidenced" wrongly counted a
queued link as evidence.

- An unchecked `international` claim scored **62.4** at the `pending` multiplier
  and was admitted outright.
- A fully fabricated club — plausible registration number, federation id,
  founding year, team count, roster URL, none of them opened — scored **70**,
  cleared the 65 bar, and could verify itself and begin nominating.

**Fix:** admission requires one *checked* source, either the applicant's own
proof or a verified club whose paperwork was itself checked; and `verified` on
the club side now requires that somebody verified something. The sweep's
definition was corrected too, so it would now catch this class on its own.

A fifth defect, found the same way: there was no ops endpoint to record a check
against a *club's* roster page, so the verified state was unreachable — a club
re-submitting its own form resets the proof to `pending` by design, which is
correct, and left no forward path at all.

### Finding 6 — an unfinished form outranked a legal disqualification

Found by the widened sweep, on its first run. `incomplete_application` was
checked *before* the age gate, so a known 15-year-old who left the competition
level blank landed in `pending` rather than being refused. The function's own
docstring promised that disqualifications run first; the code did not. Holding a
minor on file in a pending state, inviting them to finish a form they can never
pass, is the opposite of what the age model exists for.

**Fix:** both hard disqualifications — a failed proof check and being under 16 —
now run above the incompleteness check. An adult with the same unfinished form is
still simply unfinished, and an applicant whose age is unknown still cannot be
disqualified on age.

A seventh report in that run was **not** a defect: 594 "credibility exceeds claim
× max multiplier" failures were the harness comparing two independently rounded
figures. The tolerance now accounts for the display precision, and the check is
stated against the multiplier constant rather than a literal. Worth recording,
because a stress harness that cries wolf gets switched off.

---

## What the policy costs in humans

Under an assumed applicant mix — an assumption, not a measurement; replace it
with real intake data the moment it exists:

| Admit threshold | admitted | review | rejected | pending |
|---|---|---|---|---|
| 45 | 20% | 25% | 40% | 15% |
| **55 (current)** | **20%** | **25%** | **40%** | **15%** |
| 65 | 5% | 40% | 40% | 15% |

**250 manual reviews per 1,000 applicants — about 17 hours per 1,000 at four
minutes each.**

The composition matters more than the level. **Every case in that queue is there
waiting for a proof link to be looked at, not because anyone is unsure about the
athlete.** A `pending` link caps credibility at 0.70×, which structurally holds a
genuine regional athlete below the admit line until a human opens a URL.

That makes the highest-leverage ops investment obvious and small: **fetch the
roster or results page and look for the applicant's name.** Automating that one
step converts most of the review queue directly into admissions and leaves
humans only the genuinely ambiguous cases. It is also the only part of this
design that needs the public internet, which is why it is specified rather than
built here — every connector in this codebase is mocked.

The threshold is otherwise on a plateau between 45 and 60, which is a comfortable
place to sit. The nearest edge is verified regional football at **60.2**; raising
`DENSITY_SENSITIVITY` much above 0.12 would push it under the line, so that
constant should not be retuned without re-running the sweep.

---

## Built, and not

| | State |
|---|---|
| Credibility, legitimacy, nomination, decisions | **Built** — `admission.py` |
| Applications, review queue, proof review, revocation | **Built** — `routers/admission.py` |
| Hard retrieval filters, congestion, slate logging | **Built** — `matching.py` |
| Adversarial sweep | **Built** — `scripts/admission_stress.py` |
| Athlete eligibility, club eligibility + nomination, ops review queue | **Built** — see below |
| Automated proof-link checking | **Specified** — needs live HTTP; see above |
| Learned ranker | **Deliberately deferred** — no labels yet |
| Topic embeddings for narrative fit | **Deferred** — needs real post text and a model dependency |

---

## The interface

Three surfaces, and one rule holding them together: **show the working.** The
scorer returns components, weights, the evidence multiplier and a
machine-readable `rule` precisely so the interface can turn a verdict into
something the applicant can act on. A gate that returns a number without the
arithmetic behind it is a gate nobody can appeal, and refusing to ship that is
the same discipline the marketability scores already follow.

| Route | Who | Shows |
|---|---|---|
| `/athlete/application` | athlete | Credibility as the headline figure, the verdict in plain words, where it sits against the admit line, what counted for and against, and the component-by-component arithmetic |
| `/club/eligibility` | club | The same for legitimacy, plus nomination against the declared roster |
| `/admin/review` | ops | The queue, built around one action: open the link, say whether it names the applicant |

Three things the interface is deliberate about:

- **Rule codes become sentences.** `evidence_not_checked` reads "Your claim
  clears the bar — we just have not opened your proof link yet." The wording
  lives in the client so it can change without touching policy.
- **The nomination panel says what a nomination cannot do**, before the club
  spends its budget: nominees sit at `pending` until they complete their own
  form, because no club can supply someone else's date of birth. Without that,
  a club nominates twenty people and wonders why none are listed.
- **The threshold markers sit at their real positions** on the 0–100 rule rather
  than flush left and right. Flushing them told an applicant at 15 that 55 was
  the end of the bar.

Body copy on the tinted verdict panels is `ink-2`, not the semantic colour:
measured against its own 10% tint it reads 6.67–7.64:1 across both themes, where
`ink-3` would have been 4.00–4.59 and failed AA on all three tones.
