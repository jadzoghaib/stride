"""Generate the two appendices that are assembled rather than written.

    uv run python business-plan/make_appendices.py

Appendix L is the evidence base, generated from `research_data.py` -- the same
table that produces the workbook's Research sheet, so the document and the
model can never disagree about where a number came from.

Appendix M is the product walkthrough, generated from the SHOTS list in
`make_ui_shots.py`, so a screenshot cannot appear in one and not the other.

Both files are overwritten on every run. Do not hand-edit them; edit the source
and regenerate.
"""

from __future__ import annotations

import collections
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))

import research_data as RD  # noqa: E402
from make_ui_shots import SHOTS  # noqa: E402

UI = HERE / "attachments" / "ui"


def evidence() -> str:
    entries = [r for r in RD.ROWS if len(r) > 1]
    method = collections.Counter(r[2] for r in entries)
    conf = collections.Counter(r[5] for r in entries)
    n = len(entries)

    out = [
        "# 17 — Evidence Base: Where Every Assumption Comes From",
        "",
        "*Generated from `research_data.py`, which also produces the Research",
        "sheet of the financial model. Every driver the model runs on appears",
        "here with its method and the comparable behind it. A driver appears*",
        "*twice where two separate decisions rest on it.*",
        "",
        "---",
        "",
        "## 17.1 What the model is built on",
        "",
        f"The model runs on **{n} named assumptions**. Classifying them honestly "
        "matters more than the count, because a plan that presents an estimate "
        "with the same confidence as a published figure is not being read "
        "carefully by its own author.",
        "",
        "| Method | Count | What it means |",
        "|---|---|---|",
        f"| **SOURCED** | {method['SOURCED']} | A published figure, cited |",
        f"| **BENCHMARKED** | {method['BENCHMARKED']} | Set against named comparables |",
        f"| **DERIVED** | {method['DERIVED']} | Computed from other assumptions or from the codebase |",
        f"| **ESTIMATE** | {method['ESTIMATE']} | Reasoned, with no published figure behind it |",
        "",
        "| Confidence | Count |",
        "|---|---|",
        f"| High | {conf['High']} |",
        f"| Medium | {conf['Medium']} |",
        f"| Low | {conf['Low']} |",
        "",
        # Each line of a callout is its own list entry. Written as adjacent
        # string literals Python concatenates them into one, and the "> "
        # markers land in the middle of the sentence instead of starting lines.
        (f"> [!warning] {method['ESTIMATE']} of {n} assumptions are estimates, "
         f"and {conf['Low']} carry low confidence"),
        "> These are listed below rather than buried. The weakest two are the",
        "> athlete count trajectory, which is a target rather than a forecast,",
        "> and sports fandom by country, which is the softest layer of the",
        "> sport index. Both are named as such in the rows that follow.",
        "",
        "---",
        "",
        "## 17.2 The assumptions, in full",
        "",
    ]

    for entry in RD.ROWS:
        if len(entry) == 1:
            title = entry[0].strip().strip("=").strip()
            title = title.replace("\u2014", "").strip()
            out += ["", f"### {title.title()}", "",
                    "| Assumption | Method | Confidence | Benchmark or comparable | Source |",
                    "|---|---|---|---|---|"]
            continue
        label, _key, meth, bench, source, conf_v, _improve = entry
        cell = lambda t: str(t).replace("|", "\\|").replace("\n", " ").strip()
        out.append(f"| **{cell(label)}** | {meth} | {conf_v} | {cell(bench)} | {cell(source)} |")

    out += [
        "",
        "---",
        "",
        "## 17.3 How this table is kept true",
        "",
        "This appendix is generated, not maintained. `research_data.py` is the "
        "single source for both this table and the workbook's Research sheet, "
        "so the document and the model cannot disagree about where a number "
        "came from. What it records is provenance, not value: the numbers "
        "themselves live in the Assumptions sheet, which the workbook "
        "references live, and the prose figures are pinned separately by "
        "`scripts/doc_consistency.py`. Changing a driver therefore updates the "
        "model and the pinned prose, and leaves this table's method and source "
        "columns standing, which is correct only for as long as the reasoning "
        "behind them still holds. That judgement is not automatable.",
        "",
    ]
    return "\n".join(out) + "\n"


def walkthrough() -> str:
    out = [
        "# 18 — Product Walkthrough: The Deployed Demo",
        "",
        "*Screens captured from the running application at "
        "[stride-demo.onrender.com](https://stride-demo.onrender.com), not "
        "mockups. The plan claims a working product exists; this is the "
        "evidence for that claim.*",
        "",
        "---",
        "",
        "## 18.1 What is actually built",
        "",
        "The demo carries all four roles the marketplace needs, real "
        "authentication, and seeded data behind every figure on screen. The "
        "marketability score shown on the athlete dashboard is computed by the "
        "same scoring code described in Appendix K, not typed into a fixture.",
        "",
        "Anyone may sign in with the accounts shown on the first screen. The "
        "container sleeps between visits, so the first page load takes about "
        "forty seconds.",
        "",
        "---",
        "",
    ]
    missing = []
    # Screens start at 18.2 because 18.1 is the prose above them.
    for i, (name, email, path, title, caption) in enumerate(SHOTS, 2):
        png = UI / f"{name}.png"
        if not png.exists():
            missing.append(name)
            continue
        who = "signed out" if email is None else f"`{email}`"
        out += [
            f"## 18.{i} {title}",
            "",
            f"![{title} — {path}](attachments/ui/{name}.png)",
            "",
            f"{caption} Route `{path}`, viewed {who}.",
            "",
        ]
    if missing:
        print(f"  ! missing screenshots: {', '.join(missing)}", file=sys.stderr)
    return "\n".join(out)


def main() -> int:
    (HERE / "17-evidence-base.md").write_text(evidence(), encoding="utf-8")
    print(f"  17-evidence-base.md   {len([r for r in RD.ROWS if len(r) > 1])} assumptions")
    (HERE / "18-product-walkthrough.md").write_text(walkthrough(), encoding="utf-8")
    shots = sum(1 for n, *_ in SHOTS if (UI / f"{n}.png").exists())
    print(f"  18-product-walkthrough.md   {shots} screens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
