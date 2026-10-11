# The pitch deck

`Stride_Pitch_Deck.pptx`, 28 slides: 19 presented, a divider, and eight held
back for questions. `Stride_Pitch_Deck.pdf` is the same deck exported, as a
fallback if PowerPoint misbehaves on the day.

## The spine

Two engines, not one product with a feature attached. Fan monetisation and
sponsor analytics are presented as peers that feed each other, because that is
the actual thesis: each one produces the input the other cannot buy. So the
deck opens with **two** problems rather than one (the athlete earning nothing,
and the local brand spending on instinct), shows the single missing layer that
explains both, then the two engines, then the loop that joins them, and then
proves each engine in turn against the running application.

The competition table earns its keep here: the four comparables split exactly
two and two along the same seam, marketplace or data, and none of them built
both. That is the strongest available evidence that the pairing is the hard
part rather than the obvious part.

The question that table always draws is about SponsorUnited, the one comparable
that got large, and backup slide B3 answers it in the sponsor's own three verbs
from slide 4. The short version: a data company sells what the market did, and
only the platform that brokered the deal can say what your money did, because
the projection delivery is judged against is written onto the deal at the moment
the offer is made. A company outside the transaction never saw the promise.

Built for the ESADE MSc Business Plan defence: 15 minutes presenting, 10 for
questions, over Zoom, sharing your own screen. Joan Riera's evaluation form
grades contents, structure, visual presentation, delivery and questions; three
of those five are the deck's job, which is why every slide carries a page
number and the narrative runs in one line from problem to ask.

## The look

It is the product's own design language, taken from `apps/web/DESIGN.md`: the
"Timing Board" register of a stadium results board. Graphite ground, one signal
amber accent, enormous condensed numerals against 11pt tracked caps. The colours
in `build_deck.js` are the same values as `apps/web/src/index.css`, so the deck
and the demo look like one thing.

**Fonts.** Barlow Condensed and Barlow, the faces the app uses. They are not
Windows fonts, so they were converted from the app's own woff2 files
(`fonts_to_ttf.py`) and installed for the current user. They are also **embedded
in the .pptx**, so the deck is safe on a machine that does not have them.

To install them on another machine, select the four files in `fonts/` and use
the right-click "Install" item, or run:

```powershell
$d = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"; New-Item -ItemType Directory -Force $d | Out-Null
$k = "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
Add-Type -AssemblyName System.Drawing
Get-ChildItem fonts\*.ttf | ForEach-Object {
  Copy-Item $_.FullName $d -Force
  $p = New-Object System.Drawing.Text.PrivateFontCollection; $p.AddFontFile((Join-Path $d $_.Name))
  New-ItemProperty $k -Name "$($p.Families[0].Name) (TrueType)" -Value (Join-Path $d $_.Name) -PropertyType String -Force | Out-Null
}
```

Barlow is SIL Open Font License, which permits both the conversion and the
embedding.

## Rebuilding

```bash
npm install                 # pptxgenjs, once
node build_deck.js          # writes Stride_Pitch_Deck.pptx
```

Then export the PDF and check the render. PowerPoint is used rather than
LibreOffice because it is the only renderer here with the real fonts:

```powershell
$pp = New-Object -ComObject PowerPoint.Application
$d = $pp.Presentations.Open("$PWD\Stride_Pitch_Deck.pptx", $true, $false, $false)
$d.SaveAs("$PWD\Stride_Pitch_Deck.pdf", 32); $d.Close(); $pp.Quit()
```

**Re-embed the fonts after any rebuild**, because `build_deck.js` cannot write
them: open the deck, `SaveAs(path, 24, -1)` to a temporary name, and swap it in.

## What is where

| Slides | |
|---|---|
| 1 to 2 | Cover, and the athlete who started it |
| 3 to 5 | The athlete earns nothing, the brand spends blind, one missing layer |
| 6 to 7 | The two engines, and the loop that makes them one company |
| 8 to 9 | Each engine proved: the athlete dashboard, then the campaign result |
| 10 to 13 | The expert interview, market funnel, the wedge, the four comparables |
| 14 to 16 | Revenue mix, Year 1, operations and people |
| 17 to 19 | Financials, the ask, the close |
| 20 | Backup divider |
| 21 to 28 | The four steps, the matching arithmetic, how we differ from the data companies, pricing, scenarios, risk, valuation, the admission gate |

Every slide has speaker notes with what to say on it. They are written to be
spoken, not read off the screen.

Every figure comes from `business-plan/model.py` or the chart CSVs it writes.
Nothing on a slide was typed from memory, so a number that changes in the model
changes here by editing `build_deck.js` against it, never by retyping.

## The screenshots

`shots/` holds the sponsor-side captures, taken from the deployed demo the same
way the product appendix took the athlete-side ones. They exist because the
appendix only ever shot the athlete half, and a deck arguing that the analytics
are half the company cannot then show only the other half.

`sponsor-match-composition.png` is `sponsor-match-open.png` cropped to the
opened row: at full height the screen does not fit under a title.

The demo's engagement figures are seeded, and the product labels them simulated
on screen. Slide 9 says so in its source line and the notes say it out loud,
because a panel that spots it unprompted will discount everything else.

## Checks

```bash
node build_deck.js
uv run --with python-pptx python check_deck.py        # off-canvas shapes, notes, page numbers
```

`check_deck.py` catches the three failures that have actually happened here: a
shape placed off the canvas, which pptxgenjs writes rather than clamps; a
presented slide with no speaker notes; and a content slide left on the cover
layout, which silently loses its page number.

## Still yours to do

Rehearse against a clock. Nineteen slides in fifteen minutes is about forty-five
seconds each, and the cover and close take ten, so the middle has to move. The
five slides worth the most time are 3 and 4 (the two problems), 7 (the loop),
9 (the campaign result) and 18 (the ask).

If it runs long, slide 12 (the wedge) and slide 16 (operations and people) are
the two that survive compression best, because both are also written down in
the plan the panel has already read.
