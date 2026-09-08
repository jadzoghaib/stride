"""Draw the twelve plan exhibits from the generated data.

Every chart reads `attachments/chart-data/*.csv`, which `graph_data.py` writes
from `model.py`. Nothing here re-keys a number, so a chart cannot disagree with
the model that produced it.

Two exceptions, both deliberate and both documented on the chart itself:

* **G2** is illustrative. Nothing in the repository measures athlete income, so
  this is the argument of section 2.3 drawn rather than a finding. It says so
  in the subtitle, because an unlabelled illustrative chart is a lie.
* **G12** parses the risk register out of the plan's own markdown rather than a
  copied table, so the risk map cannot drift from the register the way a
  re-keyed spreadsheet does.

    uv run --with matplotlib python business-plan/make_charts.py
"""

from __future__ import annotations

import csv
import pathlib
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                    # noqa: E402
from matplotlib.ticker import FuncFormatter                        # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "attachments" / "chart-data"
OUT = HERE / "attachments" / "charts"
DRAFT = HERE / "stride-business-plan-draft.md"

# ── house style ─────────────────────────────────────────────────────────────
INK = "#1F2937"      # near-black, the body colour
MUTED = "#9CA3AF"    # grid and secondary text
AMBER = "#D97706"    # the accent, used once per chart
TEAL = "#0F766E"     # the second series
ROSE = "#B3272D"     # loss, risk, the naive option
SAND = "#E5E7EB"     # fills

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.family": "DejaVu Sans",
    "font.size": 8.5,
    "axes.edgecolor": MUTED,
    "axes.labelcolor": INK,
    "axes.titlesize": 10.5,
    "axes.titleweight": "bold",
    "axes.titlecolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "grid.color": SAND,
    "grid.linewidth": 0.6,
    "legend.frameon": False,
})

WIDTH = 6.5          # inches, to sit inside Word's default margins


def rows(name: str) -> list[dict]:
    with (DATA / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def save(fig, name: str, source: str) -> None:
    fig.text(0.01, -0.04, source, fontsize=6, color=MUTED, ha="left",
             va="top", wrap=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {path.relative_to(HERE.parent)}")


def title(ax, head: str, sub: str = "") -> None:
    ax.set_title(head, loc="left", pad=14 if sub else 8)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=7.5,
                color=MUTED, va="bottom")


def eur_m(x, _=None) -> str:
    if x == 0:
        return "€0M"
    return f"€{x:,.0f}M" if abs(x) >= 1 else f"€{x:,.1f}M"


# ── G1 · revenue and EBITDA ─────────────────────────────────────────────────
def g1() -> None:
    d = rows("g1-revenue-ebitda.csv")
    yr = [int(r["year"]) for r in d]
    rev = [float(r["revenue_eur_m"]) for r in d]
    eb = [float(r["ebitda_eur_m"]) for r in d]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    ax.bar(yr, rev, color=SAND, edgecolor=MUTED, linewidth=0.5, label="Net revenue")
    ax.plot(yr, eb, color=AMBER, marker="o", markersize=4, linewidth=2, label="EBITDA")
    ax.axhline(0, color=INK, linewidth=0.8)

    cross = next(r["year"] for r in d if float(r["ebitda_eur_m"]) > 0)
    ax.annotate(f"EBITDA positive\nY{cross}", xy=(int(cross), 0),
                xytext=(int(cross) - 0.4, max(rev) * 0.42), fontsize=7.5,
                color=AMBER, ha="center",
                arrowprops=dict(arrowstyle="->", color=AMBER, lw=1))

    ax.set_xticks(yr)
    ax.set_xticklabels([f"Y{y}" for y in yr])
    ax.yaxis.set_major_formatter(FuncFormatter(eur_m))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")
    title(ax, "The plan in one frame",
          "Net revenue and EBITDA, Y1–Y7. Losses are small and end early.")
    save(fig, "g1-revenue-ebitda.png", "Source: model.py via g1-revenue-ebitda.csv")


# ── G2 · the decoupling (illustrative) ──────────────────────────────────────
def g2() -> None:
    rank = list(range(1, 26))
    # A popular sport: income tracks rank tightly. A niche one: it does not.
    popular = [90_000 * (0.80 ** (r - 1)) + 800 for r in rank]
    niche = [1_400, 900, 1_100, 600, 700, 500, 450, 800, 300, 400,
             350, 500, 250, 300, 200, 260, 180, 240, 150, 200,
             130, 170, 110, 140, 90]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    ax.scatter(rank, popular, s=26, color=TEAL, label="Popular sport", zorder=3)
    ax.scatter(rank, niche, s=26, color=AMBER, label="Niche sport", zorder=3)
    ax.set_yscale("symlog", linthresh=1000)

    ax.scatter([1], [niche[0]], s=320, facecolors="none", edgecolors=ROSE,
               linewidths=1.6, zorder=4)
    ax.annotate("the arbitrage —\na national champion\nearning nothing",
                xy=(1.6, niche[0]), xytext=(4.2, 14_000), fontsize=7.5,
                color=ROSE, arrowprops=dict(arrowstyle="->", color=ROSE, lw=1))

    ax.set_xlabel("Sporting rank in the sport (1 = best)")
    ax.set_ylabel("Annual sponsorship income")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper right")
    title(ax, "The decoupling",
          "ILLUSTRATIVE — the argument of §2.3 drawn, not a measurement. "
          "In one sport the axes are the same line; in the other they are unrelated.")
    save(fig, "g2-decoupling.png",
         "Illustrative. Nothing in the repository measures athlete income; a real "
         "version needs the federation and income data §9.1 asks for.")


# ── G3 · the market funnel ──────────────────────────────────────────────────
def g3() -> None:
    d = rows("g3-market-funnel.csv")
    labels = [r["step"].replace(" -- ", " — ") for r in d][::-1]
    vals = [int(r["people"]) for r in d][::-1]
    colours = [AMBER if i < 2 else SAND for i in range(len(vals))]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    bars = ax.barh(labels, vals, color=colours, edgecolor=MUTED, linewidth=0.5)
    ax.set_xscale("log")
    for bar, v in zip(bars, vals):
        ax.text(v * 1.25, bar.get_y() + bar.get_height() / 2,
                f"{v:,}", va="center", fontsize=7.5, color=INK)
    ax.set_xlim(right=max(vals) * 12)
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=7.5)
    title(ax, "From 520 million people to the athletes we can serve",
          "Logarithmic — four orders of magnitude. The last two bars are the plan.")
    save(fig, "g3-market-funnel.png", "Source: g3-market-funnel.csv")


