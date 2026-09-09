"""Assemble the submission document as Word, from the markdown the guards watch.

ESADE requires a single document, on their cover page, **under 50 pages
excluding appendices**. This builds it: cover, contents, main body in the order
of the school's own outline, bibliography, then the twelve detailed documents as
appendices, which do not count toward the limit.

Nothing here re-keys a figure. The body is read from `esade-body.md`, whose
numbers are pinned by `scripts/doc_consistency.py` exactly like every other
document, and the charts come from `attachments/charts/`, which
`make_charts.py` renders from the model.

    uv run --with python-docx python business-plan/build_docx.py

Markdown supported, which is the subset the plan actually uses: ATX headings,
paragraphs, pipe tables, bullet and numbered lists, block quotes including
Obsidian-style `> [!note]` callouts, images, horizontal rules, fenced code, and
inline bold/italic/code/links.
"""

from __future__ import annotations

import pathlib
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = pathlib.Path(__file__).resolve().parent
CHARTS = HERE / "attachments" / "charts"

INK = RGBColor(0x1F, 0x29, 0x37)
MUTED = RGBColor(0x6B, 0x72, 0x80)
AMBER = RGBColor(0xD9, 0x77, 0x06)
RULE = "D1D5DB"
CALLOUT_BG = "F6F7F9"

BODY = HERE / "esade-body.md"
APPENDICES: list[tuple[str, str]] = [
    # Only the supporting depth. Operations, HR, Legal/Growth and the primary
    # research are carried in the BODY, in full: the evaluation form weights
    # them at 15%, 15%, 5% and 15%, and an examiner grades what is in front of
    # them rather than hunting an appendix for it.
    ("A", "01-revenue-model.md"),
    ("B", "02-cost-model.md"),
    ("C", "03-financial-model.md"),
    ("D", "04-capital-and-valuation.md"),
    ("E", "05-product-gaps.md"),
    ("F", "06-market-strategy.md"),
    ("G", "07-open-questions.md"),
    ("H", "08-sport-index.md"),
    ("I", "09-analytics-strategy.md"),
    ("J", "10-competitor-tekta.md"),
    ("K", "11-admission-and-matching.md"),
]

