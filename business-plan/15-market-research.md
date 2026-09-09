# 15 — Primary Research

*ESADE outline §5.1.4. Two strands of qualitative primary research: one expert
interview inside Olympic broadcasting, and conversations with athletes in the
segment the plan targets. This section reports what was said, what it changed,
and what it does not settle.*

> [!note] Two details to confirm before submission
> The number of athletes spoken to is written below as "several"; replace it
> with the exact count. The Íñigo interview date should also be stated. Both are
> the kind of specific an examiner will ask for.

---

## 15.1 Method, and what it can support

| | Strand A | Strand B |
|---|---|---|
| **Who** | Íñigo Cristóbal Losada, AI Lead at olympics.com | Rugby league players in Lebanon; one athlete competing at Asian level in CrossFit |
| **Why them** | A decade inside Olympic broadcast operations and rights-holder relationships | They *are* the target segment, not a proxy for it |
| **Format** | Unstructured conversation | Unstructured conversations |
| **Sample** | 1 | Several |

**This is a convenience sample and it is reported as one.** Both strands come
from the founder's own network. The findings below are directional and
qualitative; none of them is a statistically representative measurement, and the
plan does not treat them as one. What a sample like this *can* do is two things
a survey cannot: surface a mechanism nobody thought to ask about, and change a
product decision. Both happened.

> [!important] The Lebanon question, answered before it is asked
> The athletes interviewed compete in Lebanon. The plan launches in **Spain**.
> That gap is real and worth confronting directly.
>
> The finding those conversations produced is **structural, not national**: in a
> sport with no agent layer, there is no route from having an audience to
> earning from it. The sport index in [08](08-sport-index.md) measures agent
> density across 714 country × sport pairs and finds that absence is a property
> of *niche sports* rather than of any one country.
>
> Be precise about what the index does and does not contain: **neither Lebanon
> nor rugby league is in it.** It covers 34 countries and 21 sports, and an
> examiner checking against [08](08-sport-index.md) would find both missing.
> What transfers is the mechanism, not a cell in the matrix — where no agent
> layer exists, no route runs from audience to income — and the index is the
> evidence that this condition is set by a sport's economics rather than by
> its geography.
>
> What the Lebanese sample **cannot** support is anything about Spanish
> willingness to pay, sponsor budgets, or market size. None of those claims rests
> on it. The Spanish market sizing is desk research, and it is labelled as such.

---

## 15.2 Expert interview — Olympic broadcasting

**Íñigo Cristóbal Losada** is AI Lead at olympics.com (Olympic Channel
Services), following eleven years at Olympic Broadcasting Services, where he was
Broadcaster Services Manager through Tokyo 2020 and Beijing 2022 and managed
venue broadcast operations at the Tokyo Paralympic Games. He holds an Executive
Master in Digital Business from ESADE. He discussed the idea from the
perspective of the Olympic Channel in Europe.

**The headline: he liked it.** Three pieces of substantive advice followed, and
two of them changed the plan.

### Finding 1 — Phase it. Content first, sponsorship second.

His advice was to prioritise the content side, and to roll out the sponsorship
and business layer as real data accumulated or once a reasonable athlete base
existed. He suggested the two could even be treated as separable products.

**Effect on the plan: confirmatory.** The revenue thesis already sequences fan
monetisation ahead of sponsorship, and [01](01-revenue-model.md) states that
fan revenue leads and funds the early years while sponsorship compounds behind
it. The interview independently reached the same ordering from an operator's
perspective rather than a financial one.

It also exposes an inconsistency worth naming: **the deployed demo shows the
sponsorship engine, not the fan product.** That is deliberate, because the
matching engine is what proves the analytics are real, but it means the thing a
viewer clicks is the second-phase product. The build sequence in
[12.11](12-operations-plan.md) corrects the order; the demo has not caught up.

### Finding 2 — Open it to everyone, but filter it

The idea was originally pitched to him as a product *for the IOC*, in which only
Olympic athletes could participate. **He rejected that framing.** His position:
open registration to everyone, but build a filtering mechanism so that not
anyone can register as an athlete.

> [!important] This is the finding that changed the product
> The **admission gate** exists because of this conversation. It is not a
> feature that was designed and then justified; it is a direct response to
> expert advice that a closed, elite-only platform solves the wrong problem
> while an unfiltered open one has no sponsor-side value at all.
>
> What was built as a result, and is live in the demo today: an application
> flow with automated proof-checking, a human review queue, versioned
> marketability scoring, and club nomination as a second admission route.
> **Nothing self-verifies** — a club scoring above the verification bar still
> waits for a person to open its roster page, and a rejected proof cannot be
> cleared by re-submitting the form. The full model is in
> [11](11-admission-and-matching.md).
>
> The admission rate the model plans for rises from **20.0% in Y1 to 30.5% by
> Y7** as the funnel improves, which is a filter, not a formality.

This also settled the market-entry question. An IOC-only product would have
inherited the IOC's athlete population: elite, already represented, and largely
already monetised. The segment with the actual problem sits below that tier,
which is where the plan now starts.

### Finding 3 — Look at Athlete365, and at partnership

He pointed to the IOC's own athlete programmes, in particular **Athlete365**,
as both a reference and a possible future partnership route.