# ── G4 · the sport index ────────────────────────────────────────────────────
def g4() -> None:
    d = rows("g4-sport-index.csv")
    others = [r for r in d if r["country"] != "Spain"]
    spain = [r for r in d if r["country"] == "Spain"]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    ax.scatter([float(r["agent_density"]) for r in others],
               [float(r["score"]) for r in others],
               s=9, color=SAND, edgecolors=MUTED, linewidths=0.2,
               label=f"{len(others)} other country × sport pairs", zorder=2)
    ax.scatter([float(r["agent_density"]) for r in spain],
               [float(r["score"]) for r in spain],
               s=34, color=AMBER, edgecolors=INK, linewidths=0.4,
               label=f"Spain ({len(spain)})", zorder=3)

    ax.set_xlabel("Agent density  (0 = no intermediary exists)")
    ax.set_ylabel("Opportunity score")
    ax.axvspan(-0.02, 0.25, color=AMBER, alpha=0.07, zorder=1)
    ax.text(0.005, ax.get_ylim()[1] * 0.99, " where we start", fontsize=7.5,
            color=AMBER, va="top")
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right")
    title(ax, "714 country × sport pairs, and where Spain sits",
          "The wedge is the left edge: high opportunity, no incumbent to fight.")
    save(fig, "g4-sport-index.png", "Source: sport_index.py via g4-sport-index.csv")


# ── G5 · the competitive map ────────────────────────────────────────────────
def g5() -> None:
    d = rows("g5-competitive-map.csv")

    fig, ax = plt.subplots(figsize=(WIDTH, 3.4))
    for r in d:
        stride = r["player"] == "Stride"
        x, y = float(r["long_tail_reach_0_10"]), float(r["fan_monetisation_0_10"])
        ax.scatter(x, y, s=170 if stride else 90,
                   color=AMBER if stride else SAND,
                   edgecolors=INK if stride else MUTED,
                   linewidths=1.0 if stride else 0.5, zorder=3)
        ax.annotate(r["player"], xy=(x, y), xytext=(0, 11 if stride else -14),
                    textcoords="offset points", ha="center", fontsize=7.5,
                    fontweight="bold" if stride else "normal",
                    color=INK if stride else MUTED)

    ax.axvspan(6.5, 10.6, ymin=0.62, color=AMBER, alpha=0.07, zorder=1)
    ax.set_xlim(-0.6, 10.6)
    ax.set_ylim(-1.2, 10.8)
    ax.set_xlabel("Reach into the long tail  →")
    ax.set_ylabel("Fan monetisation  →")
    ax.grid(True)
    ax.set_axisbelow(True)
    title(ax, "The empty corner",
          "Everyone else serves the head, and nobody monetises the fan.")
    save(fig, "g5-competitive-map.png", "Source: g5-competitive-map.csv")