INLINE = re.compile(
    r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`|\[\[?[^\]]+?\]\]?\([^)]+?\)|~~.+?~~|==.+?==)")
IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$")
CALLOUT = re.compile(r"^>\s*\[!(\w+)\]\s*(.*)$")
# <!-- INCLUDE: file.md shift=1 --> splices another document into the body and
# demotes its headings, so a rubric-weighted section lives in one file and is
# rendered in two places without being written twice.
INCLUDE = re.compile(r"^<!--\s*INCLUDE:\s*(\S+?)(?:\s+shift=(\d+))?(?:\s+renumber=([\d.]+))?\s*-->$")


# ── low-level docx helpers ──────────────────────────────────────────────────
def shade(el, colour: str) -> None:
    tag = OxmlElement("w:shd")
    tag.set(qn("w:val"), "clear")
    tag.set(qn("w:fill"), colour)
    el.append(tag)


def borders(par, *, left: str | None = None, bottom: str | None = None) -> None:
    pbdr = OxmlElement("w:pBdr")
    for side, colour, size in (("left", left, "18"), ("bottom", bottom, "6")):
        if colour:
            el = OxmlElement(f"w:{side}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), size)
            el.set(qn("w:space"), "8")
            el.set(qn("w:color"), colour)
            pbdr.append(el)
    par._p.get_or_add_pPr().append(pbdr)


def field(par, instr: str) -> None:
    """Insert a Word field (page numbers, table of contents)."""
    run = par.add_run()
    for kind, text in (("begin", None), (None, instr), ("separate", None),
                       (None, ""), ("end", None)):
        if kind:
            fld = OxmlElement("w:fldChar")
            fld.set(qn("w:fldCharType"), kind)
            run._r.append(fld)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)


def inline(par, text: str, *, size: float = 10, colour=INK, bold=False) -> None:
    """Render one line of inline markdown into runs."""
    text = text.replace("&nbsp;", " ")
    for piece in INLINE.split(text):
        if not piece:
            continue
        run = par.add_run()
        run.font.size = Pt(size)
        run.font.color.rgb = colour
        run.bold = bold
        if piece.startswith("**") and piece.endswith("**"):
            run.text, run.bold = piece[2:-2], True
        elif piece.startswith("==") and piece.endswith("=="):
            run.text, run.bold = piece[2:-2], True
            run.font.color.rgb = AMBER
        elif piece.startswith("~~") and piece.endswith("~~"):
            run.text = piece[2:-2]
            run.font.strike = True
        elif piece.startswith("*") and piece.endswith("*") and len(piece) > 2:
            run.text, run.italic = piece[1:-1], True
        elif piece.startswith("`") and piece.endswith("`"):
            run.text = piece[1:-1]
            run.font.name = "Consolas"
            run.font.size = Pt(size - 1)
        elif piece.startswith("["):
            m = re.match(r"\[\[?([^\]]+?)\]?\]\(([^)]+)\)", piece)
            run.text = m.group(1) if m else piece
        else:
            run.text = piece


def spacer(doc, pts: int = 4) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(pts)
    p.paragraph_format.space_before = Pt(0)


# ── the markdown renderer ───────────────────────────────────────────────────
class Renderer:
    def __init__(self, doc: Document, *, appendix: str | None = None,
                 shift: int = 0, renumber: str | None = None):
        self.doc = doc
        self.appendix = appendix
        self.shift = shift
        self.renumber = renumber

    def render(self, md: str) -> None:
        lines = md.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            if not stripped:
                i += 1
                continue

            # fenced code — kept as a monospace block (the process map is one)
            if stripped.startswith("```"):
                block, i = [], i + 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    block.append(lines[i])
                    i += 1
                self.code(block)
                i += 1
                continue

            # tables
            if stripped.startswith("|"):
                block = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    block.append(lines[i].strip())
                    i += 1
                self.table(block)
                continue

            # callouts and quotes
            if stripped.startswith(">"):
                block = []
                while i < len(lines) and lines[i].strip().startswith(">"):
                    block.append(lines[i].strip())
                    i += 1
                self.callout(block)
                continue

            if (m := INCLUDE.match(stripped)):
                src = HERE / m.group(1)
                if src.exists():
                    body = src.read_text(encoding="utf-8")
                    if m.group(3):
                        # in-text cross references move with the headings
                        body = re.sub(r"§\d+\.(\d)", rf"§{m.group(3)}.\1", body)
                    Renderer(self.doc, shift=int(m.group(2) or 0),
                             renumber=m.group(3)).render(body)
                else:
                    print(f"  ! missing include {m.group(1)}", file=sys.stderr)
                i += 1
                continue

            # <!-- MODEL:key --> markers tell the model where to write; they
            # are not text, and rendered as paragraphs they leak the guard's
            # plumbing into the submitted document.
            if stripped.startswith("<!--") and stripped.endswith("-->"):
                i += 1
                continue

            if stripped.startswith("#"):
                self.heading(stripped)
                i += 1
                continue

            if stripped in ("---", "***", "___"):
                spacer(self.doc, 6)
                i += 1
                continue

            if (m := IMAGE.match(stripped)):
                self.image(m.group(2), m.group(1))
                i += 1
                continue

            if re.match(r"^[-*+]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
                block = []
                while i < len(lines) and (
                        re.match(r"^\s*[-*+]\s+", lines[i])
                        or re.match(r"^\s*\d+\.\s+", lines[i])
                        or (lines[i].startswith("  ") and lines[i].strip())):
                    block.append(lines[i])
                    i += 1
                self.list_block(block)
                continue

            # a paragraph: gather until a blank line or a new block starts
            block = []
            while i < len(lines) and lines[i].strip() and not re.match(
                    r"^\s*(#|\||>|```|[-*+]\s|\d+\.\s|---$)", lines[i]):
                block.append(lines[i].strip())
                i += 1
            self.para(" ".join(block))

    # -- blocks ------------------------------------------------------------
    def heading(self, line: str) -> None:
        raw_level = len(line) - len(line.lstrip("#"))
        # An included file carries its own H1 title; the body supplies the
        # numbered heading, so the file's would be a duplicate.
        if self.shift and raw_level == 1:
            return
        level = raw_level + self.shift
        text = line.lstrip("#").strip()
        # An included document numbers its own sections. Spliced into the body
        # it must take the body's number, or section 5 ends up containing
        # subsections 12.1 to 12.11.
        if self.renumber:
            text = re.sub(r"^\d+\.", f"{self.renumber}.", text)
        if self.appendix and level == 1:
            text = f"Appendix {self.appendix} — {re.sub(r'^\d+\s*[—-]\s*', '', text)}"
        sizes = {1: 16, 2: 12.5, 3: 11, 4: 10}
        # A real Word Heading style, not a bold paragraph. Without an outline
        # level the TOC field indexes nothing and the Contents page stays empty
        # however many times it is refreshed.
        par = self.doc.add_paragraph(style=f"Heading {min(level, 4)}")
        par.paragraph_format.space_before = Pt(16 if level <= 2 else 10)
        par.paragraph_format.space_after = Pt(5)
        par.paragraph_format.keep_with_next = True
        inline(par, text, size=sizes.get(level, 10), bold=True,
               colour=INK if level <= 2 else MUTED)
        if level == 1:
            borders(par, bottom=RULE)

    def para(self, text: str) -> None:
        if not text:
            return
        par = self.doc.add_paragraph()
        par.paragraph_format.space_after = Pt(7)
        par.paragraph_format.line_spacing = 1.15
        par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        inline(par, text)

    def list_block(self, block: list[str]) -> None:
        # Join continuation lines onto their marker first. Rendered one line at
        # a time, a wrapped item became several bullets.
        merged: list[str] = []
        for raw in block:
            if re.match(r"^\s*([-*+]|\d+\.)\s+", raw) or not merged:
                merged.append(raw.rstrip())
            else:
                merged[-1] += " " + raw.strip()
        for raw in merged:
            text = raw.strip()
            if not text:
                continue
            ordered = bool(re.match(r"^\d+\.\s+", text))
            text = re.sub(r"^([-*+]|\d+\.)\s+", "", text)
            indent = 1 if raw.startswith("  ") else 0
            par = self.doc.add_paragraph(
                style="List Number" if ordered else "List Bullet")
            par.paragraph_format.space_after = Pt(3)
            par.paragraph_format.left_indent = Cm(0.6 + 0.5 * indent)
            par.paragraph_format.line_spacing = 1.1
            inline(par, text)

    def table(self, block: list[str]) -> None:
        rows = [[c.strip() for c in r.strip("|").split("|")] for r in block]
        rows = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
        if not rows:
            return
        width = max(len(r) for r in rows)
        rows = [r + [""] * (width - len(r)) for r in rows]

        tbl = self.doc.add_table(rows=len(rows), cols=width)
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = True
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                target = tbl.cell(r, c)
                target.text = ""
                par = target.paragraphs[0]
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.space_before = Pt(2)
                inline(par, cell, size=8.5, bold=(r == 0))
                if r == 0:
                    shade(target._tc.get_or_add_tcPr(), "EFF1F3")
        spacer(self.doc, 8)

    def callout(self, block: list[str]) -> None:
        first = block[0]
        kind, head = "quote", ""
        if (m := CALLOUT.match(first)):
            kind, head = m.group(1).lower(), m.group(2)
            block = block[1:]
        body = [re.sub(r"^>\s?", "", b) for b in block]
        text = " ".join(b.strip() for b in body if b.strip())

        if head:
            par = self.doc.add_paragraph()
            par.paragraph_format.space_before = Pt(8)
            par.paragraph_format.space_after = Pt(1)
            par.paragraph_format.left_indent = Cm(0.4)
            par.paragraph_format.keep_with_next = True
            shade(par._p.get_or_add_pPr(), CALLOUT_BG)
            borders(par, left="D97706" if kind in
                    ("important", "danger", "warning") else "9CA3AF")
            inline(par, head, size=9.5, bold=True,
                   colour=AMBER if kind in ("important", "danger", "warning") else INK)
        if text:
            par = self.doc.add_paragraph()
            par.paragraph_format.space_before = Pt(0 if head else 8)
            par.paragraph_format.space_after = Pt(8)
            par.paragraph_format.left_indent = Cm(0.4)
            par.paragraph_format.line_spacing = 1.1
            shade(par._p.get_or_add_pPr(), CALLOUT_BG)
            borders(par, left="D97706" if kind in
                    ("important", "danger", "warning") else "9CA3AF")
            inline(par, text, size=9.5)

    def code(self, block: list[str]) -> None:
        par = self.doc.add_paragraph()
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.space_after = Pt(8)
        par.paragraph_format.left_indent = Cm(0.3)
        shade(par._p.get_or_add_pPr(), CALLOUT_BG)
        run = par.add_run("\n".join(block))
        run.font.name = "Consolas"
        run.font.size = Pt(6.5)
        run.font.color.rgb = INK

    def image(self, src: str, caption: str) -> None:
        path = (HERE / src) if not pathlib.Path(src).is_absolute() else pathlib.Path(src)
        if not path.exists():
            path = CHARTS / pathlib.Path(src).name
        if not path.exists():
            print(f"  ! missing image {src}", file=sys.stderr)
            return
        par = self.doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_before = Pt(6)
        par.paragraph_format.space_after = Pt(2)
        par.add_run().add_picture(str(path), width=Cm(16.0))
        if caption:
            cap = self.doc.add_paragraph()
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            cap.paragraph_format.space_after = Pt(10)
            inline(cap, caption, size=8, colour=MUTED)


# ── document furniture ──────────────────────────────────────────────────────
def page_setup(doc: Document) -> None:
    for section in doc.sections:
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.left_margin = section.right_margin = Cm(2.5)
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.0)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)
    style.font.color.rgb = INK


