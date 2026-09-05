<p align="center">
  <img src="docs/media/landing.jpg" alt="Stride — where athletes, sponsors and audiences meet on evidence" width="820">
</p>

<h1 align="center">Stride</h1>

<p align="center">
  <strong>The sponsorship marketplace where every number can be traced back to the post that produced it.</strong>
</p>

<p align="center">
  Athletes own evidence-based marketability analytics and publish to the audience behind them.
  Sponsors match campaign briefs against the athlete pool with fully decomposable scoring.
  Clubs sell packages. Supporters follow for free, or subscribe for what sits behind the lock.
</p>

<p align="center">
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-1f2937?style=flat-square&logo=python&logoColor=FFB020">
  <img alt="React 18" src="https://img.shields.io/badge/react-18-1f2937?style=flat-square&logo=react&logoColor=FFB020">
  <img alt="FastAPI" src="https://img.shields.io/badge/fastapi-0.11x-1f2937?style=flat-square&logo=fastapi&logoColor=FFB020">
  <img alt="Tests 359 passing" src="https://img.shields.io/badge/tests-359%20passing-1f2937?style=flat-square&logo=pytest&logoColor=3FCF8E">
  <img alt="LLM cost zero" src="https://img.shields.io/badge/LLM%20inference%20cost-%240-1f2937?style=flat-square">
  <img alt="Status: first product draft" src="https://img.shields.io/badge/status-first%20product%20draft-1f2937?style=flat-square">
</p>

---

## The problem

Sponsorship is priced on assertion. An athlete says they have reach; a brand takes the number on
faith or pays an agency to guess. Nobody on either side of the table can decompose the price.

Stride replaces the assertion with a measurement that shows its working. Marketability is computed
from connected platforms through a **versioned formula set**, and every score carries the inputs,
the coverage, and the confidence behind it. A sponsor who disagrees with a score can open it and see
precisely which posts produced it.

**The commercial claim follows from the technical one:** a marketplace whose prices are explainable
is one where both sides can negotiate against evidence instead of reputation.

---

## Run it

Two terminals. The database seeds itself on first run.

```bash
# 1. API — uv manages Python                    http://127.0.0.1:8490
uv run stride serve

# 2. Web — from apps/web, first time: npm install    http://localhost:5173
npm run dev
```

Demo accounts, password `stride123`:

| Role | Email | Lands on |
|---|---|---|
| Athlete | `athlete@demo.stride` | Own analytics, platform connections, deal inbox |
| Sponsor | `sponsor@demo.stride` | Campaign briefs, ranked matching, deal pipeline |
| Club | `club@demo.stride` | Roster, sponsorship packages, commitments |
| Supporter | `fan@demo.stride` | Discovery, a following feed, subscriptions, polls and fan walls |
| Admin | `admin@demo.stride` | Audit log and resilience drill |

---

## What it looks like

The direction is a **stadium results board**, not a SaaS dashboard: enormous condensed numerals
against 11px tracked caps, one accent (signal amber) for emphasis, semantic colour held separate
for state, and a single orchestrated motion moment on load. Written down in
[`apps/web/DESIGN.md`](apps/web/DESIGN.md) — and enforced by
[`scripts/design_audit.py`](scripts/design_audit.py), which fails a build if a semantic colour
drops under 4.5:1 where it is actually used, if a colour is written outside the token layer, or
if a type size appears that is not on the scale.

### Matching that decomposes

Every match is a weighted sum a sponsor can take apart. Bar length is each component's
**contribution** to the score — component × the weight actually applied — so the chart ranks what
really drove the match, not which raw number happened to be largest. The reasons beside it are
generated from the same arithmetic.

<p align="center">
  <img src="docs/media/score-composition.jpg" alt="Score composition ranked by contribution, with the component times weight arithmetic and plain-language reasons" width="820">
</p>

### The athlete's own board

The same numbers the sponsor sees. Information symmetry is deliberate: an athlete negotiating
against their own analytics is the point of the product.

<p align="center">
  <img src="docs/media/athlete-dashboard.jpg" alt="Athlete dashboard with marketability board and ranked dimensions" width="820">
</p>

### Where the audience actually is

Audience share as a choropleth rather than bubbles on centroids — filling the country says the
same thing with no placement problem, because the shape *is* the label. A country nobody in this
audience lives in is still drawn, plainly: that is a different statement from not drawing it.
The chip is not decoration. Platform connectors are mocked in this build, and **every surface that
shows an audience says so**.

