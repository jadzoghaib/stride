"""Generate Stride_Financial_Model.xlsx — a live, formula-driven model.

    uv run python business-plan/build_workbook.py

DESIGN PRINCIPLE: **the workbook contains the logic, not the answers.** Every
cell outside the Assumptions sheet is an Excel formula referring to other cells,
so changing one input on Assumptions recalculates the whole model — including
the three statements and the valuation. Pasting computed values would produce a
report; this produces a model you can interrogate.

Colour convention, stated on the README sheet and used consistently:

    BLUE   an input. Change these.
    BLACK  a formula. Do not overtype — you would break the chain.
    GREEN  a reference to another sheet.

Sheets, in dependency order:

    README        how to use it, and what every colour means
    Assumptions   every input, grouped, with units and provenance
    Drivers       athletes and fans, including cohort churn mechanics
    Revenue       GMV and net revenue, built stream by stream
    Costs         COGS and opex, built line by line
    P&L           income statement
    WorkingCap    receivables, payables, athlete float, capex and D&A
    CashFlow      indirect method, tying to the closing cash balance
    BalanceSheet  with an explicit balance check
    Valuation     DCF, NPV, IRR, exit multiples, WACC/growth sensitivity
    Funding       rounds, dilution, ownership
    Check         the Python model's numbers, to verify the formulas agree
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import model as M

YEARS = M.YEARS
N = len(YEARS)
FIRST = 3                      # column C = Y1
COLS = [get_column_letter(FIRST + k) for k in range(N)]

# ── styling ──────────────────────────────────────────────────────────────────
INPUT = Font(color="1F5FBF", name="Calibri", size=10)
FORMULA = Font(color="1A1A1A", name="Calibri", size=10)
LINK = Font(color="107C41", name="Calibri", size=10)
BOLD = Font(bold=True, name="Calibri", size=10)
TITLE = Font(bold=True, size=13, color="14100A", name="Calibri")
HEAD = Font(bold=True, color="FFFFFF", name="Calibri", size=10)
HEAD_FILL = PatternFill("solid", fgColor="14181F")
BAND = PatternFill("solid", fgColor="F2F4F7")
ACCENT = PatternFill("solid", fgColor="FFB020")
MONEY = '#,##0;[Red](#,##0)'
MONEY2 = '#,##0.00;[Red](#,##0.00)'
PCT = '0.0%'
NUM = '#,##0'
THIN = Side(style="thin", color="D0D5DD")
TOPLINE = Border(top=Side(style="medium", color="14181F"))


def sheet(wb, name, title):
    ws = wb.create_sheet(name)
    ws["A1"] = title
    ws["A1"].font = TITLE
    ws.column_dimensions["A"].width = 44
    ws.column_dimensions["B"].width = 15
    for c in COLS:
        ws.column_dimensions[c].width = 13
    ws.freeze_panes = "C4"
    r = 3
    ws.cell(r, 1, "Line").font = HEAD
    ws.cell(r, 1).fill = HEAD_FILL
    ws.cell(r, 2, "Unit").font = HEAD
    ws.cell(r, 2).fill = HEAD_FILL
    for k, c in enumerate(COLS):
        cell = ws.cell(r, FIRST + k, f"Y{YEARS[k]}")
        cell.font, cell.fill, cell.alignment = HEAD, HEAD_FILL, Alignment(horizontal="center")
    return ws


def row(ws, r, label, unit="", *, values=None, formula=None, fmt=MONEY,
        bold=False, font=None, band=False, top=False, indent=0):
    """Write one line. `values` writes inputs; `formula` writes a template with
    {c} substituted for the column letter and {p} for the previous column."""
    lab = ws.cell(r, 1, ("    " * indent) + label)
    lab.font = BOLD if bold else Font(name="Calibri", size=10)
    ws.cell(r, 2, unit).font = Font(name="Calibri", size=9, color="6B7480")
    for k, c in enumerate(COLS):
        cell = ws.cell(r, FIRST + k)
        if values is not None:
            cell.value = values[k] if k < len(values) else None
            cell.font = font or INPUT
        elif formula is not None:
            prev = COLS[k - 1] if k > 0 else None
            f = formula.format(c=c, p=prev or c, k=k + 1, y=YEARS[k])
            if k == 0 and "{p}" in formula and prev is None:
                pass
            cell.value = f
            cell.font = font or FORMULA
        cell.number_format = fmt
        if bold:
            cell.font = Font(bold=True, name="Calibri", size=10,
                             color=(font.color.rgb if font and font.color else "1A1A1A"))
        if band:
            cell.fill = BAND
        if top:
            cell.border = TOPLINE
    if band:
        lab.fill = BAND
        ws.cell(r, 2).fill = BAND
    if top:
        lab.border = TOPLINE
    return r + 1


def section(ws, r, text):
    c = ws.cell(r, 1, text)
    c.font = Font(bold=True, size=10, color="8A5200")
    c.fill = PatternFill("solid", fgColor="FFF4DE")
    for k in range(len(COLS) + 1):
        ws.cell(r, 2 + k).fill = PatternFill("solid", fgColor="FFF4DE")
    return r + 1


def build() -> pathlib.Path:
    wb = Workbook()
    wb.remove(wb.active)
    A = M.A
    rows = M.build()

    # ══ README ══════════════════════════════════════════════════════════════
    rd = wb.create_sheet("README")
    rd.column_dimensions["A"].width = 100
    lines = [
        ("Stride — Financial Model", TITLE),
        ("", None),
        ("10-year operating model, three statements, and a valuation. EUR. Y1 = 2027.", BOLD),
        ("", None),
        ("HOW TO USE", BOLD),
        ("Change any BLUE cell on the Assumptions sheet. Everything else recalculates.", None),
        ("Every non-input cell is a formula, so you can trace any number back to the inputs", None),
        ("that produced it — select a cell and use Formulas > Trace Precedents.", None),
        ("", None),
        ("COLOURS", BOLD),
        ("  BLUE    an input. These are the only cells you should type into.", None),
        ("  BLACK   a formula on this sheet.", None),
        ("  GREEN   a reference to another sheet.", None),
        ("", None),
        ("SHEETS", BOLD),
        ("  Assumptions    every input, grouped, with units and provenance", None),
        ("  Drivers        athletes and fans, including monthly cohort churn", None),
        ("  Revenue        GMV and net revenue, stream by stream", None),
        ("  Costs          COGS and operating costs, line by line", None),
        ("  P&L            income statement", None),
        ("  WorkingCap     receivables, payables, athlete float, capex, D&A", None),
        ("  CashFlow       indirect method, tying to closing cash", None),
        ("  BalanceSheet   with an explicit balance check row", None),
        ("  Valuation      DCF, NPV, IRR, exit multiples, sensitivity", None),
        ("  Funding        rounds, dilution, ownership", None),
        ("  Check          the Python model's figures, to verify the formulas agree", None),
        ("", None),
        ("WHY TEN YEARS", BOLD),
        ("At Y7 the business is still compounding above 50%, so a terminal value placed", None),
        ("there does most of the valuation work and does it badly. Ten years lets growth", None),
        ("decelerate inside the explicit forecast, where it can be argued with.", None),
        ("", None),
        ("MODEL SHAPE", BOLD),
        ("This is a target-driven model: athlete counts are the plan, and marketing spend", None),
        ("is derived from them at segment CAC. It is not a driver-driven model in which", None),
        ("spend produces athletes. That is the normal shape for a plan, but it means the", None),
        ("athlete trajectory is an assumption to defend, not an output to trust.", None),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        c = rd.cell(i, 1, text)
        if font:
            c.font = font

    # ══ ASSUMPTIONS ═════════════════════════════════════════════════════════
    a = sheet(wb, "Assumptions", "Assumptions — every input lives here")
    r = 4
    A_ROW = {}

    def put(label, unit, values, fmt=NUM, key=None):
        nonlocal r
        A_ROW[key or label] = r
        r = row(a, r, label, unit, values=values, fmt=fmt)

    r = section(a, r, "MARKET — the plan's shape")
    put("Active athletes (year end)", "count", A.athletes, NUM, "athletes")
    put("Niche share of athletes", "%", A.niche_share, PCT, "niche_share")
    r += 1

    for seg, tag in ((M.NICHE, "niche"), (M.POPULAR, "popular")):
        r = section(a, r, f"SEGMENT — {tag.upper()}")
        put(f"Monetising athletes ({tag})", "% of segment", seg.monetise_rate, PCT, f"{tag}_monetise")
        put(f"Paying fans per monetising athlete ({tag})", "count", seg.fans_per_athlete, NUM, f"{tag}_fpa")
        put(f"Fan ARPU per month ({tag})", "EUR", seg.fan_arpu_month, MONEY2, f"{tag}_arpu")
        put(f"Fan churn per month ({tag})", "%", seg.fan_churn_month, PCT, f"{tag}_fchurn")
        put(f"Athlete churn per year ({tag})", "%", seg.athlete_churn_year, PCT, f"{tag}_achurn")
        put(f"Athletes landing a deal ({tag})", "% of segment", seg.deal_rate, PCT, f"{tag}_dealrate")
        put(f"Deals per dealing athlete ({tag})", "count", seg.deals_per_athlete, '0.0', f"{tag}_dpa")
        put(f"Average deal value ({tag})", "EUR", seg.avg_deal_eur, MONEY, f"{tag}_deal")
        put(f"Athlete CAC ({tag})", "EUR", seg.cac_eur, MONEY, f"{tag}_cac")
        r += 1

    r = section(a, r, "SPONSORS")
    put("Registered sponsors", "count", A.sponsors, NUM, "sponsors")
    put("Share on a paid plan", "%", A.sponsor_paid_rate, PCT, "sponsor_paid")
    put("Sponsor plan ARPU per month", "EUR", A.sponsor_arpu_month, MONEY, "sponsor_arpu")
    put("Sponsor CAC", "EUR", A.sponsor_cac_eur, MONEY, "sponsor_cac")
    r += 1

    r = section(a, r, "TAKE RATES & PAYMENT RAILS")
    put("Take rate — fan revenue", "%", [A.take_fan] * N, PCT, "take_fan")
    put("Take rate — sponsorship", "%", [A.take_sponsorship] * N, PCT, "take_sp")
    put("PPV & tips as multiple of subs", "x", [A.ppv_tips_multiple] * N, '0.00', "ppv_mult")
    put("PSP percentage fee", "%", [A.psp_pct] * N, '0.00%', "psp_pct")
    put("PSP fixed fee per transaction", "EUR", [A.psp_fixed_eur] * N, MONEY2, "psp_fix")
    put("Payout percentage fee", "%", [A.payout_pct] * N, '0.00%', "payout_pct")
    put("Payout fixed fee", "EUR", [A.payout_fixed_eur] * N, MONEY2, "payout_fix")
    put("Average fan transaction", "EUR", [A.avg_fan_txn_eur] * N, MONEY2, "fan_txn")
    put("Average deal transaction", "EUR", [A.avg_deal_txn_eur] * N, MONEY, "deal_txn")
    r += 1

    r = section(a, r, "INFRASTRUCTURE & CONTENT COSTS")
    put("AWS base cost per month", "EUR", A.aws_base_month, MONEY, "aws")
    put("Media GB per paying fan per month", "GB", [A.gb_per_fan_month] * N, '0.0', "gb")
    put("Egress cost per GB (zero-egress CDN)", "EUR", [A.egress_eur_per_gb] * N, '0.000', "egress")
    put("Egress cost per GB (CloudFront list)", "EUR", [A.egress_eur_per_gb_naive] * N, '0.000', "egress_naive")
    put("Moderation cost per 1,000 items", "EUR", [A.moderation_eur_per_1k_items] * N, MONEY2, "mod_rate")
    put("Items per athlete per month", "count", [A.items_per_athlete_month] * N, '0.0', "items")
    r += 1

    r = section(a, r, "PEOPLE & OVERHEAD")
    put("Headcount", "FTE", A.headcount, '0.0', "headcount")
    put("Loaded salary (incl. ~31% employer SS)", "EUR", A.loaded_salary_eur, MONEY, "salary")
    put("Legal & compliance", "EUR", A.legal_compliance_eur, MONEY, "legal")
    put("Other opex as % of revenue", "%", [A.other_opex_pct_of_revenue] * N, PCT, "other_pct")
    r += 1

    r = section(a, r, "WORKING CAPITAL, CAPEX & TAX")
    put("Athlete payout float", "days", [15] * N, NUM, "float_days")
    put("Sponsor receivable days", "days", [45] * N, NUM, "ar_days")
    put("Trade payable days", "days", [30] * N, NUM, "ap_days")
    put("Capitalised development", "% of people cost", [0.30] * N, PCT, "capex_pct")
    put("Amortisation period", "years", [3] * N, '0', "amort_years")
    put("Corporate tax — startup rate", "%", [0.15] * N, PCT, "tax_low")
    put("Corporate tax — standard rate", "%", [0.25] * N, PCT, "tax_high")
    put("Years at startup rate (from first profit)", "years", [4] * N, '0', "tax_low_years")
    r += 1

    r = section(a, r, "VALUATION")
    put("WACC / discount rate", "%", [A.wacc] * N, PCT, "wacc")
    put("Terminal growth", "%", [A.terminal_growth] * N, PCT, "tg")
    put("Exit revenue multiple", "x", [6.5] * N, '0.0', "exit_mult")
    put("Risk-free rate (Spanish 10Y)", "%", [A.risk_free] * N, PCT, "rf")
    put("Founder alternative return", "%", [A.founder_alt_return] * N, PCT, "alt")

    def AR(key, col):
        return f"Assumptions!${col}${A_ROW[key]}"

    def A1(key):
        """First-column absolute reference (for scalars repeated across years)."""
        return f"Assumptions!$C${A_ROW[key]}"

    # ══ DRIVERS ═════════════════════════════════════════════════════════════
    d = sheet(wb, "Drivers", "Drivers — athletes and fans, with cohort churn")
    r, D = 4, {}

    def drow(label, formula=None, values=None, fmt=NUM, **kw):
        nonlocal r
        D[label] = r
        r = row(d, r, label, kw.pop("unit", ""), formula=formula, values=values, fmt=fmt, **kw)

    r = section(d, r, "ATHLETES")
    drow("Total athletes (year end)", formula=f"={{c}}{A_ROW['athletes']}".replace("{c}", "Assumptions!{c}"), fmt=NUM, font=LINK)
    drow("Niche athletes", formula="=Drivers!{c}" + str(D["Total athletes (year end)"]) + "*Assumptions!{c}" + str(A_ROW["niche_share"]))
    drow("Popular athletes", formula="=Drivers!{c}" + str(D["Total athletes (year end)"]) + "-Drivers!{c}" + str(D["Niche athletes"]))
    r += 1

    for tag, base in (("Niche", "Niche athletes"), ("Popular", "Popular athletes")):
        t = tag.lower()
        r = section(d, r, f"{tag.upper()} — fans and churn")
        drow(f"{tag} athletes lost to churn",
             formula=(f"=IF({{k}}=1,0,{{p}}{D[base]}*Assumptions!{{c}}{A_ROW[f'{t}_achurn']})"))
        drow(f"{tag} athletes acquired (gross)",
             formula=(f"=MAX(0,{{c}}{D[base]}-IF({{k}}=1,0,{{p}}{D[base]})+{{c}}{r-1})"))
        drow(f"{tag} monetising athletes",
             formula=f"={{c}}{D[base]}*Assumptions!{{c}}{A_ROW[f'{t}_monetise']}")
        drow(f"{tag} paying fans (year end)",
             formula=f"={{c}}{r-1}*Assumptions!{{c}}{A_ROW[f'{t}_fpa']}", bold=True)
        # cohort mechanics, spelled out so the maths is visible rather than asserted
        drow(f"{tag} monthly retention r = 1-churn", unit="factor",
             formula=f"=1-Assumptions!{{c}}{A_ROW[f'{t}_fchurn']}", fmt='0.000')
        drow(f"{tag} opening fans survived 12 months", unit="= open x r^12",
             formula=f"=IF({{k}}=1,0,{{p}}{D[f'{tag} paying fans (year end)']}*{{c}}{r-1}^12)")
        rr = D[f"{tag} monthly retention r = 1-churn"]
        surv = r - 1
        drow(f"{tag} monthly gross adds", unit="solved: (end - survivors)/annuity",
             formula=(f"=MAX(0,({{c}}{D[f'{tag} paying fans (year end)']}-{{c}}{surv})"
                      f"/((1-{{c}}{rr}^12)/(1-{{c}}{rr})))"))
        drow(f"{tag} fans acquired (gross)", unit="x12 months",
             formula=f"={{c}}{r-1}*12")
        drow(f"{tag} S = r(1-r^12)/(1-r)", unit="geometric sum", fmt='0.000',
             formula=f"={{c}}{rr}*(1-{{c}}{rr}^12)/(1-{{c}}{rr})")
        drow(f"{tag} average fans during year", unit="exact mean, revenue basis",
             formula=(f"=(IF({{k}}=1,0,{{p}}{D[f'{tag} paying fans (year end)']})*{{c}}{r-1}"
                      f"+{{c}}{D[f'{tag} monthly gross adds']}/(1-{{c}}{rr})*(12-{{c}}{r-1}))/12"),
             bold=True)
        drow(f"{tag} fans lost to churn", unit="avg x churn x 12",
             formula=(f"={{c}}{D[f'{tag} average fans during year']}*12"
                      f"*Assumptions!{{c}}{A_ROW[f'{t}_fchurn']}"))
        r += 1

    r = section(d, r, "TOTALS")
    drow("Paying fans (year end)",
         formula=f"={{c}}{D['Niche paying fans (year end)']}+{{c}}{D['Popular paying fans (year end)']}", bold=True)
    drow("Average paying fans",
         formula=f"={{c}}{D['Niche average fans during year']}+{{c}}{D['Popular average fans during year']}", bold=True)
    drow("Athletes acquired (gross)",
         formula=f"={{c}}{D['Niche athletes acquired (gross)']}+{{c}}{D['Popular athletes acquired (gross)']}")
    drow("Fans lost to churn",
         formula=f"={{c}}{D['Niche fans lost to churn']}+{{c}}{D['Popular fans lost to churn']}")
    r += 1

    r = section(d, r, "DEALS")
    drow("Niche deals",
         formula=(f"={{c}}{D['Niche athletes']}*Assumptions!{{c}}{A_ROW['niche_dealrate']}"
                  f"*Assumptions!{{c}}{A_ROW['niche_dpa']}"))
    drow("Popular deals",
         formula=(f"={{c}}{D['Popular athletes']}*Assumptions!{{c}}{A_ROW['popular_dealrate']}"
                  f"*Assumptions!{{c}}{A_ROW['popular_dpa']}"))
    drow("Total deals", formula=f"={{c}}{r-2}+{{c}}{r-1}", bold=True)
    drow("Paying sponsors",
         formula=f"=Assumptions!{{c}}{A_ROW['sponsors']}*Assumptions!{{c}}{A_ROW['sponsor_paid']}")
    drow("Sponsors acquired (gross)",
         formula=f"=MAX(0,Assumptions!{{c}}{A_ROW['sponsors']}-IF({{k}}=1,0,Assumptions!{{p}}{A_ROW['sponsors']}))")

    # ══ REVENUE ═════════════════════════════════════════════════════════════
    v = sheet(wb, "Revenue", "Revenue — GMV built stream by stream, then our take")
    r, R = 4, {}

    def vrow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        R[label] = r
        r = row(v, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    r = section(v, r, "FAN GMV — what fans pay athletes")
    vrow("Niche subscription GMV", unit="avg fans x ARPU x 12",
         formula=(f"=Drivers!{{c}}{D['Niche average fans during year']}"
                  f"*Assumptions!{{c}}{A_ROW['niche_arpu']}*12"))
    vrow("Popular subscription GMV",
         formula=(f"=Drivers!{{c}}{D['Popular average fans during year']}"
                  f"*Assumptions!{{c}}{A_ROW['popular_arpu']}*12"))
    vrow("Subscription GMV", formula=f"={{c}}{r-2}+{{c}}{r-1}", bold=True)
    vrow("PPV and tips GMV", unit="x multiple",
         formula=f"={{c}}{R['Subscription GMV']}*Assumptions!{{c}}{A_ROW['ppv_mult']}")
    vrow("Total fan GMV", formula=f"={{c}}{R['Subscription GMV']}+{{c}}{R['PPV and tips GMV']}",
         bold=True, band=True)
    r += 1

    r = section(v, r, "SPONSORSHIP GMV — what sponsors pay athletes and clubs")
    vrow("Niche sponsorship GMV",
         formula=f"=Drivers!{{c}}{D['Niche deals']}*Assumptions!{{c}}{A_ROW['niche_deal']}")
    vrow("Popular sponsorship GMV",
         formula=f"=Drivers!{{c}}{D['Popular deals']}*Assumptions!{{c}}{A_ROW['popular_deal']}")
    vrow("Total sponsorship GMV", formula=f"={{c}}{r-2}+{{c}}{r-1}", bold=True, band=True)
    vrow("TOTAL GMV", formula=f"={{c}}{R['Total fan GMV']}+{{c}}{R['Total sponsorship GMV']}",
         bold=True, top=True)
    r += 1

    r = section(v, r, "NET REVENUE — our share")
    vrow("Fan take", unit="fan GMV x take rate",
         formula=f"={{c}}{R['Total fan GMV']}*Assumptions!{{c}}{A_ROW['take_fan']}")
    vrow("Sponsorship take",
         formula=f"={{c}}{R['Total sponsorship GMV']}*Assumptions!{{c}}{A_ROW['take_sp']}")
    vrow("Sponsor SaaS", unit="paying sponsors x ARPU x 12",
         formula=(f"=Drivers!{{c}}{D['Paying sponsors']}"
                  f"*Assumptions!{{c}}{A_ROW['sponsor_arpu']}*12"))
    vrow("NET REVENUE", formula=f"=SUM({{c}}{r-3}:{{c}}{r-1})", bold=True, top=True, band=True)
    vrow("Growth", unit="% YoY", formula=f"=IF({{k}}=1,\"\",{{c}}{r-1}/{{p}}{r-1}-1)", fmt=PCT)
    vrow("Take rate on GMV", unit="blended",
         formula=f"={{c}}{R['NET REVENUE']}/{{c}}{R['TOTAL GMV']}", fmt=PCT)

    # ══ COSTS ═══════════════════════════════════════════════════════════════
    co = sheet(wb, "Costs", "Costs — every line built from its driver")
    r, C = 4, {}

    def crow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        C[label] = r
        r = row(co, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    r = section(co, r, "COST OF SALES")
    crow("Fan transactions", unit="fan GMV / avg ticket", fmt=NUM,
         formula=f"=Revenue!{{c}}{R['Total fan GMV']}/Assumptions!{{c}}{A_ROW['fan_txn']}")
    crow("Deal transactions", unit="count", fmt=NUM,
         formula=f"=Revenue!{{c}}{R['Total sponsorship GMV']}/Assumptions!{{c}}{A_ROW['deal_txn']}")
    crow("Payment processing", unit="% of GMV + fixed",
         formula=(f"=Revenue!{{c}}{R['TOTAL GMV']}*Assumptions!{{c}}{A_ROW['psp_pct']}"
                  f"+({{c}}{C['Fan transactions']}+{{c}}{C['Deal transactions']})"
                  f"*Assumptions!{{c}}{A_ROW['psp_fix']}"))
    crow("Payouts to athletes", unit="% + fixed",
         formula=(f"=Revenue!{{c}}{R['TOTAL GMV']}*Assumptions!{{c}}{A_ROW['payout_pct']}"
                  f"+({{c}}{C['Fan transactions']}/30+{{c}}{C['Deal transactions']})"
                  f"*Assumptions!{{c}}{A_ROW['payout_fix']}"))
    crow("Media egress GB", unit="GB/yr", fmt=NUM,
         formula=(f"=Drivers!{{c}}{D['Average paying fans']}"
                  f"*Assumptions!{{c}}{A_ROW['gb']}*12"))
    crow("Infrastructure (AWS + CDN)", unit="base + egress",
         formula=(f"=Assumptions!{{c}}{A_ROW['aws']}*12"
                  f"+{{c}}{C['Media egress GB']}*Assumptions!{{c}}{A_ROW['egress']}"))
    crow("  memo: same egress at CloudFront list", unit="the trap",
         formula=(f"=Assumptions!{{c}}{A_ROW['aws']}*12"
                  f"+{{c}}{C['Media egress GB']}*Assumptions!{{c}}{A_ROW['egress_naive']}"),
         font=Font(color="B3272D", name="Calibri", size=10, italic=True))
    crow("Moderation", unit="items x rate",
         formula=(f"=Drivers!{{c}}{D['Total athletes (year end)']}"
                  f"*Assumptions!{{c}}{A_ROW['items']}*12/1000"
                  f"*Assumptions!{{c}}{A_ROW['mod_rate']}"))
    crow("TOTAL COST OF SALES", bold=True, top=True, band=True,
         formula=(f"={{c}}{C['Payment processing']}+{{c}}{C['Payouts to athletes']}"
                  f"+{{c}}{C['Infrastructure (AWS + CDN)']}+{{c}}{C['Moderation']}"))
    r += 1

    r = section(co, r, "OPERATING COSTS")
    crow("People", unit="FTE x loaded salary",
         formula=f"=Assumptions!{{c}}{A_ROW['headcount']}*Assumptions!{{c}}{A_ROW['salary']}")
    crow("Athlete acquisition — niche", unit="gross adds x CAC",
         formula=(f"=Drivers!{{c}}{D['Niche athletes acquired (gross)']}"
                  f"*Assumptions!{{c}}{A_ROW['niche_cac']}"))
    crow("Athlete acquisition — popular",
         formula=(f"=Drivers!{{c}}{D['Popular athletes acquired (gross)']}"
                  f"*Assumptions!{{c}}{A_ROW['popular_cac']}"))
    crow("Sponsor acquisition",
         formula=(f"=Drivers!{{c}}{D['Sponsors acquired (gross)']}"
                  f"*Assumptions!{{c}}{A_ROW['sponsor_cac']}"))
    crow("Total marketing / CAC", bold=True,
         formula=f"=SUM({{c}}{r-3}:{{c}}{r-1})")
    crow("Legal & compliance", formula=f"=Assumptions!{{c}}{A_ROW['legal']}", font=LINK)
    crow("Other opex", unit="% of revenue",
         formula=f"=Revenue!{{c}}{R['NET REVENUE']}*Assumptions!{{c}}{A_ROW['other_pct']}")
    crow("TOTAL OPERATING COSTS", bold=True, top=True, band=True,
         formula=(f"={{c}}{C['People']}+{{c}}{C['Total marketing / CAC']}"
                  f"+{{c}}{C['Legal & compliance']}+{{c}}{C['Other opex']}"))

    # ══ WORKING CAPITAL & CAPEX ═════════════════════════════════════════════
    wc = sheet(wb, "WorkingCap", "Working capital, capex and amortisation")
    r, W = 4, {}

    def wrow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        W[label] = r
        r = row(wc, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    r = section(wc, r, "WORKING CAPITAL")
    wrow("Sponsor receivables", unit="SaaS+take x AR days/365",
         formula=(f"=(Revenue!{{c}}{R['Sponsorship take']}+Revenue!{{c}}{R['Sponsor SaaS']})"
                  f"*Assumptions!{{c}}{A_ROW['ar_days']}/365"))
    wrow("Athlete payout float", unit="GMV owed, not yet paid",
         formula=(f"=Revenue!{{c}}{R['TOTAL GMV']}*Assumptions!{{c}}{A_ROW['float_days']}/365"))
    wrow("Trade payables", unit="opex x AP days/365",
         formula=(f"=Costs!{{c}}{C['TOTAL OPERATING COSTS']}*Assumptions!{{c}}{A_ROW['ap_days']}/365"))
    wrow("Net working capital", unit="AR - float - AP", bold=True,
         formula=f"={{c}}{W['Sponsor receivables']}-{{c}}{W['Athlete payout float']}-{{c}}{W['Trade payables']}")
    wrow("Change in NWC", unit="cash impact",
         formula=f"=IF({{k}}=1,{{c}}{W['Net working capital']},{{c}}{W['Net working capital']}-{{p}}{W['Net working capital']})")
    r += 1

    r = section(wc, r, "CAPEX & AMORTISATION")
    wrow("Capitalised development", unit="% of people cost",
         formula=f"=Costs!{{c}}{C['People']}*Assumptions!{{c}}{A_ROW['capex_pct']}")
    wrow("Amortisation", unit="3-yr straight line on trailing capex",
         formula=(f"=SUM(OFFSET({{c}}{W['Capitalised development']},0,"
                  f"-MIN(Assumptions!{{c}}{A_ROW['amort_years']}-1,{{k}}-1),1,"
                  f"MIN(Assumptions!{{c}}{A_ROW['amort_years']},{{k}})))"
                  f"/Assumptions!{{c}}{A_ROW['amort_years']}"))
    wrow("Net intangible assets", unit="closing",
         formula=(f"=IF({{k}}=1,{{c}}{W['Capitalised development']}-{{c}}{r-1},"
                  f"{{p}}{r}+{{c}}{W['Capitalised development']}-{{c}}{r-1})"))

    # ══ P&L ═════════════════════════════════════════════════════════════════
    pl = sheet(wb, "P&L", "Income statement")
    r, P = 4, {}

    def prow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        P[label] = r
        r = row(pl, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    prow("Net revenue", formula=f"=Revenue!{{c}}{R['NET REVENUE']}", font=LINK, bold=True)
    prow("Cost of sales", formula=f"=-Costs!{{c}}{C['TOTAL COST OF SALES']}", font=LINK)
    prow("GROSS PROFIT", formula=f"={{c}}{P['Net revenue']}+{{c}}{P['Cost of sales']}", bold=True, top=True)
    prow("Gross margin", formula=f"={{c}}{P['GROSS PROFIT']}/{{c}}{P['Net revenue']}", fmt=PCT)
    r += 1
    prow("Operating costs", formula=f"=-Costs!{{c}}{C['TOTAL OPERATING COSTS']}", font=LINK)
    prow("EBITDA", formula=f"={{c}}{P['GROSS PROFIT']}+{{c}}{P['Operating costs']}", bold=True, top=True, band=True)
    prow("EBITDA margin", formula=f"={{c}}{P['EBITDA']}/{{c}}{P['Net revenue']}", fmt=PCT)
    prow("Amortisation", formula=f"=-WorkingCap!{{c}}{W['Amortisation']}", font=LINK)
    prow("EBIT", formula=f"={{c}}{P['EBITDA']}+{{c}}{P['Amortisation']}", bold=True)
    r += 1
    r = section(pl, r, "TAX — with loss carryforward and the startup-rate step")
    prow("Losses brought forward", unit="accumulated",
         formula=f"=IF({{k}}=1,0,MIN(0,{{p}}{r+2}))")
    prow("Taxable profit", unit="after offset",
         formula=f"=MAX(0,{{c}}{P['EBIT']}+{{c}}{r-1})")
    prow("Losses carried forward", unit="running",
         formula=f"=MIN(0,{{c}}{P['EBIT']}+IF({{k}}=1,0,{{p}}{r}))")
    prow("Applicable tax rate", unit="15% then 25%", fmt=PCT,
         formula=(f"=IF({{c}}{P['Taxable profit']}<=0,0,"
                  f"IF(COUNTIF($C{P['Taxable profit']}:{{c}}{P['Taxable profit']},\">0\")"
                  f"<=Assumptions!{{c}}{A_ROW['tax_low_years']},"
                  f"Assumptions!{{c}}{A_ROW['tax_low']},Assumptions!{{c}}{A_ROW['tax_high']}))"))
    prow("Tax charge", formula=f"=-{{c}}{P['Taxable profit']}*{{c}}{r-1}")
    prow("NET PROFIT", formula=f"={{c}}{P['EBIT']}+{{c}}{r-1}", bold=True, top=True, band=True)

    # ══ CASH FLOW ═══════════════════════════════════════════════════════════
    cf = sheet(wb, "CashFlow", "Cash flow — indirect method")
    r, F = 4, {}

    def frow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        F[label] = r
        r = row(cf, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    frow("Net profit", formula=f"=P&L!{{c}}{P['NET PROFIT']}", font=LINK)
    frow("Add back amortisation", formula=f"=WorkingCap!{{c}}{W['Amortisation']}", font=LINK)
    frow("Change in working capital", formula=f"=-WorkingCap!{{c}}{W['Change in NWC']}", font=LINK)
    frow("OPERATING CASH FLOW", bold=True, top=True,
         formula=f"=SUM({{c}}{r-3}:{{c}}{r-1})")
    frow("Capital expenditure", formula=f"=-WorkingCap!{{c}}{W['Capitalised development']}", font=LINK)
    frow("FREE CASH FLOW", bold=True, top=True, band=True,
         formula=f"={{c}}{F['OPERATING CASH FLOW']}+{{c}}{r-1}")
    frow("Cumulative free cash flow",
         formula=f"=IF({{k}}=1,{{c}}{F['FREE CASH FLOW']},{{p}}{r}+{{c}}{F['FREE CASH FLOW']})")
    r += 1
    frow("Equity raised", unit="see Funding", formula=f"=Funding!{{c}}5", font=LINK)
    frow("Opening cash", formula=f"=IF({{k}}=1,0,{{p}}{r+1})")
    frow("CLOSING CASH", bold=True, top=True, band=True,
         formula=f"={{c}}{r-1}+{{c}}{F['FREE CASH FLOW']}+{{c}}{F['Equity raised']}")

    # ══ BALANCE SHEET ═══════════════════════════════════════════════════════
    bs = sheet(wb, "BalanceSheet", "Balance sheet")
    r, B = 4, {}

    def brow(label, formula=None, fmt=MONEY, **kw):
        nonlocal r
        B[label] = r
        r = row(bs, r, label, kw.pop("unit", ""), formula=formula, fmt=fmt, **kw)

    r = section(bs, r, "ASSETS")
    brow("Cash", formula=f"=CashFlow!{{c}}{F['CLOSING CASH']}", font=LINK)
    brow("Sponsor receivables", formula=f"=WorkingCap!{{c}}{W['Sponsor receivables']}", font=LINK)
    brow("Net intangible assets", formula=f"=WorkingCap!{{c}}{W['Net intangible assets']}", font=LINK)
    brow("TOTAL ASSETS", bold=True, top=True, band=True, formula=f"=SUM({{c}}{r-3}:{{c}}{r-1})")
    r += 1
    r = section(bs, r, "LIABILITIES")
    brow("Athlete payout float", formula=f"=WorkingCap!{{c}}{W['Athlete payout float']}", font=LINK)
    brow("Trade payables", formula=f"=WorkingCap!{{c}}{W['Trade payables']}", font=LINK)
    brow("TOTAL LIABILITIES", bold=True, top=True, formula=f"={{c}}{r-2}+{{c}}{r-1}")
    r += 1
    r = section(bs, r, "EQUITY")
    brow("Paid-in capital", formula=f"=IF({{k}}=1,Funding!{{c}}5,{{p}}{r}+Funding!{{c}}5)")
    brow("Retained earnings",
         formula=f"=IF({{k}}=1,P&L!{{c}}{P['NET PROFIT']},{{p}}{r}+P&L!{{c}}{P['NET PROFIT']})")
    brow("TOTAL EQUITY", bold=True, top=True, formula=f"={{c}}{r-2}+{{c}}{r-1}")
    brow("Liabilities + equity", bold=True,
         formula=f"={{c}}{B['TOTAL LIABILITIES']}+{{c}}{B['TOTAL EQUITY']}")
    brow("BALANCE CHECK", unit="must be zero", bold=True, top=True,
         formula=f"=ROUND({{c}}{B['TOTAL ASSETS']}-{{c}}{r-1},2)",
         font=Font(bold=True, color="B3272D", name="Calibri", size=10))

    # ══ FUNDING ═════════════════════════════════════════════════════════════
    fu = sheet(wb, "Funding", "Funding rounds and dilution")
    raises = [400_000, 0, 2_000_000, 0, 8_000_000, 0, 0, 0, 0, 0]
    pre = [2_500_000, 0, 10_000_000, 0, 40_000_000, 0, 0, 0, 0, 0]
    r = 4
    r = row(fu, r, "Equity raised", "EUR", values=raises, fmt=MONEY)
    r = row(fu, r, "Pre-money valuation", "EUR", values=pre, fmt=MONEY)
    r = row(fu, r, "Post-money valuation", "EUR", formula="=IF({c}5=0,0,{c}6+{c}5)", fmt=MONEY)
    r = row(fu, r, "New investor stake", "%", formula="=IF({c}7=0,0,{c}5/{c}7)", fmt=PCT)
    r = row(fu, r, "Cumulative dilution", "%",
            formula="=IF({k}=1,{c}8,1-(1-{p}9)*(1-{c}8))", fmt=PCT)
    r = row(fu, r, "Founders + team retained", "%", formula="=1-{c}9", fmt=PCT, bold=True)

    # ══ VALUATION ═══════════════════════════════════════════════════════════
    va = sheet(wb, "Valuation", "Valuation — DCF, NPV, IRR and exit multiples")
    r = 4
    r = row(va, r, "Free cash flow", "EUR", formula=f"=CashFlow!{{c}}{F['FREE CASH FLOW']}",
            fmt=MONEY, font=LINK)
    r = row(va, r, "Discount factor", "1/(1+WACC)^t",
            formula=f"=1/(1+Assumptions!$C${A_ROW['wacc']})^{{k}}", fmt='0.000')
    r = row(va, r, "Discounted FCF", "EUR", formula="={c}4*{c}5", fmt=MONEY, bold=True)
    r += 1
    lastc = COLS[-1]
    blocks = [
        ("DCF", None),
        ("PV of explicit forecast", f"=SUM(C6:{lastc}6)"),
        ("Terminal value at Y10",
         f"=C4*0+{lastc}4*(1+Assumptions!$C${A_ROW['tg']})"
         f"/(Assumptions!$C${A_ROW['wacc']}-Assumptions!$C${A_ROW['tg']})"),
        ("PV of terminal value", f"=C{r+2}*{lastc}5"),
        ("ENTERPRISE VALUE (DCF)", f"=C{r+1}+C{r+3}"),
        ("", None),
        ("RETURN METRICS", None),
        ("NPV of FCF at WACC", f"=NPV(Assumptions!$C${A_ROW['wacc']},C4:{lastc}4)"),
        ("IRR of the plan", f"=IRR(C4:{lastc}4)"),
        ("IRR incl. terminal value", f"=IRR(C4:{get_column_letter(FIRST+N-2)}4,0.3)"),
        ("", None),
        ("EXIT MULTIPLE", None),
        ("Y10 net revenue", f"=Revenue!{lastc}{R['NET REVENUE']}"),
        ("Exit value at Y10", f"=C{r+13}*Assumptions!$C${A_ROW['exit_mult']}"),
        ("Discounted to today", f"=C{r+14}*{lastc}5"),
    ]
    for label, formula in blocks:
        if formula is None:
            if label:
                r = section(va, r, label)
            else:
                r += 1
            continue
        va.cell(r, 1, label).font = BOLD if label.isupper() else Font(name="Calibri", size=10)
        cell = va.cell(r, 3, formula)
        cell.number_format = PCT if "IRR" in label else MONEY
        cell.font = Font(bold=True, name="Calibri", size=10)
        r += 1

    r += 1
    r = section(va, r, "SENSITIVITY — enterprise value by WACC and terminal growth")
    va.cell(r, 1, "Terminal growth \\ WACC").font = BOLD
    waccs = [0.18, 0.20, 0.22, 0.25, 0.28, 0.30]
    for j, w in enumerate(waccs):
        c = va.cell(r, 3 + j, w)
        c.number_format = PCT
        c.font = HEAD
        c.fill = HEAD_FILL
    r += 1
    for g in (0.01, 0.02, 0.03, 0.04, 0.05):
        va.cell(r, 1, g).number_format = PCT
        va.cell(r, 1).font = BOLD
        for j, w in enumerate(waccs):
            # PV of a 10-year FCF strip plus terminal value, at this (w, g) pair
            terms = "+".join(f"CashFlow!{c}{F['FREE CASH FLOW']}/(1+{w})^{k+1}"
                             for k, c in enumerate(COLS))
            tv = (f"CashFlow!{lastc}{F['FREE CASH FLOW']}*(1+{g})/({w}-{g})/(1+{w})^{N}")
            cell = va.cell(r, 3 + j, f"={terms}+{tv}")
            cell.number_format = MONEY
        r += 1

    # ══ CHECK ═══════════════════════════════════════════════════════════════
    ck = sheet(wb, "Check", "Check — the Python model's figures for comparison")
    r = 4
    ck.cell(2, 1, "If the workbook's formulas are right, these match the sheets. "
                  "Generated by business-plan/model.py.").font = Font(italic=True, size=9)
    for label, key, fmt in [
        ("Athletes", "athletes", NUM), ("Paying fans (year end)", "paying_fans", NUM),
        ("Average paying fans", "avg_fans", NUM), ("Deals", "deals", NUM),
        ("Total GMV", "gmv", MONEY), ("Net revenue", "revenue", MONEY),
        ("Cost of sales", "cogs", MONEY), ("Gross profit", "gross", MONEY),
        ("Operating costs", "opex", MONEY), ("EBITDA", "ebitda", MONEY),
    ]:
        r = row(ck, r, label, "python", values=[x[key] for x in rows], fmt=fmt,
                font=Font(name="Calibri", size=10, color="6B7480"))

    out = pathlib.Path(__file__).parent / "Stride_Financial_Model.xlsx"
    wb.save(out)
    return out


if __name__ == "__main__":
    path = build()
    size = path.stat().st_size / 1024
    print(f"wrote {path.name} ({size:.0f} KB)")
