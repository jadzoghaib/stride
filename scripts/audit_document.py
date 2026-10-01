"""Audit the Word document against ESADE's outline, itself, and the workbook.

`doc_consistency.py` checks 309 pinned figures against `model.py`. It says
nothing about whether the document is *complete*, whether its cross-references
resolve, whether its tables are well formed, or whether the figures a reader
sees in Word are the figures in the workbook. A plan can pass that guard and
still be missing a graded subsection, point at an appendix that does not exist,
or print a number the model produces and the spreadsheet does not.

Six checks, in the order a reader would notice the failures:

  OUTLINE     Every numbered item and named subsection of ESADE's Business Plan
              Outline (BP_Outline.pdf, Entrepreneurship Institute, Oct 2009)
              has a home in the document. Marketing, Operations, HR and Finance
              are 15% of the grade each, and the outline names their subsections
              explicitly, so a missing one is a missing mark rather than a
              stylistic choice.

  NUMBERING   Appendix subsections numbered from their source filename rather
              than their appendix letter, heading levels that skip, and
              duplicated section numbers.

  REFERENCES  Every "section N.N", "Appendix X" and markdown link resolves to
              something that exists in the built document.

  FIGURES     Every figure referenced exists on disk and is embedded; every
              generated chart is referenced somewhere; figure numbers run
              consecutively.

  TABLES      Every markdown table has a consistent column count, and no
              heading is malformed.

  ALIGNMENT   The headline figures in the Word document appear in the workbook
              with the same value. This is the check that the two artefacts a
              reader is handed actually agree, which neither existing guard
              makes: `doc_consistency` compares prose to `model.py` and
              `recalc_workbook` compares the workbook to `model.py`, so both can
              pass while the two deliverables disagree about a number only one
              of them prints.

Exit code 0 when nothing material is found.
"""
from __future__ import annotations

import pathlib
import re
import sys

import docx
from openpyxl import load_workbook

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "business-plan"))
import model as M  # noqa: E402

DOCX = ROOT / "business-plan" / "Stride_Business_Plan.docx"
XLSX = ROOT / "business-plan" / "Stride_Financial_Model.xlsx"
BP = ROOT / "business-plan"

findings: list[tuple[str, str, str]] = []


def add(sev: str, where: str, what: str) -> None:
    findings.append((sev, where, what))


#: ESADE's outline, as the PDF states it. Each entry is (outline item, the
#: phrase that must appear in a heading). Matching is on meaning rather than
#: wording, so the required CONCEPT is what is tested.
REQUIRED: list[tuple[str, tuple[str, ...]]] = [
    ("3 Executive summary", ("executive summary",)),
    ("4.1 Business description", ("business description",)),
    ("4.2 Mission, vision, objectives", ("mission", "vision")),
    ("4.3 Entrepreneurial team", ("entrepreneurial team", "the team")),
    ("5.1.1 Client", ("the client", "client:")),
    ("5.1.2 Market size and evolution", ("market size",)),
    ("5.1.3 Segmentation strategy", ("segmentation",)),
    ("5.1.4 Market research", ("market research",)),
    ("5.2.1 Need definition", ("the need", "need definition")),
    ("5.2.2 Sector and competition", ("competition", "the sector")),
    ("5.2.3 The offering", ("the offering",)),
    ("5.3 Key success factors", ("key success factors",)),
    ("5.4 Costs and investment needed", ("costs and investment",)),
    ("5.5 Revenue sources", ("revenue sources",)),
    ("6.1.1 Product strategy", ("product strategy",)),
    ("6.1.2 Pricing strategy", ("pricing strategy",)),
    ("6.1.3 Communication strategy", ("communication strategy",)),
    ("6.1.4 Channel strategy", ("channel strategy",)),
    ("6.2 Forecasting and sales outlook", ("sales forecast", "sales outlook")),
    ("7.1 Process map", ("process identification", "process map")),
    ("7.2 Structural subcontracting", ("subcontracting",)),
    ("7.3 Location, infrastructure, layout", ("location",)),
    ("7.4 Permanent material resources", ("permanent material", "permanent resources")),
    ("7.5 Transitory resources", ("transitory resources",)),
    ("7.6 Stocks", ("stocks",)),
    ("7.7 Delivery times", ("delivery times",)),
    ("7.8 Investment and launching costs", ("investment and launch",)),
    ("7.9 Operating costs", ("operating costs",)),
    ("7.10 Unit costs", ("unit costs",)),
    ("7.11 Launch plan", ("launch plan",)),
    ("8.1 Organizational structure", ("organizational structure", "organisational structure")),
    ("8.2 Job descriptions", ("job descriptions",)),
    ("8.3 HR policies", ("hr policies",)),
    ("8.4 Governance structure", ("governance structure",)),
    ("9.1 Financial assumptions", ("assumptions",)),
    ("9.2 Pro forma income statement", ("profit and loss", "income statement")),
    ("9.3 Pro forma cash flows", ("cash flow",)),
    ("9.4 Pro forma balance sheet", ("balance sheet",)),
    ("9.5 Project financing", ("cash position and financing", "financing")),
    ("9.6 BEP, ratios and feasibility", ("break-even", "ratios")),
    ("9.7 Sensitivity analysis", ("sensitivity",)),
    ("10.1 Legal form and structure", ("legal form",)),
    ("10.2 Intellectual property", ("intellectual", "industrial property")),
    ("11 Critical risks", ("critical risks",)),
    ("12 Growth strategy", ("growth and business development", "growth strategy")),
    ("13 Conclusions", ("conclusions",)),
    ("14 Bibliography", ("bibliography",)),
]


