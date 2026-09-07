"""Calculate every formula in the workbook, and check what it computes.

`verify_workbook.py` proves the workbook is structurally sound: references
resolve, no cycles, every formula parses. That is not the same as proving it
*computes the right numbers*, and the difference matters more than it sounds.

openpyxl writes formulas but never evaluates them, so a workbook built this way
ships with no cached values at all -- every cell is a formula string and nothing
has ever run it. The workbook carries a Check sheet whose VARIANCE rows compare
Excel's own answers against model.py and are documented as "must be zero", but
those rows are themselves formulas: until a spreadsheet application opens the
file, nobody has ever computed them. The check existed and had never once run.

This module runs it. It is a small Excel evaluator -- the workbook uses nine
functions across 2,010 formulas, which is a small enough vocabulary to implement
exactly rather than depend on a library (the obvious ones pull in scipy, which
this machine's Application Control blocks anyway).

    python scripts/recalc_workbook.py

Exit code 0 when every formula evaluates and every VARIANCE row is zero.
"""

from __future__ import annotations

import decimal
import math
import pathlib
import re
import sys
from dataclasses import dataclass

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "business-plan" / "Stride_Financial_Model.xlsx"


# ── the tiny AST ────────────────────────────────────────────────────────────
@dataclass
class Num:
    value: float


@dataclass
class Str:
    value: str


@dataclass
class Ref:
    sheet: str | None
    col: int
    row: int


@dataclass
class Rng:
    start: Ref
    end: Ref


@dataclass
class Call:
    name: str
    args: list


@dataclass
class Bin:
    op: str
    left: object
    right: object


@dataclass
class Neg:
    operand: object


