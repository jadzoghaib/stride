"""Compare every workbook row against model.py, not only the fifteen on Check.

The Check sheet proves fifteen lines agree with the model: net revenue, cost of
sales, gross profit, operating costs, EBITDA, paying fans, average fans, GMV,
deals, applications, verification, tax, net profit, free cash flow and the
balance-sheet tie. That is a good spine and it is not coverage. A compensating
error inside cost of sales, payment fees up and infrastructure down by the same
amount, reproduces the total exactly and passes every existing check here.

So this walks the rows that should equal a model output, evaluates the
workbook's own formulas with the recalculator, and compares magnitudes.

Sign conventions are detected rather than assumed. The P&L presents costs as
negatives and the cost build-up presents them as positives, which is correct
accounting presentation and not a defect; the audit reports which convention
each row uses and fails only when the magnitude is wrong. Asserting a sign in
the expectation table would have made the audit wrong about the thing it is
least qualified to judge.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "business-plan"))

import model as M  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "recalc", ROOT / "scripts" / "recalc_workbook.py")
recalc = importlib.util.module_from_spec(spec)
# Registered before executing: recalc_workbook defines dataclasses, and
# @dataclass resolves annotations through sys.modules[cls.__module__], which
# does not exist yet during exec_module.
sys.modules["recalc"] = recalc
spec.loader.exec_module(recalc)

WORKBOOK = ROOT / "business-plan" / "Stride_Financial_Model.xlsx"
FIRST, N = 3, 10

#: sheet -> {row label: (model key, tolerance in that row's own units)}
EXPECT: dict[str, dict[str, tuple[str, float]]] = {
    "Drivers": {
        "Total athletes (year end)": ("athletes", 0.5),
        "Paying fans (year end)": ("paying_fans", 1.0),
        "Average paying fans": ("avg_fans", 1.0),
        "Athletes acquired (gross)": ("athlete_gross_adds", 1.0),
        "Fans lost to churn": ("fans_churned", 1.0),
        "Total deals": ("deals", 0.5),
        "Paying sponsors": ("paying_sponsors", 0.5),
        "Blended admission rate": ("admit_rate", 0.0005),
        "Applications required": ("applications", 1.0),
        "Manual reviews": ("reviews", 1.0),
        "Reviewer FTE implied": ("review_fte", 0.0005),
    },
    "Revenue": {
        "Total fan GMV": ("fan_gmv", 1.0),
        "Total sponsorship GMV": ("sponsorship_gmv", 1.0),
        "TOTAL GMV": ("gmv", 1.0),
        "Fan take": ("rev_fan", 1.0),
        "Sponsorship take": ("rev_sponsorship", 1.0),
        "Sponsor SaaS": ("rev_saas", 1.0),
        "NET REVENUE": ("revenue", 1.0),
    },
    "Costs": {
        "Payment processing": ("psp", 1.0),
        "Payouts to athletes": ("payouts", 1.0),
        "Infrastructure (AWS + CDN)": ("infra", 1.0),
        "Moderation": ("moderation", 1.0),
        "Athlete verification": ("verification", 1.0),
        "TOTAL COST OF SALES": ("cogs", 1.0),
        "People": ("people", 1.0),
        "Total marketing / CAC": ("marketing", 1.0),
        "Legal & compliance": ("legal", 1.0),
        "Other opex": ("other", 1.0),
        "TOTAL OPERATING COSTS": ("opex", 1.0),
    },
    "P&L": {
        "Net revenue": ("revenue", 1.0),
        "Cost of sales": ("cogs", 1.0),
        "GROSS PROFIT": ("gross", 1.0),
        "Operating costs": ("opex", 1.0),
        "EBITDA": ("ebitda", 1.0),
        "Amortisation": ("amortisation", 1.0),
        "EBIT": ("ebit", 1.0),
        "Taxable profit": ("taxable", 1.0),
        "Applicable tax rate": ("tax_rate", 0.0005),
        "Tax charge": ("tax", 1.0),
        "NET PROFIT": ("net_profit", 1.0),
    },
    "CashFlow": {
        "Net profit": ("net_profit", 1.0),
        "Add back amortisation": ("amortisation", 1.0),
        "Change in working capital": ("change_in_nwc", 1.0),
        "OPERATING CASH FLOW": ("operating_cf", 1.0),
        "Capital expenditure": ("capex", 1.0),
        "FREE CASH FLOW": ("fcf", 1.0),
    },
    "WorkingCap": {
        "Sponsor receivables": ("receivables", 1.0),
        "Athlete payout float": ("payout_float", 1.0),
        "Trade payables": ("payables", 1.0),
        "Net working capital": ("nwc", 1.0),
        "Change in NWC": ("change_in_nwc", 1.0),
        "Capitalised development": ("capex", 1.0),
        "Amortisation": ("amortisation", 1.0),
    },
    "Assumptions": {
        "Headcount": ("headcount", 0.005),
    },
    "KPIs": {
        "Active athletes": ("athletes", 0.5),
        "Paying fans, year end": ("paying_fans", 1.0),
        "Paying sponsors": ("paying_sponsors", 0.5),
        "Net revenue": ("revenue", 1.0),
    },
}

#: The lines the Check sheet already compares, by the model key they stand for.
CHECKED_ON_CHECK_SHEET = {
    "revenue", "cogs", "gross", "opex", "ebitda", "paying_fans", "avg_fans",
    "gmv", "deals", "applications", "verification", "tax", "net_profit", "fcf",
}


def main() -> int:
    rows = M.build()
    calc = recalc.Calculator(WORKBOOK)
    wb = calc.wb

    checked = 0
    problems: list[str] = []
    flipped: list[str] = []
    unmatched: list[str] = []

    for sheet, wanted in EXPECT.items():
        ws = wb[sheet]
        found: dict[str, int] = {}
        for row in ws.iter_rows(min_col=1, max_col=1):
            lab = row[0].value
            if isinstance(lab, str) and lab.strip() in wanted and lab.strip() not in found:
                found[lab.strip()] = row[0].row
        for label, (key, tol) in wanted.items():
            if label not in found:
                unmatched.append(f"{sheet}: {label!r}")
                continue
            r = found[label]
            signs = set()
            for i in range(N):
                want = rows[i][key]
                got = calc.cell(sheet, FIRST + i, r)
                if not isinstance(got, (int, float)) or isinstance(got, bool):
                    problems.append(
                        f"{sheet}!{label} Y{i+1}: not a number ({got!r})")
                    continue
                got = float(got)
                checked += 1
                # A zero matches either convention, so it tells us nothing about
                # the row's sign and must not be counted as evidence of one.
                # Tax is zero for six loss-making years and a negative deduction
                # for four, which read as "inconsistent" until zeros were
                # excluded.
                if abs(want) <= tol and abs(got) <= tol:
                    continue
                if abs(got - want) <= tol:
                    signs.add("+")
                elif abs(got + want) <= tol:
                    signs.add("-")
                else:
                    problems.append(
                        f"{sheet}!{label} Y{i+1}: workbook {got:,.2f}, "
                        f"model {want:,.2f}, out by {got - want:,.2f}")
            if signs == {"-"}:
                flipped.append(f"{sheet}!{label} (presented negative; magnitude agrees)")
            elif len(signs) > 1:
                problems.append(
                    f"{sheet}!{label}: sign is inconsistent ACROSS YEARS "
                    f"({'/'.join(sorted(signs))}), which no presentation convention explains")

    print(f"Cross-checked {checked} cells against model.py.\n")

    if problems:
        print(f"{len(problems)} problems:")
        for p in problems[:40]:
            print("  MISMATCH", p)
        if len(problems) > 40:
            print(f"  ... and {len(problems) - 40} more")
    else:
        print("Every mapped row reproduces model.py to within its own unit.")

    if flipped:
        print(f"\nSign conventions detected ({len(flipped)}), magnitudes all agree:")
        for f in flipped:
            print(f"  {f}")

    if unmatched:
        print("\nLabels this audit looked for and did not find:")
        for u in unmatched:
            print(f"  {u}")

    # ── what the Check sheet leaves unguarded ────────────────────────────
    gaps = sorted({key for wanted in EXPECT.values() for key, _ in wanted.values()}
                  - CHECKED_ON_CHECK_SHEET)
    print(f"\nModel outputs this audit verifies that the Check sheet does NOT "
          f"({len(gaps)}). A compensating error inside any of these reproduces its\n"
          f"parent total exactly and passes recalc_workbook.py:")
    for g in gaps:
        print(f"  {g}")

    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