def cover(doc: Document, title: str, student: str, tutor: str, course: str) -> None:
    for _ in range(4):
        spacer(doc, 10)
    for text, size, bold, colour in (
            ("BACHELOR/MASTER's Final Project", 12, False, MUTED),
            ("BUSINESS PLAN", 26, True, INK)):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(6)
        inline(par, text, size=size, bold=bold, colour=colour)

    spacer(doc, 26)
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    par.paragraph_format.space_after = Pt(30)
    inline(par, title, size=15, bold=True)

    for label, value in (("MSc Programmes in Management", ""),
                         (f"Course {course}", ""),
                         ("", ""),
                         ("Student:", student),
                         ("Tutor:", tutor)):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.space_after = Pt(5)
        if value:
            inline(par, f"{label} ", size=10.5, colour=MUTED)
            inline(par, value, size=10.5, bold=True)
        elif label:
            inline(par, label, size=10.5, colour=MUTED)

    spacer(doc, 30)
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    inline(par, "This work is licensed under a Creative Commons "
                "Attribution-NonCommercial-NoDerivatives 4.0 International License.",
           size=7.5, colour=MUTED)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def contents(doc: Document) -> None:
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(10)
    inline(par, "Contents", size=16, bold=True)
    borders(par, bottom=RULE)

    par = doc.add_paragraph()
    field(par, r'TOC \o "1-2" \h \z \u')

    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(14)
    inline(par, "Word populates this table on opening the document: right-click "
                "anywhere in it and choose Update Field, or press F9.",
           size=8, colour=MUTED)
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def footer(doc: Document) -> None:
    for section in doc.sections:
        par = section.footer.paragraphs[0]
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        inline(par, "", size=8.5, colour=MUTED)
        field(par, "PAGE")