_TOKEN = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<sheet>'[^']+'!|[A-Za-z_][A-Za-z0-9_.]*!)
  | (?P<func>[A-Z][A-Z0-9.]*\()
  | (?P<cell>\$?[A-Z]{1,3}\$?[0-9]{1,5})
  | (?P<num>[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)
  | (?P<str>"[^"]*")
  | (?P<op><>|<=|>=|[-+*/^&<>=,():])
    """,
    re.VERBOSE,
)


def tokenize(formula: str) -> list[tuple[str, str]]:
    out, pos = [], 0
    while pos < len(formula):
        m = _TOKEN.match(formula, pos)
        if not m:
            raise ValueError(f"cannot tokenize at {formula[pos:pos + 20]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind != "ws":
            out.append((kind, m.group()))
    return out


class Parser:
    """Recursive descent, precedence climbing. Small because the input is."""

    def __init__(self, tokens: list[tuple[str, str]]):
        self.toks = tokens
        self.i = 0

    def peek(self) -> tuple[str, str] | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self) -> tuple[str, str]:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, text: str) -> None:
        kind, value = self.take()
        if value != text:
            raise ValueError(f"expected {text!r}, found {value!r}")

    def parse(self):
        node = self.comparison()
        if self.peek() is not None:
            raise ValueError(f"trailing tokens at {self.peek()}")
        return node

    def comparison(self):
        node = self.additive()
        while (tok := self.peek()) and tok[1] in ("=", "<>", "<", ">", "<=", ">="):
            node = Bin(self.take()[1], node, self.additive())
        return node

    def additive(self):
        node = self.multiplicative()
        while (tok := self.peek()) and tok[1] in ("+", "-", "&"):
            node = Bin(self.take()[1], node, self.multiplicative())
        return node

    def multiplicative(self):
        node = self.unary()
        while (tok := self.peek()) and tok[1] in ("*", "/"):
            node = Bin(self.take()[1], node, self.unary())
        return node

    def unary(self):
        tok = self.peek()
        if tok and tok[1] == "-":
            self.take()
            return Neg(self.unary())
        if tok and tok[1] == "+":
            self.take()
            return self.unary()
        return self.power()

    def power(self):
        node = self.atom()
        while (tok := self.peek()) and tok[1] == "^":
            self.take()
            node = Bin("^", node, self.atom())
        return node

    def atom(self):
        kind, value = self.take()
        if kind == "num":
            return Num(float(value))
        if kind == "str":
            return Str(value[1:-1])
        if kind == "func":
            name, args = value[:-1], []
            if (tok := self.peek()) and tok[1] == ")":
                self.take()
                return Call(name, args)
            while True:
                args.append(self.comparison())
                kind2, value2 = self.take()
                if value2 == ")":
                    return Call(name, args)
                if value2 != ",":
                    raise ValueError(f"expected , or ) in {name}, found {value2!r}")
        if value == "(":
            node = self.comparison()
            self.expect(")")
            return node
        if kind == "sheet":
            sheet = value[:-1].strip("'")
            return self.reference(sheet)
        if kind == "cell":
            self.i -= 1
            return self.reference(None)
        raise ValueError(f"unexpected token {value!r}")

    def reference(self, sheet: str | None):
        start = self._cell(sheet)
        if (tok := self.peek()) and tok[1] == ":":
            self.take()
            nxt = self.peek()
            if nxt and nxt[0] == "sheet":
                self.take()
            return Rng(start, self._cell(sheet))
        return start

    def _cell(self, sheet: str | None) -> Ref:
        kind, value = self.take()
        if kind != "cell":
            raise ValueError(f"expected a cell reference, found {value!r}")
        plain = value.replace("$", "")
        letters = re.match(r"[A-Z]+", plain).group()
        return Ref(sheet, column_index_from_string(letters), int(plain[len(letters):]))


# ── evaluation ──────────────────────────────────────────────────────────────
class Calculator:
    def __init__(self, path: pathlib.Path):
        self.wb = load_workbook(path)
        self.cache: dict[tuple[str, int, int], object] = {}
        self.stack: set[tuple[str, int, int]] = set()
        self.errors: list[str] = []

    # -- cells -------------------------------------------------------------
    def cell(self, sheet: str, col: int, row: int):
        key = (sheet, col, row)
        if key in self.cache:
            return self.cache[key]
        if key in self.stack:
            raise ValueError(f"circular reference at {sheet}!{get_column_letter(col)}{row}")
        raw = self.wb[sheet].cell(row=row, column=col).value
        if raw is None:
            value: object = 0.0
        elif isinstance(raw, str) and raw.startswith("="):
            self.stack.add(key)
            try:
                value = self.evaluate(Parser(tokenize(raw[1:])).parse(), sheet)
            finally:
                self.stack.discard(key)
        elif isinstance(raw, bool):
            value = float(raw)
        elif isinstance(raw, (int, float)):
            value = float(raw)
        else:
            value = raw
        self.cache[key] = value
        return value

    def flatten(self, node, sheet: str) -> list:
        """A range as a flat list of values; a scalar as a one-item list."""
        if isinstance(node, Rng):
            s = node.start.sheet or sheet
            return [self.cell(s, c, r)
                    for r in range(node.start.row, node.end.row + 1)
                    for c in range(node.start.col, node.end.col + 1)]
        value = self.evaluate(node, sheet)
        return value if isinstance(value, list) else [value]

    # -- expressions -------------------------------------------------------
    def evaluate(self, node, sheet: str):
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Str):
            return node.value
        if isinstance(node, Ref):
            return self.cell(node.sheet or sheet, node.col, node.row)
        if isinstance(node, Rng):
            return self.flatten(node, sheet)
        if isinstance(node, Neg):
            return -_num(self.evaluate(node.operand, sheet))
        if isinstance(node, Bin):
            return self._binary(node, sheet)
        if isinstance(node, Call):
            return self._call(node, sheet)
        raise ValueError(f"cannot evaluate {node!r}")

    def _binary(self, node: Bin, sheet: str):
        if node.op == "&":
            return f"{self.evaluate(node.left, sheet)}{self.evaluate(node.right, sheet)}"
        left = self.evaluate(node.left, sheet)
        right = self.evaluate(node.right, sheet)
        if node.op in ("=", "<>"):
            same = left == right
            return same if node.op == "=" else not same
        a, b = _num(left), _num(right)
        return {
            "+": lambda: a + b,
            "-": lambda: a - b,
            "*": lambda: a * b,
            # Excel would show #DIV/0! here. Returning zero instead lets a
            # broken formula sail through as a passing VARIANCE, which is
            # the one outcome this whole script exists to prevent. The
            # divisions that legitimately guard against a zero denominator
            # sit inside an IF, and IF is lazy, so they never reach this.
            "/": lambda: _divide(a, b),
            "^": lambda: a ** b,
            "<": lambda: a < b,
            ">": lambda: a > b,
            "<=": lambda: a <= b,
            ">=": lambda: a >= b,
        }[node.op]()

    def _call(self, node: Call, sheet: str):
        name, args = node.name, node.args

        # IF is lazy in Excel; evaluating both branches eagerly would divide by
        # zero in exactly the cells whose IF exists to prevent it.
        if name == "IF":
            cond = self.evaluate(args[0], sheet)
            if _truthy(cond):
                return self.evaluate(args[1], sheet)
            return self.evaluate(args[2], sheet) if len(args) > 2 else False

        if name == "SUM":
            return sum(_num(v) for a in args for v in self.flatten(a, sheet))
        if name in ("MIN", "MAX"):
            vals = [_num(v) for a in args for v in self.flatten(a, sheet)]
            return (min if name == "MIN" else max)(vals) if vals else 0.0
        if name == "ROUND":
            value = _num(self.evaluate(args[0], sheet))
            digits = int(_num(self.evaluate(args[1], sheet)))
            return _round_half_up(value, digits)
        if name == "ABS":
            return abs(_num(self.evaluate(args[0], sheet)))
        if name == "COUNTIF":
            return self._countif(args, sheet)
        if name == "OFFSET":
            return self.flatten(self._offset(args, sheet), sheet)
        if name == "NPV":
            rate = _num(self.evaluate(args[0], sheet))
            flows = [_num(v) for a in args[1:] for v in self.flatten(a, sheet)]
            return sum(f / (1 + rate) ** (i + 1) for i, f in enumerate(flows))
        if name == "IRR":
            flows = [_num(v) for v in self.flatten(args[0], sheet)]
            guess = _num(self.evaluate(args[1], sheet)) if len(args) > 1 else 0.1
            return _irr(flows, guess)
        raise ValueError(f"unsupported function {name}")

    def _offset(self, args, sheet: str) -> Rng:
        base = args[0]
        if not isinstance(base, Ref):
            raise ValueError("OFFSET needs a cell reference")
        rows = int(_num(self.evaluate(args[1], sheet)))
        cols = int(_num(self.evaluate(args[2], sheet)))
        height = int(_num(self.evaluate(args[3], sheet))) if len(args) > 3 else 1
        width = int(_num(self.evaluate(args[4], sheet))) if len(args) > 4 else 1
        start = Ref(base.sheet, base.col + cols, base.row + rows)
        return Rng(start, Ref(base.sheet, start.col + width - 1, start.row + height - 1))

    def _countif(self, args, sheet: str) -> float:
        values = self.flatten(args[0], sheet)
        criteria = self.evaluate(args[1], sheet)
        if isinstance(criteria, str):
            m = re.match(r"^(<=|>=|<>|<|>|=)?(.*)$", criteria)
            op, operand = m.group(1) or "=", m.group(2)
            try:
                target: object = float(operand)
            except ValueError:
                target = operand
            test = {
                "=": lambda v: v == target,
                "<>": lambda v: v != target,
                ">": lambda v: _num(v) > _num(target),
                "<": lambda v: _num(v) < _num(target),
                ">=": lambda v: _num(v) >= _num(target),
                "<=": lambda v: _num(v) <= _num(target),
            }[op]
            return float(sum(1 for v in values if test(v)))
        return float(sum(1 for v in values if v == criteria))

    # -- the whole book ----------------------------------------------------
    def calculate_all(self) -> int:
        done = 0
        for ws in self.wb:
            for row in ws.iter_rows():
                for c in row:
                    if isinstance(c.value, str) and c.value.startswith("="):
                        done += 1
                        try:
                            self.cell(ws.title, c.column, c.row)
                        except Exception as exc:                      # noqa: BLE001
                            self.errors.append(
                                f"{ws.title}!{c.coordinate}: {exc} -- {c.value[:70]}")
        return done


def _divide(a: float, b: float) -> float:
    if b == 0:
        raise ValueError(f"#DIV/0! evaluating {a!r}/{b!r}")
    return a / b


def _num(value) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return _num(value[0]) if value else 0.0
    return 0.0


def _truthy(value) -> bool:
    return bool(value) if isinstance(value, bool) else _num(value) != 0.0


def _round_half_up(value: float, digits: int) -> float:
    """Excel rounds halves away from zero; Python rounds them to even.

    Adding 0.5 and truncating is not that: 1.005 is stored as slightly less
    than one and a half hundredths, so `int(100.4999... + 0.5)` gives 1.00
    where Excel gives 1.01. Decimal on the float's shortest repr rounds the
    number as written, which is what a spreadsheet appears to do.
    """
    if not math.isfinite(value):
        return value
    quantum = decimal.Decimal(1).scaleb(-digits)
    rounded = decimal.Decimal(repr(value)).quantize(
        quantum, rounding=decimal.ROUND_HALF_UP)
    return float(rounded)


def _irr(flows: list[float], guess: float = 0.1) -> float:
    """Bisection, because it converges on the sign changes IRR actually has."""
    def npv(rate: float) -> float:
        return sum(f / (1 + rate) ** i for i, f in enumerate(flows))

    lo, hi = -0.9999, 10.0
    if npv(lo) * npv(hi) > 0:
        return guess
    for _ in range(200):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def check_variances(calc: Calculator) -> list[str]:
    """Every row on the Check sheet labelled VARIANCE must compute to zero."""
    ws = calc.wb["Check"]
    problems, checked = [], 0
    for row in ws.iter_rows(min_col=1, max_col=1):
        label = row[0].value
        # An exact match, not a substring one. The sheet's own explanatory
        # sentence contains the word VARIANCE, so a substring test picked up a
        # prose row and computed five meaningless "variance" cells out of it --
        # which is where the odd count of 145 came from. There are 140.
        if not isinstance(label, str) or label.strip().upper() != "VARIANCE":
            continue
        heading = _heading_above(ws, row[0].row)
        for col in range(3, ws.max_column + 1):
            if ws.cell(row=row[0].row, column=col).value is None:
                # Not a skip: a variance cell that stops existing is a check
                # that quietly covers less than it says it does.
                problems.append(
                    f"VARIANCE {heading} Y{col - 2}: cell is empty, so this "
                    f"year is no longer compared against model.py")
                continue
            checked += 1
            value = _num(calc.cell("Check", col, row[0].row))
            if abs(value) > 0.5:
                problems.append(
                    f"VARIANCE {heading} Y{col - 2}: workbook differs from "
                    f"model.py by {value:,.0f}")
    print(f"Check sheet: {checked} variance cells computed")
    return problems


def _heading_above(ws, row: int) -> str:
    for r in range(row - 1, 0, -1):
        value = ws.cell(row=r, column=1).value
        if isinstance(value, str) and value.strip() and not value.startswith(" "):
            return value.strip()
    return "?"


def main() -> int:
    if not WORKBOOK.exists():
        print(f"{WORKBOOK} not found -- run build_workbook.py first")
        return 1

    calc = Calculator(WORKBOOK)
    done = calc.calculate_all()
    print(f"{WORKBOOK.name}: {done:,} formulas evaluated")

    problems = list(calc.errors)
    if not problems:
        problems += check_variances(calc)

    if problems:
        print(f"\n{len(problems)} problems:")
        for p in problems[:25]:
            print("  -", p)
        if len(problems) > 25:
            print(f"  ... and {len(problems) - 25} more")
        return 1

    print("every formula evaluates, and every VARIANCE row on the Check sheet "
          "is zero: the workbook computes what model.py computes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