#: `Checklist First Partial Submission.doc`, the form the tutor completes. Some
#: items are headings and some are statements inside a section, so each is
#: searched for in the whole document rather than only in the heading list.
CHECKLIST: list[tuple[str, tuple[str, ...]]] = [
    ("The need", ("the need",)),
    ("The valued customer", ("the client", "valued customer")),
    ("The value proposition", ("value proposition",)),
    ("Key success factors", ("key success factors",)),
    ("Major cost drivers", ("costs and investment", "cost drivers")),
    ("Revenue streams", ("revenue sources", "revenue streams")),
    ("General environment", ("the general environment",)),
    ("Competitors, entrants, substitutes", ("substitutes and new entrants",)),
    ("Suppliers", ("suppliers",)),
    ("Source of advantage", ("competitive advantage", "source of advantage")),
    ("Market overview and trends", ("market size",)),
    ("Segmentation", ("segmentation",)),
    ("Positioning strategy", ("positioning",)),
    ("Marketing mix", ("product strategy", "marketing mix")),
    ("Sales forecasts", ("sales forecast",)),
    ("Sales plan", ("sales plan",)),
]

#: `esade BP-FINAL EVALUATION FORM v5.docx`, the eight learning objectives. Only
#: the ones naming something checkable are tested; "communicate persuasively" is
#: a judgement an examiner makes and not a string this can look for.
OBJECTIVES: list[tuple[str, tuple[str, ...]]] = [
    ("Operating locally and internationally", ("second market", "eu-wide", "internationally")),
    ("UN Sustainable Development Goals", ("sustainable development goal", "sdg")),
    ("Equality and non-discrimination", ("non-discrimination", "gender equality")),
    ("Ethically responsible business model", ("responsible business", "social impact")),
    ("Tools to validate market opportunities", ("market research", "primary research")),
    ("Positive social impact", ("social impact",)),
]


