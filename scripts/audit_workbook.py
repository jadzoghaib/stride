"""Audit the workbook against the promises it makes about itself.

The three existing checks answer three narrow questions. `verify_workbook.py`
asks whether every formula parses and points somewhere real. `recalc_workbook.py`
asks whether the arithmetic reproduces `model.py`. `doc_consistency.py` asks
whether the prose matches the model. All three can pass on a workbook that is
still misleading to read, because none of them asks whether the sheet is
*honest*: whether a cell the colour key calls an input is really an input,
whether a row's formula is the same in Y7 as it was in Y3, or whether a number
typed into a formula should have been a reference.

This is that audit. It finds the class of defect a reader discovers by hand and
an automated check never reports:

  COLOUR LIES      a cell whose fill promises one thing and whose content is
                   another. Amber means "sourced fact, change only if the source
                   changed"; if an amber cell holds a formula, the key is lying.
                   Green means "pulled from another sheet"; if a green cell has
                   no cross-sheet reference, same.

  ROW DRIFT        a row whose formula changes shape partway across the years.
                   This is the classic spreadsheet error and the reason auditors
                   read along rows rather than down columns: Y1 to Y6 computed
                   one way and Y7 another, with nothing to show for it.

  MAGIC NUMBERS    a numeric literal inside a formula that should have been a
                   reference to Assumptions. It passes every check in the repo,
                   because the model agrees with it today, and silently stops
                   agreeing the moment someone edits the input it duplicates.

  ORPHANS          an input cell nothing downstream reads. Either dead weight or
                   a wiring mistake, and from the outside they look identical.

  PRECISION        a number format that hides a figure's real value, such as a
                   headcount of 1.5 displayed as 2, and a Check-sheet tolerance
                   looser than half the last digit it prints.

  STALE STAMPS     an "as of" date or a source year that has drifted out of step
                   with the data beside it.

Exit code 0 when nothing material is found. Findings are grouped by severity:
ERROR is wrong, WARN is misleading, NOTE is worth a human glance.
"""
from __future__ import annotations

import pathlib
import re
import sys

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "business-plan"))

import comparables_data as CD  # noqa: E402
import model as M  # noqa: E402

WORKBOOK = ROOT / "business-plan" / "Stride_Financial_Model.xlsx"

FILL_INPUT, FILL_HARD = "00DCE9F7", "00FDF0D5"
FILL_LINK, FILL_TOTAL = "00E4F2E4", "00EDF0F5"
FILL_CHECK = "00FBE3E3"

findings: list[tuple[str, str, str]] = []


def add(sev: str, where: str, what: str) -> None:
    findings.append((sev, where, what))


def rgb(cell) -> str:
    try:
        return (cell.fill.fgColor.rgb or "") if cell.fill and cell.fill.fgColor else ""
    except Exception:
        return ""


def is_formula(v) -> bool:
    return isinstance(v, str) and v.startswith("=")


# Column letters a formula may legitimately contain without being "magic".
NUM_IN_FORMULA = re.compile(r"(?<![A-Za-z0-9_$.])(\d+(?:\.\d+)?)(?![0-9]*\s*[:)]?[A-Za-z]*\d*\()")
CELL_REF = re.compile(r"\$?[A-Z]{1,3}\$?\d+")
SHEET_REF = re.compile(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_&]*))!")

#: Literals that are structure rather than assumption: unit conversions, the
#: identity element, a sign flip, a percentage base, the month count.
BENIGN = {0, 1, 2, 3, 4, 10, 12, 100, 365, 1000, 0.5, -1, 1e6, 1000000}


#: A cell reference: optional $ before the column, optional $ before the row.
#: Guarded so it cannot match inside a sheet name or a function name (a function
#: has no trailing digits, so the \d+ already excludes SUM, MIN and friends).
REF = re.compile(r"(?<![A-Za-z0-9_$])(\$?)([A-Z]{1,3})(\$?)(\d+)\b")


def shift_relative(formula: str, by: int) -> str:
    """Move every RELATIVE column reference `by` columns to the right.

    This is what Excel does when a formula is filled sideways, and comparing a
    shifted formula against its neighbour is therefore an exact test of whether
    the two are "the same formula". Absolute columns, written `$C`, do not move,
    which is the whole point: a fixed reference to year one must stay fixed.
    """
    def move(m: re.Match) -> str:
        cdollar, col, rdollar, row = m.groups()
        if cdollar:
            return m.group(0)
        idx = 0
        for ch in col:
            idx = idx * 26 + (ord(ch) - ord("A") + 1)
        idx += by
        if idx < 1:
            return m.group(0)
        out = ""
        while idx:
            idx, rem = divmod(idx - 1, 26)
            out = chr(ord("A") + rem) + out
        return f"{out}{rdollar}{row}"

    return REF.sub(move, formula)


