# Stride — Design Direction (v0.1)

**Register: dark, editorial, premium. No emojis anywhere. Color arrives as
controlled gradient waves, never as loud fills.**

## Tokens (tailwind.config.ts + index.css)
- **Surfaces**: `ink-950 → ink-600` (deep blue-black ramp), hairline borders
  (`line`, `line-strong` at 14%/28% alpha).
- **Ink**: `mist-100 → mist-400` for text hierarchy.
- **Accent**: `pulse` (indigo) for interactive states; the **wave** trio
  (indigo `#6366f1` → violet `#8b5cf6` → cyan `#22d3ee`) reserved for:
  `.wave-field` (layered radial auroras on page background, ≤16% alpha),
  `.wave-line` (meter/bar fills), `.wave-text` (one gradient word per page, max).
- **Status**: ok/warn/danger, always paired with a text label — color never
  carries meaning alone.

## Typographic rules
- System sans; weight and tracking do the branding (no display font).
- `microcaps`: 11px uppercase, 0.08em tracking — every section label, table header.
- `tnum`: tabular figures on all data (money, scores, counts).
- One `text-2xl` number per stat card; body stays 14px.

## Component vocabulary
Panel (surface + hairline + 12px radius), stat card, dimension card with meter,
share bars (audience), coverage chip ("2 of 3 platforms" with status dot),
status chips (deal/connection states), initials avatar (deterministic gradient —
no stock photos), ranked match row with expandable evidence, dense tables.

## UX principles
- **Evidence within one click**: every score opens its inputs; every match
  decomposes into weight × component with reasons and caveats.
- **Partial data is labeled, never hidden or zero-filled** (coverage chips,
  "commercial signals only" caveats, explicit n/a with reason).
- **Empty states are designed**: every list has a written empty state that says
  what action produces content.
- **No consumer inflation**: density over hero sections; the landing page is the
  only marketing surface, and it is typographic, not illustrated.

## Explicitly banned
Emojis, flag glyphs, star ratings, confetti/gamification, stock photography,
rainbow category colors, exclamation-point copy.
