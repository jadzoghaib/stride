# Stride — UI / UX Architecture (v0.1)

How the web client is put together: what depends on what, how a request becomes a
screen, and which rules keep the surfaces consistent. **Structure only.**

| Concern | Owner |
|---|---|
| Visual language — tokens, type, motion register, information design | `apps/web/DESIGN.md` |
| Client structure — layers, routing, session, data flow, view contract | **this document** |
| Server, data, deployment, observability | `docs/architecture.md` |
| Role flows and product intent | `docs/product.md` |

**The same material as diagrams.** `docs/how-it-works.html` covers the four client
mechanisms below — cold start, the route guard, the view state contract, and
expired sessions — as one flowchart each, in plain language.
`docs/system-map.html` places the client in the whole system.

---

## Layers

```
main.tsx          mount, global CSS, ErrorBoundary
  App.tsx         providers + router + scroll behaviour
    Shell.tsx     board bar, role navigation, theme control, session
      views/      one file per route — fetch, arrange, own their states
        components/   Board · charts · ui primitives
          lib/        api · auth · theme · toast · format · types
```

**The dependency rule is one-directional.** Views import from `components/` and
`lib/`; neither ever imports a view. `lib/` imports nothing from `components/`.
A primitive that needs to know which view is rendering it has been mis-factored —
pass it a prop.

`views/` is grouped by **audience**, not by feature: `athlete/`, `club/`,
`sponsor/`, `fan/`, with public and cross-cutting views at the top level. Role is
the strongest boundary in this product — it decides access, navigation, and data
shape — so it is the boundary the filesystem reflects.

## Information architecture

20 routes. Every one names its access rule at the route, not inside the view.

| Path | View | Access | Chrome |
|---|---|---|---|
| `/` | `Landing` | public | none |
| `/auth` | `Auth` | public | none |
| `/athletes` | `AthletesDirectory` | public | Shell |
| `/athletes/:slug` | `AthletePublic` | public | Shell |
| `/clubs` | `ClubsDirectory` | public | Shell |
| `/clubs/:slug` | `ClubPublic` | public | Shell |
| `/athlete` | `athlete/Dashboard` | athlete | Shell + Guard |
| `/athlete/deals` | `athlete/Deals` | athlete | Shell + Guard |
| `/athlete/profile` | `athlete/Profile` | athlete | Shell + Guard |
| `/club` | `club/Dashboard` | club | Shell + Guard |
| `/sponsor` | `sponsor/Campaigns` | sponsor | Shell + Guard |
| `/sponsor/campaigns/:id` | `sponsor/CampaignMatches` | sponsor | Shell + Guard |
| `/sponsor/athletes/:slug` | `sponsor/AthleteEvidence` | sponsor | Shell + Guard |
| `/sponsor/pipeline` | `sponsor/Pipeline` | sponsor | Shell + Guard |
| `/discover` | `fan/Discover` | fan · athlete · sponsor · admin | Shell + Guard |
| `/feed` | `fan/Feed` | fan · athlete · sponsor | Shell + Guard |
| `/admin` | `admin/Operations` | admin | Shell + Guard |
| `/legal/data` | `legal/YourData` | public | Shell |
| `/legal/:doc` | `legal/Legal` | public | Shell |
| `*` | `NotFound` | public | Shell |

**The legal routes are public deliberately.** Someone deciding whether to hand
over their social data has to be able to read the terms *before* creating an
account, so these sit outside the Guard.

**Landing and Auth render outside the Shell, deliberately.** They are the two
surfaces where navigation would be wrong: one is the only marketing page, the
other is where you have no session to navigate with. Everything else is inside
the Shell, so the board bar is a constant.

`:slug` for people and organizations (stable, legible, shareable), `:id` only for
campaigns (internal objects, never linked publicly).

## Role → navigation

`Shell.tsx` holds one `NAV` map, keyed by role. It is the single definition of
what each audience can reach; adding a destination means editing one object.

| Role | Navigation | Home (`roleHome`) |
|---|---|---|
| athlete | Dashboard · Deals · Profile · Directory · Clubs | `/athlete` |
| sponsor | Campaigns · Pipeline · Directory · Clubs | `/sponsor` |
| club | Club HQ · Directory · Clubs | `/club` |
| fan | Discover · Following · Clubs | `/discover` |
| admin | Directory · Clubs · Operations | `/admin` |

`roleHome(role)` is the one function that answers "where does this account
belong?". Guard redirects, the wordmark link, and post-auth landing all call it —
so there is no second opinion about a role's home.

