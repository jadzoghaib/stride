# Stride: MSc Business Plan · status

*ESADE MSc Final Project, Business Plan track, October 2026 session.
Last updated 30 September 2026.*

---

## Where to look

| What | Where |
|---|---|
| **The submission** | `business-plan/Stride_Business_Plan.docx`, 40-page body, 108 total, TOC populated |
| Same, without Word | `business-plan/Stride_Business_Plan.pdf` |
| **The financial model** | `business-plan/Stride_Financial_Model.xlsx`, 18 sheets, 2,617 formulas |
| The body's source | `business-plan/esade-body.md` |
| The exhibits | `business-plan/attachments/charts/`, 12 PNGs, and `attachments/ui/`: 6 screens |
| School material | `Desktop\Business Track MSc Thesis\` (outside this repo) |

**One thing on opening.** In Excel, go to the **Check** sheet first: every
VARIANCE row must read zero. The Word table of contents is already populated
(it is a field, so it needs F9 only if you edit headings after this).

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
uv run --with playwright python business-plan/make_ui_shots.py  # 6 UI screens
uv run --with playwright python business-plan/make_appendices.py # appendices L, M
uv run --with python-docx python business-plan/build_docx.py   # the .docx
uv run python business-plan/build_workbook.py                  # the .xlsx
```

Then check it:

```bash
uv run python scripts/doc_consistency.py    # 301 prose claims against the model
uv run python scripts/verify_workbook.py    # structure: refs, cycles, parsing
uv run python scripts/recalc_workbook.py    # arithmetic: every VARIANCE is zero
```

`esade-body.md` carries Operations, HR, Legal/Growth and the primary research
**in the body** via `<!-- INCLUDE: -->`, not as appendices, the rubric weights
Operations and HR at 15% each, and an examiner grades what is in front of them
rather than what is filed behind it.
Appendices are `01-` to `11-`, plus the two generated ones, `17-evidence-base.md`
and `18-product-walkthrough.md`.

---

## What is done

- All 15 sections of ESADE's outline, on their cover page, under the page limit
- Financial model: P&L, balance sheet, cash flow, DCF, sensitivity, **plus** the
  hiring plan, CAC/CLV and KPI sheets the school's template teaches
- 12 exhibits drawn from generated data
- Primary research written up: one expert interview, athlete conversations
- A deployed demo at **stride-demo.onrender.com** (takes ~30s to wake)

---

## Added 29 September

- **§4.6 Sales plan**, generated from the model's own funnel. The school's
  checklist lists it separately from the sales forecast; only the forecast existed
- **§10 Growth** is now a real section. It was a pointer at §8.3, because Legal
  and Growth shared one file and spliced in together. `16-growth-strategy.md`
  splits them, as the outline does
- **§7.6 scenarios are computed**, not typed. `model.scenario_table()` re-runs
  the whole model under changed drivers; the pessimistic case removes the niche
  churn advantage entirely. Six new pins guard the table
- **Appendix L**: the evidence base, 32 assumptions classified
  SOURCED/BENCHMARKED/DERIVED/ESTIMATE, generated from `research_data.py`
- **Appendix M**: six screens of the deployed demo, captured by
  `make_ui_shots.py` against the live site
- **Social impact** in §2.2, for the evaluation form's learning objectives
- **53 em-dashes removed** from prose. The remainder are structural: table
  cells, figure captions, appendix labels

## Changed 30 September

- **Scout Starter at €99/mo**, a fourth sponsor tier. The plan listed €249 as
  its cheapest paid plan while the model booked €199 per subscriber in Y1,
  which no mix of €249 and €999 can produce
- **Sponsorship commission tiered 10 / 7 / 5** by plan. The blended rate falls
  from 9.60% in Y1 to 8.56% by Y10
- **Pre-seed cut to €400k** from €600k, by moving the hiring ramp out about
  eighteen months rather than building less. Scaling the plan down was tried
  first and does not work: halving the athlete trajectory leaves the trough
  within €15k of where it was, because cutting growth cuts income and
  outgoings in the same proportion. Trough €280k, requirement €392k
- **WACC cited to Damodaran**, NYU Stern European cost of capital, 5 January
  2026: Software (Internet) at 6.01% in euros, with the 19-point gap to our
  25% stated as a stage premium rather than hidden
- **Zero em-dashes** in the document and the workbook

## What is not done

| Item | Note |
|---|---|
| **Slide deck** | 30% of the grade. Deliberately left until the plan is validated |
| **Sponsor-side interviews** | The largest hole in the research. No brand-side conversations exist: the only completely untested side of the marketplace |
| Trade mark clearance | "Stride" has existing marks in apparel and fitness software. A search comes before any brand spend |
| Loose tolerances | ~100 of the guard's pins are looser than half their printed place. Some deliberately, some not: a judgement pass, not a mechanical one |

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

Every figure written in prose is pinned to the model, and **the rule for a new
pin is half the last printed place**. Anything looser reports "checked" and
checks nothing: proven in the wild, when a 0.05 tolerance on a two-decimal
figure let four stale EBITDA cells pass the very check added to catch them.

The rule is not yet retrofitted. Roughly a hundred older pins are looser than
that, some deliberately (a rounded crossover like €1,380/month is not claiming
euro precision) and some not. Until that pass is done, **a green guard means
every pinned figure is within its own stated tolerance, not that every figure
is exact.**

When adding a claim, pin it in `scripts/doc_consistency.py` on the way in, not
after it drifts. Two tables sat stale through four pull requests because nothing
watched them.
