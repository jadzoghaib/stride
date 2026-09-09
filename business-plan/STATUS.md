# Stride — MSc Business Plan · status

*ESADE MSc Final Project, Business Plan track, October 2026 session.
Last updated 9 September 2026.*

---

## Where to look

| What | Where |
|---|---|
| **The submission** | `business-plan/Stride_Business_Plan.docx` — 34-page body + appendices, 91 total |
| Same, without Word | `business-plan/Stride_Business_Plan.pdf` |
| **The financial model** | `business-plan/Stride_Financial_Model.xlsx` — 18 sheets, 2,520 formulas |
| The body's source | `business-plan/esade-body.md` |
| The exhibits | `business-plan/attachments/charts/` — 12 PNGs |
| School material | `Desktop\Business Track MSc Thesis\` (outside this repo) |

**Two things on opening.** In Word, press **F9** on the Contents page — the table
of contents is a field and starts empty. In Excel, go to the **Check** sheet
first: every VARIANCE row must read zero.

---

## Deadlines

| Date | What |
|---|---|
| ~~10 Sept 2026~~ | Final title registered in eOffice, after tutor approval |
| **25–30 Sept 2026** | Document submitted |
| Week of 12 Oct | Online defence, 15 min + 10 min Q&A |

Document is **70%** of the grade, presentation **30%**. Body must stay **under
50 pages** excluding appendices.

---

## How it is built

Nothing is hand-typed. Rebuild after any change to the model:

```bash
uv run python business-plan/model.py --write                   # the MODEL: tables
uv run python business-plan/graph_data.py                      # CSVs from model.py
uv run --with matplotlib python business-plan/make_charts.py   # 12 exhibits
uv run --with python-docx python business-plan/build_docx.py   # the .docx
uv run python business-plan/build_workbook.py                  # the .xlsx
```

Then check it:

```bash
uv run python scripts/doc_consistency.py    # 282 prose claims against the model
uv run python scripts/verify_workbook.py    # structure: refs, cycles, parsing
uv run python scripts/recalc_workbook.py    # arithmetic: every VARIANCE is zero
```

`esade-body.md` carries Operations, HR, Legal/Growth and the primary research
**in the body** via `<!-- INCLUDE: -->`, not as appendices — the rubric weights
Operations and HR at 15% each, and an examiner grades what is in front of them.
Only `01-` to `11-` are appendices.

---

## What is done

- All 15 sections of ESADE's outline, on their cover page, under the page limit
- Financial model: P&L, balance sheet, cash flow, DCF, sensitivity, **plus** the
  hiring plan, CAC/CLV and KPI sheets the school's template teaches
- 12 exhibits drawn from generated data
- Primary research written up: one expert interview, athlete conversations
- A deployed demo at **stride-demo.onrender.com** (takes ~30s to wake)

---

## What is not done

| Item | Note |
|---|---|
| **Slide deck** | 30% of the grade. Deliberately left until the plan is validated |
| **Sponsor-side interviews** | The largest hole in the research. No brand-side conversations exist — the only completely untested side of the marketplace |
| Two blanks in §3.1.5 | Exact number of athletes interviewed, and the date of the Íñigo interview |
| Trade mark clearance | "Stride" has existing marks in apparel and fitness software. A search comes before any brand spend |
| Loose tolerances | ~100 of the guard's pins are looser than half their printed place. Some deliberately, some not — a judgement pass, not a mechanical one |

---

## Decisions worth not relitigating

- **€600k pre-seed, not €400k.** It clears the €464k Y4 trough on its own, which
  makes the seed a growth option rather than a rescue.
- **The financial model stays ours** rather than being retrofitted into the
  school's template, which says of itself that it is a guide and not a
  fill-in-the-blanks. The three concepts it teaches that were missing have been
  added instead.
- **No paid hosting.** The demo runs on a free tier and sleeps.
- **The postal address is not published.** The email is, in the privacy policy.

---

## The habit that has caught the most errors

Every figure written in prose is pinned to the model, and **the tolerance is half
the last printed place**. Anything looser reports "checked" and checks nothing —
that was proven in the wild: a pin with a 0.05 tolerance on a two-decimal figure
let four stale EBITDA cells pass the very check added to catch them.

When adding a claim, pin it in `scripts/doc_consistency.py` on the way in, not
after it drifts. Two tables sat stale through four pull requests because nothing
watched them.