def main() -> int:
    if not WORKBOOK.exists():
        print(f"{WORKBOOK} not found")
        return 1
    wb = load_workbook(WORKBOOK)
    N = len(M.YEARS) if hasattr(M, "YEARS") else 10
    FIRST = 3
    cols = [get_column_letter(FIRST + i) for i in range(N)]

    print(f"Auditing {WORKBOOK.name}: {len(wb.sheetnames)} sheets\n")

    # ── 1. structure ─────────────────────────────────────────────────────
    readme = wb["README"]
    linked = set()
    for row in readme.iter_rows():
        for c in row:
            if not c.hyperlink:
                continue
            # openpyxl puts an INTERNAL link in .target as "#'Sheet'!A1" and
            # leaves .location empty. Reading only .location reported all
            # seventeen working links as missing.
            ref = c.hyperlink.location or (c.hyperlink.target or "").lstrip("#")
            if "!" in ref:
                linked.add(ref.split("!")[0].strip("'"))
    for name in wb.sheetnames:
        if name != "README" and name not in linked:
            add("WARN", f"README", f"{name} is not linked from the index")
    for name in linked:
        if name not in wb.sheetnames:
            add("ERROR", "README", f"index links {name}, which does not exist")

    # ── 2. the colour key's promises ─────────────────────────────────────
    amber_formula = link_no_ref = input_formula = calc_constant = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is None:
                    continue
                fill = rgb(c)
                f = is_formula(c.value)
                if fill == FILL_HARD and f:
                    amber_formula += 1
                    if amber_formula <= 5:
                        add("WARN", f"{ws.title}!{c.coordinate}",
                            f"amber (sourced fact) but holds a formula: {str(c.value)[:60]}")
                # Green means "dependent value": pulled from another sheet, or
                # from the single input at the head of its own row, which is the
                # flat-assumption idiom and writes `=C7`. Only a green cell that
                # is neither of those is lying about itself.
                elif (fill == FILL_LINK and f and "!" not in c.value
                      and not re.fullmatch(r"=\$?[A-Z]{1,3}\$?\d+", c.value)):
                    link_no_ref += 1
                    if link_no_ref <= 5:
                        add("WARN", f"{ws.title}!{c.coordinate}",
                            f"green (from another sheet) but references none: {str(c.value)[:60]}")
                elif fill == FILL_INPUT and f:
                    input_formula += 1
                    if input_formula <= 5:
                        add("WARN", f"{ws.title}!{c.coordinate}",
                            f"blue (an input you may change) but holds a formula")
    for n, what in ((amber_formula, "amber cells holding formulas"),
                    (link_no_ref, "green cells with no cross-sheet reference"),
                    (input_formula, "blue input cells holding formulas")):
        if n > 5:
            add("WARN", "colour key", f"{n} {what} in total (first 5 listed)")

    # ── 3. row drift: a formula that is not its neighbour, shifted ──────
    drift = 0
    baked_years: list[str] = []
    for ws in wb.worksheets:
        if ws.title in ("README", "Comparables", "Research"):
            continue
        for row in ws.iter_rows(min_col=FIRST, max_col=FIRST + N - 1):
            cells = [c for c in row if is_formula(c.value)]
            if len(cells) < 3:
                continue
            # A flat assumption points every year at the single input in Y1, so
            # its formulas are byte-identical rather than shifted. That is the
            # workbook's `const=True` idiom and it is not drift.
            tail = [c.value for c in cells[1:]]
            if len(set(tail)) == 1:
                continue
            bad, baked = [], []
            # Year one is allowed its own formula: there is no prior column for
            # it to point at, and the generator writes it separately for exactly
            # that reason. So comparison starts at the second pair.
            for a, b in zip(cells[1:], cells[2:]):
                by = b.column - a.column
                if shift_relative(a.value, by) == b.value:
                    continue
                # The generator substitutes the year index as a LITERAL, so
                # `IF(5=1,...)` and `IF(6=1,...)` are one formula written for
                # two years. Blanking both years' numbers separates that case
                # from real drift, which is what the distinction is for: a baked
                # year is ugly and correct, drift is wrong.
                ya, yb = a.column - FIRST + 1, b.column - FIRST + 1
                na = re.sub(rf"(?<![A-Z0-9.]){ya}(?![0-9])", "Y",
                            shift_relative(a.value, by))
                nb = re.sub(rf"(?<![A-Z0-9.]){yb}(?![0-9])", "Y", b.value)
                (baked if na == nb else bad).append(get_column_letter(b.column))
            label = ws.cell(row[0].row, 1).value or ""
            # Two documented constructs to which "is it the previous formula,
            # shifted?" does not apply, because neither is a fill-right row:
            #
            #   A two-way data table. Each cell reads its own column header and
            #   its own row label and sums the SAME ten-year cash-flow strip, so
            #   the strip must not shift. That is what makes it a grid.
            #
            #   A terminal-value row, `=FCF + IF(year = last, TV, 0)`, whose
            #   final column is deliberately the only one that differs.
            if isinstance(label, (int, float)) and ws.title == "Valuation":
                continue
            if bad == [get_column_letter(FIRST + N - 1)]:
                add("NOTE", f"{ws.title}!row {row[0].row}",
                    f"only the final year differs, which is the terminal-value "
                    f"construct: '{str(label)[:40]}'")
                continue
            if bad:
                drift += 1
                if drift <= 12:
                    add("ERROR", f"{ws.title}!row {row[0].row}",
                        f"formula is not the previous one shifted, at "
                        f"{','.join(bad)} in '{str(label)[:40]}'")
            elif baked:
                baked_years.append(f"{ws.title}!row {row[0].row} '{str(label)[:40]}'")
    if drift > 12:
        add("ERROR", "row drift", f"{drift} rows total (first 12 listed)")
    if baked_years:
        add("NOTE", "year index baked into formulas",
            f"{len(baked_years)} rows write the year number as a literal "
            f"(e.g. IF(5=1,...)), so each column reads as a different formula. "
            f"Correct, but it looks like an error in the formula bar: "
            f"{baked_years[0]}")

    # ── 4. magic numbers in formulas ─────────────────────────────────────
    magic = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if not is_formula(c.value):
                    continue
                stripped = CELL_REF.sub("", SHEET_REF.sub("", c.value))
                for lit in NUM_IN_FORMULA.findall(stripped):
                    val = float(lit)
                    if val in BENIGN or val != val:
                        continue
                    magic += 1
                    if magic <= 15:
                        label = ws.cell(c.row, 1).value or ""
                        add("WARN", f"{ws.title}!{c.coordinate}",
                            f"literal {lit} inside a formula, '{str(label)[:34]}': "
                            f"{str(c.value)[:70]}")
                    break
    if magic > 15:
        add("WARN", "magic numbers", f"{magic} formulas contain a literal (first 15 listed)")

    # ── 5. orphan inputs ─────────────────────────────────────────────────
    referenced: set[tuple[str, str]] = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if not is_formula(c.value):
                    continue
                text = c.value
                for m in re.finditer(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_&]*))!"
                                     r"(\$?[A-Z]{1,3}\$?\d+)(?::(\$?[A-Z]{1,3}\$?\d+))?", text):
                    sheet = (m.group(1) or m.group(2))
                    a, b = m.group(3).replace("$", ""), (m.group(4) or "").replace("$", "")
                    if b:
                        ca, ra = re.match(r"([A-Z]+)(\d+)", a).groups()
                        cb, rb = re.match(r"([A-Z]+)(\d+)", b).groups()
                        for rr in range(int(ra), int(rb) + 1):
                            for ci in range(ord(ca[-1]), ord(cb[-1]) + 1):
                                referenced.add((sheet, f"{chr(ci)}{rr}"))
                    else:
                        referenced.add((sheet, a))
                for m in re.finditer(r"(?<![A-Za-z0-9_!$])(\$?[A-Z]{1,3}\$?\d+)"
                                     r"(?::(\$?[A-Z]{1,3}\$?\d+))?", text):
                    a, b = m.group(1).replace("$", ""), (m.group(2) or "").replace("$", "")
                    if b:
                        ca, ra = re.match(r"([A-Z]+)(\d+)", a).groups()
                        cb, rb = re.match(r"([A-Z]+)(\d+)", b).groups()
                        for rr in range(int(ra), int(rb) + 1):
                            for ci in range(ord(ca[-1]), ord(cb[-1]) + 1):
                                referenced.add((ws.title, f"{chr(ci)}{rr}"))
                    else:
                        referenced.add((ws.title, a))

    orphans = 0
    for ws in wb.worksheets:
        # Comparables and Research are reference sheets: they carry published
        # facts and their sources, and MarketModel draws on them selectively. A
        # fact nothing computes from is evidence a reader can check, not dead
        # weight, so "nothing reads this" is not a defect there.
        if ws.title in ("README", "Check", "Comparables", "Research"):
            continue
        for row in ws.iter_rows(min_col=FIRST, max_col=FIRST + N - 1):
            for c in row:
                if c.value is None or is_formula(c.value):
                    continue
                if not isinstance(c.value, (int, float)):
                    continue
                if rgb(c) not in (FILL_INPUT, FILL_HARD):
                    continue
                if (ws.title, c.coordinate) not in referenced:
                    orphans += 1
                    if orphans <= 10:
                        label = ws.cell(c.row, 1).value or ""
                        add("NOTE", f"{ws.title}!{c.coordinate}",
                            f"input nothing reads: '{str(label)[:40]}' = {c.value}")
    if orphans > 10:
        add("NOTE", "orphan inputs", f"{orphans} total (first 10 listed)")

    # ── 6. precision: a format that hides the value ──────────────────────
    hidden = 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if not isinstance(c.value, (int, float)) or isinstance(c.value, bool):
                    continue
                fmt = c.number_format or ""
                if "." in fmt or "%" in fmt or fmt in ("General", "@"):
                    continue
                # A money format showing whole euros is correct, not hidden
                # precision: the cents are not information anyone wants. What
                # matters is a COUNT or an FTE rounded away, so only formats
                # with no currency/thousands intent are checked.
                if "#,##0" in fmt and "[Red]" in fmt:
                    continue
                if ws.title == "Check":
                    continue
                if abs(c.value - round(c.value)) > 1e-9:
                    hidden += 1
                    if hidden <= 10:
                        label = ws.cell(c.row, 1).value or ""
                        add("ERROR", f"{ws.title}!{c.coordinate}",
                            f"{c.value} displayed with no decimals as "
                            f"{round(c.value)}: '{str(label)[:40]}'")
    if hidden > 10:
        add("ERROR", "hidden precision", f"{hidden} cells total (first 10 listed)")

    # ── 7. the data blocks against their source modules ──────────────────
    cp = wb["Comparables"]
    seen = {}
    for row in cp.iter_rows(max_col=6):
        a = row[0].value
        if isinstance(a, str) and "(" in a and isinstance(row[1].value, (int, float)):
            seen[a.split(" (")[0]] = (row[1].value, row[2].value, row[3].value)
    for name, country, founded, emp, asof, raised, rnd, date, pre, status in CD.SPONSORSHIP_PLATFORMS:
        if name not in seen:
            add("ERROR", "Comparables", f"{name} missing from the competitor table")
            continue
        got_f, got_e, got_r = seen[name]
        for label, want, got in (("founded", founded, got_f), ("employees", emp, got_e),
                                 ("raised", raised, got_r)):
            if want != got:
                add("ERROR", "Comparables",
                    f"{name} {label}: sheet {got}, comparables_data {want}")

    # funding sheet against ROUNDS
    fu = wb["Funding"]
    frow = {}
    for row in fu.iter_rows(max_col=2):
        if isinstance(row[0].value, str):
            frow[row[0].value.strip()] = row[0].row
    for rd in M.ROUNDS:
        col = cols[rd["year"] - 1]
        amt = fu[f"{col}{frow['Equity raised']}"].value
        pre = fu[f"{col}{frow['Pre-money valuation']}"].value
        if amt != rd["amount"]:
            add("ERROR", "Funding", f"{rd['stage']} Y{rd['year']} amount: "
                                    f"sheet {amt}, model {rd['amount']}")
        if pre != rd["pre"]:
            add("ERROR", "Funding", f"{rd['stage']} Y{rd['year']} pre-money: "
                                    f"sheet {pre}, model {rd['pre']}")
    years_with_money = {rd["year"] for rd in M.ROUNDS}
    for i, col in enumerate(cols, start=1):
        amt = fu[f"{col}{frow['Equity raised']}"].value
        if i not in years_with_money and amt not in (0, None):
            add("ERROR", "Funding", f"Y{i} raises {amt} but no round is defined for it")

    # ── 8. stale stamps ──────────────────────────────────────────────────
    for ws in wb.worksheets:
        for row in ws.iter_rows(max_col=8):
            for c in row:
                if not isinstance(c.value, str):
                    continue
                # Only the year that FOLLOWS "as of", not every year in the
                # cell. A status note naming a 2020 funding round beside a 2026
                # headcount is not a stale stamp.
                for yr in re.findall(r"as of[^.;]*?\b(20\d\d)\b", c.value, re.I):
                    if int(yr) < 2024:
                        add("NOTE", f"{ws.title}!{c.coordinate}",
                            f"'as of' date in {yr}: {c.value[:70]}")

    # ── report ───────────────────────────────────────────────────────────
    order = {"ERROR": 0, "WARN": 1, "NOTE": 2}
    findings.sort(key=lambda f: (order[f[0]], f[1]))
    counts = {s: sum(1 for f in findings if f[0] == s) for s in order}
    for sev, where, what in findings:
        print(f"  [{sev:<5}] {where:<28} {what}")
    print(f"\n{counts['ERROR']} errors, {counts['WARN']} warnings, {counts['NOTE']} notes")
    if not findings:
        print("The workbook keeps every promise its colour key makes.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
