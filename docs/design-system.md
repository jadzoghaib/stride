# Stride — Design Direction

> **Superseded. The canonical design brief is [`apps/web/DESIGN.md`](../apps/web/DESIGN.md).**
> Read that before writing any UI. This file is a redirect, kept because the
> repo's docs index links to this path.

| Looking for | Go to |
|---|---|
| Visual language — tokens, themes, type, motion, information design | [`apps/web/DESIGN.md`](../apps/web/DESIGN.md) |
| Client structure — layers, routing, session, data flow, view contract | [`ui-architecture.md`](./ui-architecture.md) |
| Server, data, deployment, observability | [`architecture.md`](./architecture.md) |

## What this file used to say, and why it is gone

The v0.1 direction here was *"dark, editorial, premium"*, built on an indigo →
violet → cyan gradient trio (`wave-field`, `wave-line`, `wave-text`), a system
sans with no display face, and `ink-*` / `mist-*` / `pulse-*` tokens.

It was replaced by the **Timing Board** direction — the register of a stadium
results board and a race split sheet — because the v0.1 rules produced a
competent but anonymous product with no point of view. The specific devices it
prescribed are now **explicitly rejected** in `DESIGN.md`: gradient waves, an
accent rail on every card, equal-gap `rounded-2xl` card grids, and a type scale
where everything sits between 14px and 30px so nothing has hierarchy.

None of the old tokens survive in the codebase — `mist-*`, `ink-950`, `pulse-*`
and the `wave-*` classes were fully migrated out. If you find one, it is a
regression, not a leftover.

**What carried forward** (unchanged, and still binding — now stated in
`DESIGN.md`): partial data is labelled rather than hidden or zero-filled; every
score opens its inputs within one click; empty states name the action that
produces content; colour never carries meaning alone; no emojis, stock
photography, star ratings, or gamification.