The active tab is marked with an inset amber underscore — the same rule that
closes the board header, so navigation and content read as one system.

## Session and access control

```
AuthProvider  GET /api/auth/me on mount → me | null, loading
  Guard       loading      → "Checking session…"
              no session   → <Navigate to="/auth">
              wrong role   → <Navigate to={roleHome(me.role)}>
              otherwise    → <Shell>{view}</Shell>
```

Sessions are **httpOnly cookies, same-origin** — the client never holds a token
and cannot read one. `credentials: 'same-origin'` on every request is the whole
of the auth wiring.

**Client guards are for navigation, not security.** They decide what to render;
the API enforces the boundary with `require_role` on every route. A user who
edits their way past a Guard reaches a 403, not data.

**But a guard that is *more permissive* than the API is still a bug.** It does
not leak anything — it strands the user on a 403 instead of redirecting them
somewhere useful. `/discover` and `/feed` are the pair that differ (admin may
reach discovery, but a following feed needs follows an admin has none of), and
`test_admin_reaches_discover_but_not_feed` pins the two lists together.

**One place handles session death.** `lib/api.ts` intercepts any `401` carrying a
known session-failure code (`not_authenticated`, `invalid_session`,
`session_revoked`, `account_unavailable`) and hard-redirects to `/auth` — so an
expired session cannot leave a view rendering half-authorized. The `/api/auth/me`
probe is exempt: anonymous visitors hit it legitimately on every cold load.

## Data flow

**Fetch in the view, in an effect, into local state.** There is no client cache,
no query library, no store.

```
view mounts → api.get('/api/<role>/workspace') → setState → render
mutation    → api.post(...) → load() again → toast
```

**One aggregate call per workspace.** `/api/athlete/workspace`,
`/api/sponsor/workspace`, `/api/club/workspace` each return everything their
dashboard needs in a single response. The server composes; the client does not
orchestrate. This is why no cache layer is missed — a screen is one request, and
a mutation refetches that one request.

Accepted cost: cross-view navigation refetches, and two views showing the same
entity each fetch it. At this data scale that is cheaper than the invalidation
logic a cache would need. When it stops being true, the seam is `lib/api.ts` —
introduce a query client there, not in the views.

**Server error codes never reach the screen.** The API returns stable machine
codes; `ERROR_TEXT` in `lib/api.ts` is the single table mapping them to human
sentences, and `errorText(err)` is the only thing views call. An unmapped code
falls through as itself rather than as a lie.

A code whose text is *generated* rather than drawn from a fixed set cannot live
in that table — `requires_role:fan|sponsor|athlete` is built per route — so
`errorText` carries a prefix rule for it. Any future generated code needs the
same, or the raw string is what the user reads.

## The view state contract

Every data view renders exactly four states, and none of them is a blank screen:

| State | Component | Rule |
|---|---|---|
| Loading | `PageLoading` | Skeleton in the shape of the content, not a spinner |
| Failed | `LoadError` | The mapped human sentence, never a raw code |
| Empty | `EmptyNote` | Says **what action produces content**, not "no data" |
| Data | the view | |

The canonical guard is one line, before any content:

```tsx
if (!ws) return error ? <LoadError text={error} /> : <PageLoading />
```

**Load failure and mutation failure are different states.** The guard above only
fires when there is nothing to show. Once data has loaded, a failed action
renders an inline banner instead — the screen keeps its content and reports what
went wrong in place, rather than collapsing to an error page.

Held by 12 of 14 data views. `AthletesDirectory` and `fan/Discover` render their
own inline error and skip the skeleton — see Known gaps.

## Composition order

```
ErrorBoundary          last-resort catch; a render crash shows a recovery panel
  AuthProvider         session — everything else may depend on it
    ToastProvider      transient confirmations, mounted above the router
      BrowserRouter
        ScrollToHash
          Routes
```

Auth wraps Toast wraps Router: the session must resolve before any route decides
what to show, and a toast has to survive the navigation that triggered it.

`ScrollToHash` exists because React Router does not scroll to `#anchors`.

**Every headline figure links to the section that explains it.** The board's
figures carry hash targets — `/athlete/deals#history`, `/athlete#platforms` — and
`Section` renders the matching `id`. That is the *evidence within one click*
principle expressed as routing, and it works across views as well as within one
(`/club#roster` from a stat tile). The 60ms delay lets a freshly-routed view
render its sections before the scroll is attempted.

## Styling architecture

