# 08 — Sport Opportunity Index

**714 country × sport pairs** — 34 countries (EU-27 + UK, US, Canada, Mexico,
Brazil, Australia, India) × 21 sports. Built by
[`sport_index.py`](sport_index.py) on data in [`sport_data.py`](sport_data.py).

```bash
python business-plan/sport_index.py                     # top opportunities
python business-plan/sport_index.py --country Spain     # one country ranked
python business-plan/sport_index.py --sport padel       # one sport across countries
python business-plan/sport_index.py --athlete Spain football   # content guidance
python business-plan/sport_index.py --sponsor Spain padel      # tier visibility
python business-plan/sport_index.py --coverage          # data confidence audit
```

**There is no launch sport.** The index is *context*, not a gate. Early athletes
are judged on everything — audience, consistency, professionalism, willingness
to publish — and their sport is one input among those. What the index does is
tell us, and them, how to read their numbers.

---

## Method

Authoring 714 numbers by hand would be unmaintainable and indefensible, so the
matrix is **decomposed**:

```
participation(country, sport) = activity_index(country) × base_participation(sport) × region_multiplier
fandom(country, sport)        = media_index(country)    × base_fandom(sport)        × region_multiplier
```

34 country rows + 21 sport rows + multipliers only where a region genuinely
departs from the world. Add a country, and every sport is scored for it.

### The five signals

| Signal | Weight | What it asks |
|---|---|---|
| **supply** | 0.25 | How many athletes exist to sign |
| **demand** | 0.20 | How many people might pay |
| **gap** | 0.25 | How much value is unclaimed (1 − agent density) |
| **appetite** | 0.15 | Do the fans *do* the sport? |
| **concentration** | 0.15 | Is this sport disproportionately strong here? |

**`appetite` does the conceptual work.** `participation / (participation + fandom)`
asks whether a sport's followers are practitioners or spectators. A trail
runner's audience is other trail runners who want training knowledge and will
pay for it. A football fan watches and does not want a training plan.
Participatory sports already have the content habit — athletes publish training
logs for free on platforms that pay them nothing — so the paywall is the only
missing piece.

**`concentration` is what a global average erases.** Padel in Spain and padel in
Poland are not the same proposition. Without this signal, running dominated
every country and padel never surfaced; with it, padel/Spain is the 5th best
pair in the world.

Supply and demand are **log-normalised against the matrix's own range**, learned
at runtime. Change the data and the scale follows — no hand-tuned ceilings.

---

## Results

### Spain

| Sport | Score | Segment | Audience |
|---|---|---|---|
| **padel** | **78.2** | niche | practitioner |
| **running / trail** | **74.9** | niche | practitioner |
| fitness / gym | 71.1 | niche | practitioner |
| cycling | 66.3 | niche | practitioner |
| swimming | 65.7 | niche | practitioner |
| climbing | 57.6 | niche | practitioner |
| athletics | 53.1 | popular | mixed |
| football | 53.1 | popular | spectator |
| triathlon | 52.6 | niche | mixed |

Padel first, endurance second — which is where intuition put them, now derived
rather than asserted.

### Top pairs globally

| # | Sport | Country | Score |
|---|---|---|---|
| 1 | running / trail | Finland | 80.6 |
| 2 | running / trail | Sweden | 80.5 |
| 3 | running / trail | Denmark | 80.0 |
| 4 | running / trail | Australia | 78.9 |
| **5** | **padel** | **Spain** | **78.2** |
| 6 | running / trail | United Kingdom | 77.7 |
| 12 | padel | Finland | 75.7 |

**Niche is 57% of all pairs and 100% of the top 50**, and every one of the top
50 is a practitioner audience. That is the strategy falling out of the data
rather than being imposed on it.

The Nordics outrank Spain on endurance because Eurobarometer puts them far ahead
on participation (Finland 8% never exercise, vs an EU average of 45%). Worth
knowing for market two.

---

## Three product uses

### 1. Athletes — content guidance

The athlete sees their audience type and what converts for it. Not "your sport
is niche" — that is a positioning risk and tells them nothing useful — but
**what to publish.**

```
$ python sport_index.py --athlete Spain football

Your followers watch your sport; they do not play it. (spectator, appetite 0.16)
They pay for proximity and personality, not for instruction.

Publish   Matchday and travel access · Personality and off-season life ·
          Reactions and commentary · Club and teammate content
Monetise  Access-led. Tips and unlocks around fixtures outperform subscriptions.
Avoid     Training plans — this audience does not want them, and low conversion
          will read as low demand when it is a content mismatch.
```

That last line is the valuable one. Without it, a footballer publishes training
content, converts badly, and concludes the platform does not work.

### 2. Sponsors — tiered visibility

| Tier | Normalised | Raw | Components |
|---|---|---|---|
| Scout Free | yes | – | – |
| Scout Pro | yes | yes | – |
| Scout Agency | yes | yes | yes + API |

Lower tiers see the sport-relative percentile only; higher tiers also see the
raw absolute and the index components. This is an upsell ladder, but the
constraint matters more than the ladder: **normalisation must never hide its
basis.** A percentile is shown as *"92nd percentile among padel athletes in
Spain, n=340"*, never as a bare number. The product's entire claim is that a
score decomposes, and a normalisation that cannot be opened would break it.

### 3. The scoring engine — the change that matters most

`audience_scale` is currently `logband(followers, 2, 7)`, and **sport is not an
input to any dimension**. A trail runner with 25k followers scores identically
to a footballer with 25k, though 25k is elite in one and irrelevant in the
other.

**The engine under-rates exactly the athletes the strategy targets.** The fix is
a sport-relative percentile presented alongside the absolute figure — both
visible, because both are true and they answer different questions. This is the
highest-leverage product change in the plan: it makes the algorithm agree with
the go-to-market.

---

## Data provenance and refresh

| Layer | Source | Confidence | Refresh |
|---|---|---|---|
| Country activity index | **Special Eurobarometer 525** (2022) | 6 countries measured, 28 estimated | Every ~4 years, free |
| Sport licences | National federations (CSD Spain, DOSB Germany…) | Not yet ingested | Annual, free |
| Padel | **FIP World Padel Report 2025** | measured | Annual |
| Fandom index | Reasoned estimates | estimate | **Replaced by Stride's own data** |
| Agent density | Reasoned estimates | estimate | Revised from observed deal flow |

`--coverage` audits this at any time: today **6 of 34 countries are measured**
and 28 are estimates. That ratio is the honest state of the dataset, and it
improves in a specific way.

**The index becomes self-improving.** Fandom and agent density are the weakest
inputs today and are exactly what Stride will measure directly: once connectors
are live, the platform observes real engagement per sport per country, and once
deals flow it observes how many athletes arrive already represented. **The
estimates are placeholders for data the product generates as a by-product of
operating** — which is also why the index is defensible as a moat rather than a
spreadsheet anyone could copy.

### Honest limitations

- **28 of 34 country activity indices are estimates.** They sit inside the
  Eurobarometer distribution and are the right shape, but they are not measured.
- **Fandom is the weakest layer throughout**, and it drives `demand` and
  `appetite` — the signal the whole content-guidance feature rests on. First
  candidate for replacement with real data.
- **Regional multipliers are coarse.** Sweden and Denmark share "nordics"
  despite different padel adoption.
- **Agent density is a judgement**, not a measurement, and it carries the
  heaviest single weight (0.25) alongside supply.
