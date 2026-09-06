# Attachments

Everything the business plan points at that is not prose: screenshots that are
already here, photographs that are briefed and not yet taken, and the CSV series
behind the marked graph slots.

Obsidian resolves these relative to the note, so the folder can move with it.

## Product screenshots — in place

All eight are §4.1 of `../stride-business-plan-draft.md`, captured from the
running application rather than mocked. Re-take them after any visual change
worth showing; the alt text in the plan says what each one has to demonstrate.

| File | What it shows |
|---|---|
| `product-athlete-board.jpg` | The athlete's own dashboard — marketability score as the headline, five dimensions ranked with confidence |
| `product-audience-map.jpg` | Audience by country as a choropleth, with the simulated-audience disclosure chip |
| `product-matching.jpg` | A match expanded: eight components ranked by contribution, arithmetic visible. **The most persuasive image in the deck** |
| `product-campaign-matches.jpg` | The same ranking collapsed — the sponsor's shortlist, coverage on every row |
| `product-athlete-page.jpg` | An athlete's public page: membership card, follow and subscribe as separate actions |
| `product-creator-feed.jpg` | A wall mixing own posts with platform activity, above a locked post showing only its title |
| `product-directory.jpg` | The public athlete directory, sortable on the measurement |
| `product-deal-delivery.jpg` | A completed deal measured against the projection captured at offer time. Taken as `sponsor3@demo.stride` (Solstice Hydration), the only demo org with a completed deal carrying two measured deliverables |

## Photographs — briefed, not taken

Each has a `📷 PHOTO Pn` slot in the plan carrying the brief and the licensing
note. Drop a file in with the name below and swap the callout for an embed.

| File | What it is |
|---|---|
| `hero-trail-runner.jpg` | Opening image. One athlete small in a large landscape: scale. Stock is acceptable |
| `athlete-portrait.jpg` | A real niche athlete at an ordinary event, captioned with sport, ranking and follower count. **Needs a signed release if named** |
| `race-expo.jpg` | A race expo or tournament village. The argument is density: everyone in frame is a practitioner |

## `chart-data/` — the numbers behind the graph slots

Written by `python business-plan/graph_data.py`, straight out of `model.py` and
`sport_index.py`, so a chart cannot quietly disagree with the arithmetic it came
from. **Re-run it after any change to the model.** Nine of the twelve graph
slots have a file here; `G2` is illustrative and has no data, and `G12` reads
the risk table in the plan directly.

The plan's §9.4 lists every slot, its section, and which file feeds it.

> The directory is `chart-data/` rather than `data/` because `data/` is
> gitignored at the repository root, where it holds the runtime database.