# ── G6 · revenue mix ────────────────────────────────────────────────────────
def g6() -> None:
    d = rows("g6-revenue-mix.csv")
    yr = [int(r["year"]) for r in d]
    fan = [float(r["fan_eur_m"]) for r in d]
    spo = [float(r["sponsorship_eur_m"]) for r in d]
    saas = [float(r["saas_eur_m"]) for r in d]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    ax.stackplot(yr, fan, spo, saas, colors=[AMBER, TEAL, SAND],
                 edgecolor="white", linewidth=0.6,
                 labels=["Fan subscriptions", "Sponsorship", "Sponsor SaaS"])
    ax.set_xticks(yr)
    ax.set_xticklabels([f"Y{y}" for y in yr])
    ax.set_xlim(min(yr), max(yr))
    ax.yaxis.set_major_formatter(FuncFormatter(eur_m))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")
    first, last = float(d[0]["fan_share_pct"]), float(d[-1]["fan_share_pct"])
    title(ax, "The business changes shape",
          f"Fan revenue leads throughout, falling from {first:.0f}% to {last:.0f}% "
          "of the mix as the other two compound behind it.")
    save(fig, "g6-revenue-mix.png", "Source: g6-revenue-mix.csv")


# ── G7 · unit economics ─────────────────────────────────────────────────────
def g7() -> None:
    d = rows("g7-unit-economics.csv")
    yr = [int(r["year"]) for r in d]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(WIDTH, 2.9))
    ax1.plot(yr, [float(r["niche_cac_eur"]) for r in d], color=AMBER,
             marker="o", markersize=3, linewidth=1.8, label="Niche")
    ax1.plot(yr, [float(r["popular_cac_eur"]) for r in d], color=TEAL,
             marker="o", markersize=3, linewidth=1.8, label="Popular")
    ax1.set_ylabel("Athlete CAC")
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax1.legend()
    ax1.grid(axis="y")
    ax1.set_axisbelow(True)
    ax1.set_title("Acquisition cost", loc="left", fontsize=9)

    ax2.plot(yr, [float(r["niche_monetise_pct"]) for r in d], color=AMBER,
             marker="o", markersize=3, linewidth=1.8, label="Niche")
    ax2.plot(yr, [float(r["popular_monetise_pct"]) for r in d], color=TEAL,
             marker="o", markersize=3, linewidth=1.8, label="Popular")
    ax2.set_ylabel("Athletes who monetise")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.legend()
    ax2.grid(axis="y")
    ax2.set_axisbelow(True)
    ax2.set_title("Share monetising", loc="left", fontsize=9)

    for ax in (ax1, ax2):
        ax.set_xticks(yr[::2])
        ax.set_xticklabels([f"Y{y}" for y in yr[::2]])
    fig.suptitle("Why niche first, in two lines", x=0.005, ha="left",
                 fontsize=10.5, fontweight="bold", color=INK)
    fig.tight_layout(rect=[0, 0.02, 1, 0.94])
    save(fig, "g7-unit-economics.png", "Source: g7-unit-economics.csv")