<p align="center">
  <img src="docs/media/audience-map.jpg" alt="Audience by country as a choropleth, with a simulated-audience chip and the ranked country table" width="820">
</p>

### The page an athlete gives their audience

Cover and avatar are generated from the name until the athlete uploads their own. Follow and
subscribe are different relationships, not two words for one: following is free and public,
subscribing is what opens the lock. The rate card and the score are stripped from this page for
anyone who is not a sponsor, a club or an admin — an athlete previewing their own page sees
exactly what a visitor sees.

<p align="center">
  <img src="docs/media/athlete-public.jpg" alt="An athlete's public page: generated cover art, verified badge, membership card and platform links" width="820">
</p>

### One wall, two kinds of post

Posts an athlete writes sit beside the platform activity their connected accounts produce, and the
platform items carry a very light wash of that platform's own colour — Instagram purple, TikTok
cyan, YouTube red — at 5–7% behind a coloured edge. The label says the platform too, so the colour
is never the only carrier. Locked posts show their title, their tier and what is behind them, and
nothing else: no thumbnail leaks through the blur.

<p align="center">
  <img src="docs/media/creator-feed.jpg" alt="A wall mixing the athlete's own posts with platform activity, each tinted by platform" width="820">
</p>

<details>
<summary><strong>More screens</strong> — ranked matching, directory, account, operations</summary>

<br>

**Ranked matches against a campaign brief** — coverage stated on every row, because a score from
one platform is not the same claim as a score from three

<img src="docs/media/campaign-matches.jpg" alt="Campaign matches ranked with coverage chips" width="820">

**Public athlete directory, sortable on the measurement**

<img src="docs/media/directory.jpg" alt="Athlete directory with marketability, rate card and analytics coverage columns" width="820">

**The account behind the profile** — address confirmation, password, sessions, export and deletion

<img src="docs/media/account.jpg" alt="Account settings: confirmed email, password change, sessions and data controls" width="820">

**Operations** — the moderation queue, the audit log and the resilience drill

<img src="docs/media/operations.jpg" alt="Admin operations view with the report queue and chaos controls" width="820">

</details>

---

## How it works

```
apps/web/            React 18 · Vite · TS · Tailwind — 32 routes, each naming
                     its own access rule (public, or guarded by role)
apps/api/            FastAPI — auth + RBAC, routers per bounded context,
                     matching engine, JSON logs, /metrics, probes, chaos layer
packages/creatorlens/  the analytics engine, built first and vendored:
                     connectors → ingestion → KPIs → versioned scoring
infra/               Dockerfiles, compose, K8s manifests, Supabase migration + RLS
docs/                architecture · ui-architecture · product · costs · runbook
```

**The analytics core is a separate engine.** `packages/creatorlens` was built before the product
around it and is integrated, not reimplemented — connectors are mock today behind the production
interface, so going live changes one class per platform and nothing downstream.

**Five dimensions, each with its evidence:** audience scale, engagement quality, audience fit,
growth, consistency. A dimension the engine cannot compute stays `null` all the way through to the
ranking — it is excluded and named, never silently scored as zero.

**One code path, two databases.** SQLite by default; set `STRIDE_DATABASE_URL` for Postgres. A
~100-line shim translates the dialect, so nothing above the connection changes — and the claim is
checked rather than asserted: the same suite runs on both, 359 tests on SQLite and 361 on Postgres,
where the two measurement tests that skip without a server can finally run.

📐 Architecture: [`docs/architecture.md`](docs/architecture.md) · Client: [`docs/ui-architecture.md`](docs/ui-architecture.md) ·
Visual: open [`docs/system-map.html`](docs/system-map.html) and [`docs/how-it-works.html`](docs/how-it-works.html) in a browser

---

## The business

| | |
|---|---|
| **Revenue** | Take rate on sponsorship deals and club packages |
| **Unit economics** | On a $5,000 deal at 10%: ~$341 contribution after payment rails (~68% margin on fee revenue) |
| **Break-even** | At launch-stage infrastructure, **one mid-size deal a month covers the entire platform's operating cost** |
| **Cost per MAU** | $0.01 – $0.05 through 100k MAU — the architecture scales roughly linearly |
| **AI inference cost** | **$0.** Scoring and matching are deterministic formulas, not model calls |