```
index.css   :root RGB channel triplets   →  the only place values exist
            [data-theme='light'] override
            @layer base
            @layer components            →  personality: board, lanes, meters, rules
tailwind.config.ts   wraps tokens with <alpha-value>  →  bg-ok/10 works
views + components   utilities for layout only
```

**Tailwind for layout; hand-written CSS for personality.** Structure — flex, grid,
gap, spacing — stays in utilities. Anything with character — the board rule, the
lane grid, textures, masks, motion — lives in `@layer components` as real CSS.
Reaching only for what utilities make cheap is what caps a UI at "competent
default".

Tokens are stored as **channel triplets** (`--c-ink: 242 244 247`), never whole
colours, or every opacity modifier silently breaks. Full rationale and the token
table are in `apps/web/DESIGN.md` — this document does not restate them.

**Theme has one source of truth.** An inline script in `index.html` sets
`data-theme` on `<html>` **before first paint**; `useTheme()` only reads it back
and persists changes. No flash, no second opinion. Components never reference a
theme directly — they use tokens, and the tokens flip.

## Component inventory

| Module | Holds |
|---|---|
| `components/ui.tsx` | Primitives: `PageHeader` `Modal` `KV` `Section` `Meter` `DimensionGrid` `ShareBar` `Sparkline` `Delta` `Avatar` `CoverageChip` `StatusChip` `Rise`, the three state components, and the `useCountUp` / `useReducedMotion` hooks |
| `components/Board.tsx` | The full-bleed board header — identity, one display-scale figure, signed delta, trend, secondary figures |
| `components/charts.tsx` | Audience visualization: `AgeBars` `GenderDonut` `CountryMap` `AudiencePanel` |
| `components/Shell.tsx` | Board bar, `NAV`, `Wordmark`, `ThemeToggle` |
| `components/ErrorBoundary.tsx` | Render-crash recovery |
| `lib/format.ts` | `fmtNum` `fmtMoney` `fmtPct` `fmtDate` `fmtDT` `initials` `avatarHue` — every number on screen goes through one of these |

Charts are hand-built SVG, not a charting dependency: four chart types, each
needing token-driven colour and reduced-motion behaviour, cost less as SVG than
as a library plus its overrides.

## Layout

`<main class="stride-main">` is a **full-bleed grid**. Content sits in a centred
1084px track; a direct child marked `.bleed` spans edge to edge. Views render
content as direct children of `<main>` (fragments flatten), so a board header can
break the column while the rest stays in it.

Never `width: 100vw` + negative margins — `100vw` includes the scrollbar on
Windows and scrolls the body sideways.

## Motion and accessibility

**One orchestrated moment: the board boots.** The headline numeral rolls up, lane
bars wipe left on an ~85ms stagger, blocks rise in sequence. Then it stops.
Scattered micro-animation is what makes a UI read as generated; a single settling
sequence reads as intended.

Two enforcement paths, both required: `useReducedMotion()` for anything animated
in JS (`useCountUp` jumps straight to the final value), and the global
`prefers-reduced-motion` guard in `index.css` for CSS. A JS-driven count-up
ignores the CSS guard entirely — that is why both exist.

- **Colour never carries meaning alone.** `Delta` pairs its colour with ▲/▼ *and*
  a screen-reader word; status is a labelled pill.
- Icon-only controls (theme, sign out) carry `aria-label` and `title`.
- Loading regions announce with `role="status"`.
- Interactive lanes expose `aria-pressed`; selection state is not colour-only.

## How a view opens

Exactly two options, so no surface falls back to an unstyled heading in the body
face:

| The view… | Opens with | Examples |
|---|---|---|
| reports a headline figure | `Board` (full-bleed, display-scale numeral, closing rule) | athlete dashboard, sponsor campaigns, campaign matches, club HQ, public athlete profile |
| does not | `PageHeader` (eyebrow, display-face title, tags, lede) | directory, clubs, deals, profile, pipeline, discover, feed, evidence |

**The closing rule must report something true.** When the headline is a 0-100
score the rule fills to it. When the headline is money or a count it is not a
percentage of anything, so the view passes `rulePct` explicitly — the club board
fills it to the share of live packages that have a backer, the sponsor board to
the accept rate. A rule filled to an arbitrary width would be decoration.

## Known gaps

| Gap | Impact | Fix |
|---|---|---|
| No client cache | Cross-view navigation refetches | Accepted at this scale; the seam is `lib/api.ts` |
| Mobile layout is unpolished below ~700px | Tables scroll horizontally inside their own container rather than reflowing | Deliberate non-goal for v0.1 (product.md) |