Athlete365 is the IOC's athlete community brand. Its **Business Accelerator**,
run with Alibaba.com, supports Olympians, Paralympians and elite athletes
*transitioning to life after sport*, through online modules on business
fundamentals, financial planning, branding and marketing, plus mentoring, with
prizes including promotional packages and Alibaba.com credit.

**Read carefully, this is adjacent rather than competitive**, and the distinction
matters:

| | Athlete365 Business Accelerator | Stride |
|---|---|---|
| Who | Olympians and elite athletes | The tier below, where no agent exists |
| When in a career | Transitioning **out of** sport | **During** the competitive career |
| What it provides | Education, mentoring, credit | Revenue, from fans and sponsors |
| Business model | IOC-funded programme | Marketplace take rate |

That the IOC funds a programme at all is evidence the problem is recognised at
the top of the sport. That the programme teaches entrepreneurship to retiring
elite athletes confirms it is not addressing the athlete this plan targets.

**As a partnership**, the relevant asset is credibility and reach into national
federations, which is exactly the channel [14.3](14-legal-and-growth.md) plans
to open at Y3. It is listed as an opportunity, not as a dependency.

---

## 15.3 Athlete interviews — the segment itself

Conversations with rugby league players in Lebanon and with an athlete
competing at Asian level in CrossFit. The founder is capped by the Lebanese
national rugby team, which is how this access exists and why the conversations
were candid rather than performative.

### Finding 1 — Current earnings are zero, not low

Not "modest", not "inconsistent". **Nothing.** The athletes spoken to earn no
income from their sport or their audience.

This matters for the plan's framing: the alternative to Stride for this athlete
is not a worse deal. It is no deal. That is the market-creation argument in
[06](06-market-strategy.md), stated by the people it describes.

### Finding 2 — The inequity is visible, and it is felt

The comparison that came up unprompted: **influencers producing far less
demanding content earn more than competing athletes do.** The grievance is not
that sport should pay more in the abstract. It is that the monetisation
infrastructure available to a lifestyle creator has no equivalent for someone
whose content is a training block and a competitive record.

### Finding 3 — Sponsorship arrives despite the sport, not because of it

One athlete does receive sponsorship. **He does not receive it as a rugby league
athlete.** There is no route by which the sport itself produces the commercial
relationship, because no platform exists to carry it and no mechanism exists for
a brand to find him through it.

This is the disintermediation thesis observed from the supply side: the
sponsorship market is not competitive here, it is **absent**.

### Finding 4 — The suppression loop

The strongest finding, and the one that changes how the opportunity should be
sized:

> Athletes do not invest in building an audience, because there is no return on
> doing so. As one put it: people are not going to spend time setting up social
> media and building followers purely around their sport if nothing comes back.

**The absence of monetisation suppresses the supply of audience in the first
place.** That reframes the addressable market: the plan's funnel in
[03](03-financial-model.md) counts athletes who *already* have ≥5,000 followers,
which measures the market under current incentives. If a credible route to
income exists, some athletes below that threshold cross it who otherwise never
would.

The plan does **not** claim that expansion. The TAM stays measured on today's
follower counts, and the sizing is deliberately the conservative reading. But it
is worth stating that the honest error direction here is *understatement*, and
that the mechanism for expansion is exactly the one the product supplies.

---

## 15.4 What the research settles, and what it does not

**Supported by primary research:**

- Niche-sport athletes at this tier earn nothing from their audience, and
  experience that as a structural absence rather than a pricing problem
- There is no mechanism for brands to find them through their sport
- An open platform with a real admission filter is the right shape, per an
  expert with a decade inside Olympic broadcast
- Content and fan monetisation should lead; sponsorship should follow the data

**Not supported, and not claimed:**

- **Will fans actually pay?** No interview answers this. It is the assumption
  the whole plan rests on, it is named as such in [07](07-open-questions.md) as
  risk R1, and only three months of real subscription data from one anchor
  athlete resolves it. That is the pre-seed gate, and it is a gate precisely
  because the research does not clear it.
- **Sponsor-side willingness to pay.** No sponsor or brand-side interviews have
  been conducted. This is the largest hole in the research and is acknowledged
  rather than papered over.
- **Spanish market specifics.** The interviews are Lebanese; the launch market
  is Spain. The structural finding transfers (§15.1); the pricing and budget
  figures do not, and none of them rests on this research.

---

## 15.5 Research roadmap

In priority order, and sized to what actually changes a decision:

| Priority | Research | Why it matters | Effort |
|---|---|---|---|
| **1** | **6–10 sponsor-side interviews** — regional brands, sports nutrition, local retail | The only completely untested side of the marketplace. Without it, the demand side is desk research alone | 2 weeks |
| **2** | Structured athlete survey, n ≥ 30, via the club channel | Converts the qualitative findings into something defensible. Ask about current income, brand approaches, and willingness to accept a 15% take | 3 weeks |
| **3** | Spanish athlete interviews, 5–8 | Tests whether the structural finding holds in the launch market specifically | 2 weeks |
| **4** | Athlete365 / federation exploratory contact | Partnership route, and a credibility signal for the club channel | Opportunistic |

The pre-seed gate does what none of the above can: it measures whether fans pay,
with real money, over three months. Every item here reduces uncertainty around
that test. None of them substitutes for it.