def main() -> int:
    # --body-only writes the main document without appendices, which is what
    # the school's 50-page limit actually applies to.
    body_only = "--body-only" in sys.argv
    if not BODY.exists():
        print(f"{BODY.name} not found", file=sys.stderr)
        return 1

    doc = Document()
    page_setup(doc)
    footer(doc)

    cover(doc,
          title="Stride: A Business Plan for an Athlete Monetisation "
                "Platform Built on Analytics",
          student="Jad Zoghaib", tutor="Ignacio Gallardo Albajar",
          course="2025-2026")
    contents(doc)

    Renderer(doc).render(BODY.read_text(encoding="utf-8"))

    if body_only:
        out = HERE / "_body_only.docx"
        doc.save(out)
        print(f"wrote {out.name} (main body, no appendices)")
        return 0

    # ── appendices, which do not count toward the 50 pages ────────────────
    doc.add_section(WD_SECTION.NEW_PAGE)
    page_setup(doc)
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(10)
    inline(par, "Appendices", size=18, bold=True)
    borders(par, bottom=RULE)
    par = doc.add_paragraph()
    par.paragraph_format.space_after = Pt(14)
    inline(par, "The detailed working behind the plan. Every figure in these "
                "documents is generated by the financial model and checked by "
                "the consistency guard described in Appendix C.",
           size=9.5, colour=MUTED)

    for letter, name in APPENDICES:
        path = HERE / name
        if not path.exists():
            print(f"  ! missing appendix {name}", file=sys.stderr)
            continue
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        Renderer(doc, appendix=letter).render(path.read_text(encoding="utf-8"))
        print(f"  appendix {letter}: {name}")

    out = HERE / "Stride_Business_Plan.docx"
    doc.save(out)
    print(f"\nwrote {out.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