# ── G8 · the trough and the buffer ──────────────────────────────────────────
def g8() -> None:
    d = rows("g8-cash-and-capital.csv")
    # Y1-Y5, not Y1-Y7. The argument is a EUR 464k trough and the band above
    # it; against a EUR 5.3M Y7 balance that band is 9% of the axis and
    # invisible. G1 already carries the full seven-year shape.
    seven = d[:5]
    yr = [int(r["year"]) for r in seven]
    cum = [float(r["cumulative_cash_before_raises_eur_m"]) for r in seven]
    trough = min(cum)
    t_year = yr[cum.index(trough)]
    preseed = next(float(r["raise_eur_m"]) for r in d if r["stage"] == "Pre-seed")

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    ax.plot(yr, cum, color=INK, marker="o", markersize=4, linewidth=2,
            label="Cumulative cash, before raises", zorder=3)
    ax.axhline(0, color=MUTED, linewidth=0.8)
    ax.axhline(-preseed, color=AMBER, linewidth=1.6, linestyle="--",
               label=f"€{preseed:.1f}M pre-seed", zorder=2)
    # Only while the company is under water. Filling every year the cash line
    # sits above the pre-seed shades the whole balance sheet by Y7 and buries
    # the one band this chart exists to show.
    ax.fill_between(yr, [-preseed] * len(yr), cum, where=[c < 0 for c in cum],
                    color=AMBER, alpha=0.14, zorder=1, interpolate=True)
    ax.annotate(f"trough €{abs(trough) * 1000:,.0f}k, Y{t_year}",
                xy=(t_year, trough), xytext=(t_year - 2.4, trough + 0.22),
                fontsize=7.5, color=ROSE, ha="left",
                arrowprops=dict(arrowstyle="->", color=ROSE, lw=1))
    ax.text(yr[0] + 0.08, (-preseed + trough) / 2, "buffer", fontsize=7.5,
            color=AMBER, va="center")

    for r in d[:7]:
        if r["stage"]:
            ax.annotate(r["stage"], xy=(int(r["year"]), 0.06),
                        fontsize=7, color=TEAL, ha="center")
    ax.set_xticks(yr)
    ax.set_xticklabels([f"Y{y}" for y in yr])
    ax.yaxis.set_major_formatter(FuncFormatter(eur_m))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    # Lower right: the stage labels sit along the zero line at upper left.
    ax.legend(loc="lower right")
    title(ax, "The hole, and the buffer over it",
          "Y1–Y5, where the trough lives. The shaded band is the margin the "
          "pre-seed clears it by; cash turns positive in Y5.")
    save(fig, "g8-cash-and-capital.png", "Source: g8-cash-and-capital.csv")


# ── G9 · the take-rate corridor ─────────────────────────────────────────────
def g9() -> None:
    d = rows("g9-take-rate-corridor.csv")
    labels = [r["fan_take"] for r in d]
    rev = [float(r["y7_revenue_eur_m"]) for r in d]
    eb = [float(r["y7_ebitda_eur_m"]) for r in d]
    x = range(len(d))

    fig, ax = plt.subplots(figsize=(WIDTH, 3.0))
    ax.bar([i - 0.19 for i in x], rev, width=0.38, color=SAND,
           edgecolor=MUTED, linewidth=0.5, label="Y7 net revenue")
    ax.bar([i + 0.19 for i in x], eb, width=0.38, color=AMBER,
           edgecolor=MUTED, linewidth=0.5, label="Y7 EBITDA")
    for i, (r, e) in enumerate(zip(rev, eb)):
        ax.text(i - 0.19, r + 0.25, f"€{r:.1f}M", ha="center", fontsize=7)
        ax.text(i + 0.19, e + 0.25, f"€{e:.1f}M", ha="center", fontsize=7)

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"{lab}\n{r['against']}" for lab, r in zip(labels, d)],
                       fontsize=7.5)
    ax.set_ylim(top=max(rev) * 1.2)
    ax.yaxis.set_major_formatter(FuncFormatter(eur_m))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper left")
    title(ax, "The take-rate corridor",
          "Both ends are real competitor rates. Five points down costs "
          "nearly half of EBITDA, because the cost base does not shrink with the take.")
    save(fig, "g9-take-rate-corridor.png", "Source: g9-take-rate-corridor.csv")


# ── G10 · the football field ────────────────────────────────────────────────
def g10() -> None:
    d = rows("g10-valuation.csv")
    labels = [r["method"] for r in d][::-1]
    vals = [float(r["value_eur_m"]) for r in d][::-1]
    colours = [AMBER if lab == "DCF" else SAND for lab in labels]

    fig, ax = plt.subplots(figsize=(WIDTH, 2.9))
    bars = ax.barh(labels, vals, color=colours, edgecolor=MUTED, linewidth=0.5)
    for bar, v in zip(bars, vals):
        ax.text(v * 1.02, bar.get_y() + bar.get_height() / 2,
                f"€{v:,.1f}M", va="center", fontsize=7.5)
    ax.set_xlim(right=max(vals) * 1.18)
    ax.set_xlabel("Enterprise value at Y10, except the DCF which is today")
    ax.xaxis.set_major_formatter(FuncFormatter(eur_m))
    ax.grid(axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=7.5)
    title(ax, "Two methods that disagree, for a reason",
          "The DCF is the floor: it assumes growth stops dead after Y10.")
    save(fig, "g10-valuation.png", "Source: g10-valuation.csv")


