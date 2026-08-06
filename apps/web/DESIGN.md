# Stride — design brief

**Read this before writing any UI.** It replaces the previous "light, airy,
premium / Passes-register" note, which produced a competent but anonymous
product with no point of view.

---

## Direction: "Timing Board"

The register of a **stadium results board and a race split sheet** — not a
generic SaaS dashboard. Sports data has its own typographic tradition:
enormous condensed numerals, tabular alignment, signed deltas, ranked
positions, timestamped official results. That tradition is the source, because
Stride's subject is athlete measurement.

The feeling to chase: **measured, kinetic, adult.** A pit wall, not a
marketing page. Dense where the data is dense; silent everywhere else.

**Explicitly rejected**, because they are what generated software looks like:
indigo→violet→cyan gradients, Inter / Space Grotesk, `rounded-2xl` cards in
equal-gap grids, an accent rail on every card, emoji section markers, centred
everything, hero gradients.

---

## Tokens

Values live in `src/index.css` as **RGB channel triplets**
(`--c-ink: 242 244 247`), never hex. `tailwind.config.ts` wraps them with
`<alpha-value>` so `bg-ok/10` compiles to `rgb(var(--c-ok) / 0.1)`. Storing a
whole colour silently breaks every opacity modifier — don't.

| Role | Token | Notes |
|---|---|---|
| Page ground | `ground` | Graphite, not black |
| Board ground | `ground-deep` | Full-bleed header band |
| Card | `panel` | |
| Hover / inset | `raised` | |
| Meter track | `track` | |
| Text | `ink` → `ink-2` → `ink-3` | Heading → body → muted |
| Hairline | `line`, `line-strong` | Alpha baked in; no `/opacity` on these |
| Accent | `accent` | Signal amber — the scoreboard LED |
| Accent as text | `accent-ink` | Darkens in light mode; `#FFB020` fails contrast on white |
| Text **on** amber | `accent-on` | **Does not flip with the theme.** The fill is light amber in both modes |
| Semantics | `ok`, `warn`, `critical` | Separate from the accent, always |

**One accent, one job.** Amber marks emphasis and strength. Semantic colour
marks state. They never trade places — if a warning turns amber and the accent
also means "good", the board stops reporting anything.

## Themes

**Dark is the default.** `data-theme="light"` on `<html>` flips token values;
component rules must never reference a theme directly. The attribute is set
pre-paint by an inline script in `index.html` — `useTheme()` only reads it back
and persists changes, so there is no flash and no second source of truth.

Light mode is not an inversion. It gets its own accent-ink, its own shadows,
and **no scanline texture** (dark 1px rules on a pale ground moiré against the
pixel grid and read as a rendering fault).

## Type

| Role | Face | Used for |
|---|---|---|
| Display | **Barlow Condensed** 600/700 | Numerals, labels, table heads, nav, buttons |
| Body | **Barlow** 400/500 | Running text |
| Meta | `ui-monospace` | Timestamps, formula versions, IDs |

Self-hosted from `public/fonts` (SIL OFL). Never link a font CDN.

**The scale gap is the point.** A ~116px headline numeral against 11px tracked
caps. If everything on a screen sits between 14px and 30px, the screen has no
hierarchy — that was the old app's core failure. `.score` and `.cap` exist to
make that contrast the default, not an effort.

Uppercase labels get `tracking-micro` (.13em). Anything with digits in a column
gets `tnum`.

## Layout

`<main class="stride-main">` is a **full-bleed grid**: content sits in a centred
1084px track, and a direct child marked `.bleed` spans edge to edge. Views
render content as direct children of `<main>` (fragments flatten), so a board
header can break the column while the rest stays in it.

Never use `width: 100vw` + negative margins for full-bleed — `100vw` includes
the scrollbar on Windows and scrolls the body sideways.

Break the uniform grid deliberately: a board header, then an asymmetric split
(`1.85fr / 1fr`), not another row of equal cards.

## Motion

**One orchestrated moment: the board boots.** On mount, the headline numeral
rolls up, lane bars wipe from the left on an ~85ms stagger, blocks rise in
sequence. Then it stops.

Scattered micro-animation is what makes a UI read as generated. A single
settling sequence reads as intended. Everything checks
`prefers-reduced-motion` — `useReducedMotion()` for JS, the global guard in
`index.css` for CSS.

## Information design

- **Summary before detail.** The board reports; the sections explain.
- **Structural devices must encode something true.** Lane numbers are the
  athlete's actual rank on that dimension. The rule closing the board fills to
  the score. If a device carries no information, delete it — that is the line
  between structure and decoration.
- **State in form, not colour alone.** A pill, a stripe, an arrow glyph. The
  `Delta` component pairs its colour with ▲/▼ and a screen-reader word.
- **Label derived numbers as derived.** The API has no athlete-level composite,
  so the dashboard's headline is a client-side mean and says so. Never present
  a computed figure as a stored one — the whole product claim is traceability.
- **Partial data is labelled, never hidden.** Two connected platforms means a
  two-platform score, stated as such.

## Where things live

| | |
|---|---|
| Tokens, component layer, motion | `src/index.css` |
| Token → Tailwind mapping | `tailwind.config.ts` |
| Primitives (lanes, meters, count-up, sparkline, chips) | `src/components/ui.tsx` |
| Full-bleed board header | `src/components/Board.tsx` |
| App shell, nav, theme toggle | `src/components/Shell.tsx` |
| Charts | `src/components/charts.tsx` |

## The rule that keeps this from decaying

**Tailwind for layout; hand-written CSS for personality.**

Utility classes are a lossy vocabulary for design — reaching only for what
utilities make cheap is what caps a UI at "competent default". Anything with
character (motion, gradients, textures, masks, the board rule, the lane grid)
belongs in `@layer components` as real CSS. Structure — flex, grid, gap,
spacing — stays in utilities.

Watch specificity when you add to the component layer: `.bar > i` is 0,1,1 and
beats a `bg-*` utility at 0,1,0. That is why the muted variant is
`.bar > i.muted` and lane alignment lives in CSS rather than on the element.