Full staged cost model, per-transaction economics and the honest people-cost line:
[`docs/costs.md`](docs/costs.md). Product definition and role workflows:
[`docs/product.md`](docs/product.md). Phasing: [`docs/build-plan.md`](docs/build-plan.md).

---

## Privacy posture

This product asks athletes to connect social accounts, so the data position is part of the design
rather than an afterthought:

- **Consent is per platform, explicit, and recorded.** The connect endpoint refuses without it, and
  both the grant and any withdrawal land in the audit log with the policy version agreed to.
- **Aggregates only.** Stride receives age bands, gender splits and country shares. No row in the
  schema can identify an individual follower, because no such data is ever requested.
- **One cookie, and it is strictly necessary.** No analytics, no third-party scripts, no tracking —
  which is why there is no consent banner, a position the [Cookie Policy](apps/web/src/lib/legal.ts)
  explains rather than papers over.
- **Six of six GDPR rights are live, and the page says which.** Access and portability are one JSON
  export of everything held about you; erasure anonymises the person and keeps only the deal records
  an accounting duty requires, with the name removed. Consent withdrawal, rectification and
  restriction were already there. `/legal/data` states the status of each rather than implying a
  button that does not exist.
- **Terms acceptance is recorded with the version shown**, and a test reads `POLICY_VERSION` out of
  the client to check the two constants cannot drift apart.
- **Anyone can block anyone.** A block ends contact in both directions and tells the other side
  nothing; a report reaches an admin queue with the message attached. With sixteen-year-olds
  admitted and an open messaging network, that is a requirement rather than a feature.

---

## Verification

```bash
python scripts/verify.py                 # everything: 12 checks, ~3 minutes
python scripts/verify.py --quick         # skip the build, the drill, the workbook
```

That is the whole protocol. It runs the unit suite, the design-token audit, the
build, the four API audits, the failure drill, the admission sweep and the two
business-plan guards, then prints one table. It exists because running them by
hand in sequence *drains the API rate limiter* -- 300 requests of burst against
audits that fire hundreds -- and a drill that starts on an empty bucket used to
die half way and leave a 60% error rate injected. `verify.py` waits for the
bucket between phases. Checks that need something which is not running are
reported as skipped rather than failed, because "the API was down" and "the
product is broken" are different sentences.

To include the Postgres run, point it at a server:

```bash
docker run -d --name stride-pg -e POSTGRES_PASSWORD=stride -p 55432:5432 postgres:16-alpine
python scripts/verify.py --postgres postgresql://postgres:stride@127.0.0.1:55432/stride
python scripts/verify.py --external      # also reach every URL the business plan cites
```

Two tests are skipped on SQLite and only run there; on Postgres the suite is
361 rather than 359. The dual backend is a claim this repository makes, so it
is worth the container to check it.

The individual checks, if you want one on its own:

```bash
cd apps/api && uv run pytest -q          # 359 passed, 2 skipped (those two need Postgres)
cd apps/web && npx tsc -b && npx vite build
python scripts/design_audit.py           # contrast measured, type scale named, DESIGN.md honoured
python scripts/journey.py     http://127.0.0.1:8490   # 38 product rules, end to end
python scripts/permissions.py http://127.0.0.1:8490   # 408 role x route combinations
python scripts/propagation.py http://127.0.0.1:8490   # 20 cross-role consequences
python scripts/links.py --api http://127.0.0.1:8490   # every link and API call resolves
python scripts/failure_drill.py                       # latency -> errors -> db down -> recovery
python scripts/admission_stress.py                    # the admission bar under a funnel sweep
python scripts/doc_consistency.py                     # every figure in prose still matches model.py
python scripts/verify_workbook.py                     # 1,973 formulas, no dangling refs, no cycles
```

`journey.py` and `permissions.py` write to the demo database and restore it afterwards, so
running them does not leave test applications sitting in the admin review queue.

---

## Containerized

```bash
docker compose -f infra/docker-compose.yml up --build   # web :8080, api :8490
kubectl apply -f infra/k8s/stride.yaml                  # probes, HPA, scrape annotations
```

---

<p align="center">
  <sub>First product draft — simulated athlete and sponsor data, by design, through the production pipeline.</sub>
</p>
