# The pitch deck

`Stride_Pitch_Deck.pptx`, 23 slides: 17 presented, a divider, and five held back
for questions. `Stride_Pitch_Deck.pdf` is the same deck exported, as a fallback
if PowerPoint misbehaves on the day.

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
| 1 | Cover |
| 2 to 4 | Origin, the €0 finding, and why the gap exists |
| 5 to 8 | The product, the deployed demo, how it works, the expert interview |
| 9 to 11 | Market funnel, why niche first, the four comparables |
| 12 to 14 | Revenue mix, Year 1, operations and people |
| 15 to 17 | Financials, the ask, the close |
| 18 | Backup divider |
| 19 to 23 | Pricing, scenarios, risk, valuation, the admission gate |

Every slide has speaker notes with what to say on it. They are written to be
spoken, not read off the screen.

Every figure comes from `business-plan/model.py` or the chart CSVs it writes.
Nothing on a slide was typed from memory, so a number that changes in the model
changes here by editing `build_deck.js` against it, never by retyping.

## Still yours to do

Rehearse against a clock. Seventeen slides in fifteen minutes is about fifty
seconds each, and the cover and close take ten. The three slides worth the most
time are 3 (the €0 finding), 6 (the demo) and 16 (the ask).