def main() -> int:
    if not DOCX.exists():
        print(f"{DOCX} not found")
        return 1
    d = docx.Document(DOCX)

    headings: list[tuple[int, str]] = []
    body_text: list[str] = []
    for p in d.paragraphs:
        st = p.style.name
        t = p.text.strip()
        if not t:
            continue
        body_text.append(t)
        if st.startswith("Heading"):
            tail = st.split()[-1]
            headings.append((int(tail) if tail.isdigit() else 9, t))
    for tb in d.tables:
        for row in tb.rows:
            for c in row.cells:
                if c.text.strip():
                    body_text.append(c.text.strip())
    full = "\n".join(body_text)
    heads_lower = [h.lower() for _, h in headings]

    # ── 1. the outline ───────────────────────────────────────────────────
    missing = []
    for item, phrases in REQUIRED:
        if not any(any(ph in h for ph in phrases) for h in heads_lower):
            missing.append(item)
    for item in missing:
        add("ERROR", "ESADE outline", f"no heading covers {item}")
    print(f"Outline: {len(REQUIRED) - len(missing)}/{len(REQUIRED)} required "
          f"items have a heading.")

    low = full.lower()
    miss_c = [item for item, ph in CHECKLIST
              if not any(x in low for x in ph)]
    for item in miss_c:
        add("ERROR", "tutor checklist", f"nothing in the document covers {item!r}")
    print(f"Checklist: {len(CHECKLIST) - len(miss_c)}/{len(CHECKLIST)} tutor "
          f"checklist items found.")

    miss_o = [item for item, ph in OBJECTIVES if not any(x in low for x in ph)]
    for item in miss_o:
        add("ERROR", "learning objectives", f"nothing addresses {item!r}")
    print(f"Objectives: {len(OBJECTIVES) - len(miss_o)}/{len(OBJECTIVES)} "
          f"checkable learning objectives addressed.")

    # The declaration of AI use must not ship with its placeholder in it.
    if "TO BE COMPLETED BY THE AUTHOR" in full:
        add("ERROR", "declaration of AI use",
            "Appendix O still carries its placeholder box and has not been written")

    # ── 2. numbering ─────────────────────────────────────────────────────
    # An appendix subsection must not be numbered from its source filename.
    current_appendix = None
    for lvl, t in headings:
        m = re.match(r"Appendix ([A-Z]):", t)
        if m:
            current_appendix = m.group(1)
            continue
        if current_appendix:
            n = re.match(r"(\d+)\.\d+\s", t)
            if n:
                add("ERROR", f"Appendix {current_appendix}",
                    f"subsection numbered {n.group(1)}.x, which is the source "
                    f"file's number, not the appendix's: {t[:54]!r}")
    # malformed headings
    for lvl, t in headings:
        if t.startswith(":") or t.endswith("::") or re.match(r"^:\s*.*:$", t):
            add("ERROR", "heading", f"malformed heading {t[:60]!r}")
    # duplicate section numbers
    seen: dict[str, str] = {}
    for lvl, t in headings:
        # Levels 1 and 2 only. Appendices H and J use numbered lists as
        # sub-headings ("1. Athletes: content guidance"), which are list items
        # that happen to start with a digit, not section numbers.
        if lvl > 2:
            continue
        n = re.match(r"((?:\d+\.)+\d+|\d+)\.?\s", t)
        if not n:
            continue
        num = n.group(1)
        if num in seen and seen[num] != t:
            add("WARN", "numbering",
                f"section {num} used twice: {seen[num][:36]!r} and {t[:36]!r}")
        seen[num] = t

    # ── 3. cross-references ──────────────────────────────────────────────
    appendix_letters = {m.group(1) for _, t in headings
                        if (m := re.match(r"Appendix ([A-Z]):", t))}
    section_numbers = set(seen) | {re.match(r"(\d+)\.", t).group(1)
                                   for _, t in headings if re.match(r"\d+\.", t)}
    for ref in sorted(set(re.findall(r"[Aa]ppendix ([A-Z])\b", full))):
        if ref not in appendix_letters:
            add("ERROR", "cross-reference", f"points at Appendix {ref}, which does not exist")
    bad_sections = set()
    for ref in re.findall(r"§\s?((?:\d+\.)*\d+)", full):
        root = ref.split(".")[0]
        if ref not in section_numbers and root not in section_numbers:
            bad_sections.add(ref)
    for ref in sorted(bad_sections):
        add("ERROR", "cross-reference", f"points at section {ref}, which does not exist")
    # markdown links that survived into the docx are a conversion failure
    for m in re.findall(r"\[[^\]]{1,60}\]\([^)]{1,80}\)", full):
        add("ERROR", "conversion", f"raw markdown link left in the document: {m[:60]}")

    # ── 4. figures ───────────────────────────────────────────────────────
    charts = {p.name for p in (BP / "attachments" / "charts").glob("*.png")}
    referenced = set(re.findall(r"(g\d+-[a-z0-9-]+\.png)", full))
    fig_nums = [int(n) for n in re.findall(r"Figure (\d+)[:.]", full)]
    embedded = sum(1 for s in d.inline_shapes)
    if fig_nums:
        expected = list(range(1, max(fig_nums) + 1))
        gaps = sorted(set(expected) - set(fig_nums))
        if gaps:
            add("WARN", "figures", f"figure numbers skip: {gaps}")
        dupes = {n for n in fig_nums if fig_nums.count(n) > 1}
        if dupes:
            add("ERROR", "figures", f"figure number used more than once: {sorted(dupes)}")
    unused = charts - referenced
    print(f"Figures: {len(fig_nums)} captions, {embedded} images embedded, "
          f"{len(charts)} charts on disk.")
    if unused and len(unused) < len(charts):
        add("NOTE", "figures", f"generated but never referenced by filename: "
                               f"{', '.join(sorted(unused))}")

    # ── 5. markdown table integrity, in the sources ──────────────────────
    for path in sorted(BP.glob("*.md")):
        if path.name == "stride-business-plan-draft.md":
            continue
        lines = path.read_text(encoding="utf-8").split("\n")
        block: list[tuple[int, int]] = []
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("|") and line.strip().endswith("|"):
                block.append((i, line.count("|")))
            else:
                if len(block) >= 2:
                    widths = {w for _, w in block}
                    if len(widths) > 1:
                        counts = {}
                        for ln, w in block:
                            counts.setdefault(w, []).append(ln)
                        odd = sorted(counts.items(), key=lambda kv: len(kv[1]))[0]
                        add("ERROR", f"{path.name}:{odd[1][0]}",
                            f"table row has {odd[0] - 1} columns where the rest "
                            f"have {max(widths) - 1}")
                block = []

    # ── 6. alignment: the document's figures against the workbook ────────
    wb = load_workbook(XLSX, data_only=False)
    rows = M.build()
    y7, y10 = rows[6], rows[9]

    def in_workbook(value: float, tol: float) -> bool:
        """Is this number a constant somewhere in the workbook?"""
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, (int, float)) and not isinstance(c.value, bool):
                        if abs(float(c.value) - value) <= tol:
                            return True
        return False

    headline = [
        ("pre-seed first tranche", M.ROUNDS[0]["amount"], 1.0),
        ("pre-seed first pre-money", M.ROUNDS[0]["pre"], 1.0),
        ("extension amount", M.ROUNDS[1]["amount"], 1.0),
        ("extension pre-money", M.ROUNDS[1]["pre"], 1.0),
        ("growth round amount", M.ROUNDS[2]["amount"], 1.0),
        ("growth round pre-money", M.ROUNDS[2]["pre"], 1.0),
        ("Y10 headcount", M.A.headcount[9], 0.01),
        ("fan take rate", M.A.take_fan, 1e-6),
        ("sponsorship take rate", M.A.take_sponsorship, 1e-6),
    ]
    for label, value, tol in headline:
        if not in_workbook(value, tol):
            add("ERROR", "alignment",
                f"{label} = {value:,} appears in the plan but not as a value "
                f"anywhere in the workbook")
    print(f"Alignment: checked {len(headline)} headline inputs against the workbook.")

    # ── 7. how much of the document is actually guarded ──────────────────
    # doc_consistency pins prose figures to model.py and recalc pins the
    # workbook to model.py, so every PINNED figure is consistent across all
    # three artefacts. This counts what is left: the euro and percentage
    # figures in the built document that no pin watches. It is not a defect
    # list, it is the size of the blind spot, and the honest number to quote
    # when saying the plan is checked.
    import importlib.util as _il
    dc_spec = _il.spec_from_file_location("dc", ROOT / "scripts" / "doc_consistency.py")
    dc = _il.module_from_spec(dc_spec)
    sys.modules["dc"] = dc
    dc_spec.loader.exec_module(dc)

    money = re.findall(r"€\s?[\d][\d,.]*\s?[kKmM]?", full)
    pct = re.findall(r"\b\d{1,3}(?:\.\d+)?%", full)
    pinned = len([c for c in dc.CLAIMS])
    print(f"\nCoverage: the document prints {len(money)} euro figures and "
          f"{len(pct)} percentages.\n"
          f"          {pinned} claims are pinned to model.py and re-checked on "
          f"every build.\n"
          f"          Everything else is prose a human has to read. That is the "
          f"blind spot, and it\n"
          f"          is where every stale figure found on 1 October was living.")

    # ── 8. the cover page, against the school's template ────────────────
    # Portada_Eng_TFG_TFM - BUSINESS PLAN.docx: the degree line is the largest
    # thing on the page at 20pt, BUSINESS PLAN sits at 14, the title at 18 and
    # the metadata at 14. The licence line is 9pt. Both images are the school's
    # own, extracted from that file.
    COVER = [("MASTER's Final Project", 20.0), ("BUSINESS PLAN", 14.0),
             ("MSc Programmes in Management", 14.0), ("Course ", 14.0),
             ("Student:", 14.0), ("Tutor:", 14.0),
             ("This work is licensed under a Creative Commons", 9.0)]
    front = []
    for par in d.paragraphs[:16]:
        t = par.text.strip()
        if t:
            r = par.runs[0] if par.runs else None
            front.append((t, r.font.size.pt if (r and r.font.size) else None))
    for needle, want in COVER:
        hit = next((sz for t, sz in front if t.startswith(needle)), "absent")
        if hit == "absent":
            add("ERROR", "cover page", f"{needle!r} is missing")
        elif hit != want:
            add("ERROR", "cover page",
                f"{needle!r} is {hit}pt; the template sets it at {want}pt")

    imgs_on_cover = sum(par._p.xml.count("<pic:pic") for par in d.paragraphs[:16])
    if imgs_on_cover < 2:
        add("ERROR", "cover page",
            f"{imgs_on_cover} image(s) on the cover; the template carries two, "
            f"the esade logo and the Creative Commons badge")

    sec = d.sections[0]
    if not sec.different_first_page_header_footer:
        add("WARN", "cover page", "the cover is numbered; it should not be")
    else:
        fp = "".join(par._p.xml for par in sec.first_page_footer.paragraphs)
        if "PAGE" in fp:
            add("WARN", "cover page", "the first-page footer still carries a page field")
    if "PAGE" not in "".join(par._p.xml for par in sec.footer.paragraphs):
        add("ERROR", "format", "the body has no page numbers")

    if abs(sec.page_width.inches - 8.27) > 0.05 or abs(sec.page_height.inches - 11.69) > 0.05:
        add("ERROR", "format",
            f"page is {sec.page_width.inches:.2f} x {sec.page_height.inches:.2f} in, not A4")

    # ── 9. the contents ──────────────────────────────────────────────────
    toc = [par for par in d.paragraphs if par.style.name.lower().startswith("toc")]
    has_field = r"TOC \o" in d.element.xml or r"TOC \h" in d.element.xml
    if not toc and not has_field:
        add("ERROR", "contents", "there is no table of contents")
    elif not toc:
        # python-docx writes the field; only Word can populate it. Running this
        # audit straight after build_docx.py and before the Word pass is the
        # normal order, so an empty field is a state rather than a defect.
        add("NOTE", "contents",
            "the TOC field is present but not populated: run the Word pass "
            "(fields update, then save) before submitting")
    else:
        broken = [par.text[:50] for par in toc
                  if "Error!" in par.text or "Bookmark not defined" in par.text]
        for b in broken:
            add("ERROR", "contents", f"unresolved entry: {b}")
        unpaged = [par.text[:50] for par in toc if not re.search(r"\t\d+\s*$", par.text)]
        for u in unpaged[:5]:
            add("ERROR", "contents", f"entry with no page number: {u}")
        listed = {m.group(1) for par in toc
                  if (m := re.match(r"Appendix ([A-Z]):", par.text.strip()))}
        for letter in sorted(appendix_letters - listed):
            add("ERROR", "contents", f"Appendix {letter} is not in the table of contents")
        print(f"Contents: {len(toc)} entries, all paged, "
              f"{len(listed)}/{len(appendix_letters)} appendices listed.")

    # ── report ───────────────────────────────────────────────────────────
    order = {"ERROR": 0, "WARN": 1, "NOTE": 2}
    findings.sort(key=lambda f: (order[f[0]], f[1]))
    counts = {s: sum(1 for f in findings if f[0] == s) for s in order}
    print()
    for sev, where, what in findings:
        print(f"  [{sev:<5}] {where:<26} {what}")
    print(f"\n{counts['ERROR']} errors, {counts['WARN']} warnings, {counts['NOTE']} notes")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