# ── G11 · what cost of revenue is made of ───────────────────────────────────
def g11() -> None:
    d = rows("g11-cogs-composition.csv")
    yr = [int(r["year"]) for r in d]
    pay = [float(r["payments_eur_k"]) for r in d]
    inf = [float(r["infrastructure_eur_k"]) for r in d]
    mod = [float(r["moderation_eur_k"]) for r in d]
    ver = [float(r["verification_eur_k"]) for r in d]
    naive = [float(r["infrastructure_naive_eur_k"]) for r in d]

    fig, ax = plt.subplots(figsize=(WIDTH, 3.2))
    bottom = [0.0] * len(yr)
    for vals, colour, label in ((pay, AMBER, "Payment processing"),
                                (inf, TEAL, "Infrastructure"),
                                (mod, SAND, "Moderation"),
                                (ver, MUTED, "Verification")):
        ax.bar(yr, vals, bottom=bottom, color=colour, edgecolor="white",
               linewidth=0.5, label=label)
        bottom = [b + v for b, v in zip(bottom, vals)]

    ax.plot(yr, naive, color=ROSE, linestyle="--", linewidth=1.4, marker="o",
            markersize=3, label="Infrastructure, naive CDN")
    ax.set_xticks(yr)
    ax.set_xticklabels([f"Y{y}" for y in yr])
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"€{v:,.0f}k"))
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(loc="upper left", fontsize=7.5)
    share = 100 * pay[-1] / (pay[-1] + inf[-1] + mod[-1] + ver[-1])
    title(ax, "It is a payments bill",
          f"Payment processing is {share:.0f}% of cost of revenue at Y7. "
          "The dashed line is the infrastructure we chose not to buy.")
    save(fig, "g11-cogs-composition.png", "Source: g11-cogs-composition.csv")


# ── G12 · the risk map, parsed from the register itself ─────────────────────
RISK = re.compile(r"^\|\s*\*\*(R\d+)\*\*\s*\|\s*(.+?)\s*\|\s*(\d)\s*\|\s*(\d)\s*\|")


def read_risks() -> list[tuple[str, int, int]]:
    out = []
    for line in DRAFT.read_text(encoding="utf-8").splitlines():
        m = RISK.match(line)
        if m:
            out.append((m.group(1), int(m.group(3)), int(m.group(4))))
    if not out:
        raise SystemExit("no risks parsed from the register — has the table changed?")
    return out


def g12() -> None:
    risks = read_risks()

    fig, ax = plt.subplots(figsize=(WIDTH, 3.6))
    # Shade by SCORE, not by a fixed top-right quadrant. Nothing here is rated
    # above probability 3, so a P>=4 quadrant contains no risk at all and the
    # chart contradicted its own title.
    for px in range(1, 6):
        for iy in range(1, 6):
            if px * iy >= 12:
                ax.add_patch(plt.Rectangle((px - 0.5, iy - 0.5), 1, 1,
                                           color=ROSE, alpha=0.07, zorder=1))
    ax.text(5.45, 5.45, "score ≥ 12", fontsize=7.5, color=ROSE,
            ha="right", va="top")

    placed: dict[tuple[int, int], int] = {}
    for code, p, i in risks:
        n = placed.get((p, i), 0)
        placed[(p, i)] = n + 1
        dx = 0.16 * n
        score = p * i
        ax.scatter(p + dx, i, s=42 + score * 12,
                   color=ROSE if score >= 12 else (AMBER if score >= 8 else SAND),
                   edgecolors=INK, linewidths=0.4, zorder=3)
        # Alternate the label above and below so two dots sharing a cell do not
        # print their codes on top of one another.
        ax.annotate(code, xy=(p + dx, i), xytext=(0, 11 if n % 2 == 0 else -17),
                    textcoords="offset points", ha="center", fontsize=7,
                    fontweight="bold" if score >= 12 else "normal")

    ax.set_xlim(0.4, 5.9)
    ax.set_ylim(0.4, 5.9)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel("Probability  →")
    ax.set_ylabel("Impact  →")
    ax.grid(True)
    ax.set_axisbelow(True)
    top = [c for c, p, i in risks if p * i >= 12]
    worst = max(risks, key=lambda r: r[1] * r[2])
    title(ax, f"{worst[0]} scores above everything else, and it is the thesis",
          f"{len(risks)} risks scored probability × impact. "
          f"{', '.join(top)} clear 12; nothing is rated more likely than 3, "
          "which is why the map has no far-right column.")
    save(fig, "g12-risk-map.png",
         "Parsed directly from the risk register in §7 of the plan, not from a copy.")


def main() -> None:
    for fn in (g1, g2, g3, g4, g5, g6, g7, g8, g9, g10, g11, g12):
        fn()
    print(f"\n12 exhibits written to {OUT.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
