"""Static checks on the generated workbook, for a machine with no Excel on it.

    python scripts/verify_workbook.py

The workbook is the deliverable a reader opens in Excel, and this repository
cannot open it. An earlier version of this check confirmed that every reference
pointed at a cell holding something — which it did — and reported the file
clean. It was not: forty formulas said `=P&L!C21`, which Excel cannot parse at
all because the sheet token ends at the ampersand. openpyxl stores that string
without complaint and a reference-resolution pass walks straight over it.

So this checks the things that actually break a spreadsheet:

    1. DANGLING     a reference to a cell that holds nothing — a silent zero
    2. QUOTING      a sheet name Excel cannot read bare, unquoted
    3. SELF-REF     a formula that names its own cell, including inside an IF
                    branch that never runs; Excel's dependency graph does not
                    care which branch is taken and calls it circular
    4. SYNTAX       anything the formula tokenizer cannot read

Exit code is non-zero if any of them fire.
"""

from __future__ import annotations

import pathlib
import re
import sys

from openpyxl import load_workbook
from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils import column_index_from_string

WORKBOOK = pathlib.Path(__file__).resolve().parents[1] / "business-plan" / "Stride_Financial_Model.xlsx"

# A sheet name may be used unquoted only if it is a plain identifier.
BARE_SHEET = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")
# sheet-qualified reference, quoted or not
QUALIFIED = re.compile(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_.&]*))!(\$?[A-Z]{1,3}\$?\d{1,5})")
# any A1 reference
LOCAL = re.compile(r"(?<![A-Z0-9$!'])(\$?)([A-Z]{1,3})(\$?)(\d{1,5})(?![0-9(])")


def main() -> int:
    if not WORKBOOK.exists():
        print(f"no workbook at {WORKBOOK} — run business-plan/build_workbook.py first")
        return 1
    wb = load_workbook(WORKBOOK)
    names = set(wb.sheetnames)
    problems: list[str] = []
    formulas = refs = 0

    for ws in wb.worksheets:
        for line in ws.iter_rows():
            for cell in line:
                value = cell.value
                if not (isinstance(value, str) and value.startswith("=")):
                    continue
                formulas += 1
                here = f"{ws.title}!{cell.coordinate}"

                # 4. syntax
                try:
                    Tokenizer(value)
                except Exception as exc:
                    problems.append(f"SYNTAX   {here}: {exc}  [{value[:70]}]")
                    continue

                # 2. quoting — a bare sheet token that Excel cannot read
                for quoted, bare, _ in QUALIFIED.findall(value):
                    if bare and not BARE_SHEET.match(bare):
                        problems.append(
                            f"QUOTING  {here}: sheet {bare!r} must be quoted  [{value[:70]}]")
                    target = quoted or bare
                    if target and target not in names:
                        # a bare token that is not a sheet at all is a local ref
                        continue

                # 1. dangling
                for quoted, bare, coord in QUALIFIED.findall(value):
                    target = quoted or bare
                    if target not in names:
                        continue
                    col, row_no = re.match(r"\$?([A-Z]{1,3})\$?(\d+)", coord).groups()
                    refs += 1
                    if wb[target].cell(int(row_no), column_index_from_string(col)).value is None:
                        problems.append(f"DANGLING {here} -> empty {target}!{coord}")

                # 3. self-reference, after removing the cross-sheet references
                local_only = QUALIFIED.sub(" ", value)
                for _, col, _, row_no in LOCAL.findall(local_only):
                    refs += 1
                    if col == cell.column_letter and int(row_no) == cell.row:
                        problems.append(
                            f"SELF-REF {here}: names its own cell — Excel calls this "
                            f"circular even in an untaken IF branch  [{value[:70]}]")
                    elif wb[ws.title].cell(int(row_no), column_index_from_string(col)).value is None:
                        problems.append(f"DANGLING {here} -> empty {ws.title}!{col}{row_no}")

    print(f"{WORKBOOK.name}: {formulas:,} formulas, {refs:,} references")
    if problems:
        kinds: dict[str, int] = {}
        for pr in problems:
            kinds[pr.split()[0]] = kinds.get(pr.split()[0], 0) + 1
        print(f"\n{len(problems)} problems: " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        for pr in problems[:25]:
            print("  -", pr)
        if len(problems) > 25:
            print(f"  ... and {len(problems) - 25} more")
        return 1
    print("no dangling references, no unquoted sheet names, nothing circular, "
          "every formula parses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
