"""Do the business-plan documents still agree with the model behind them?

    python scripts/doc_consistency.py

Tables inside `<!-- MODEL:key -->` markers regenerate themselves, so they cannot
drift. Prose can, and did: several figures survived the Stripe rate correction
unchanged, and two documents ended up contradicting each other about the same
number — one saying a EUR 4.99 tier retains 54% of our take, the other 47%.

So every load-bearing number written in prose is pinned here against the code
that produces it. A claim is read back out of the document with a regex and
recomputed from `model.py`; drift fails the run and names the file.

Adding a claim is cheap. The rule of thumb: if a number in a document came out
of the model, it belongs in this list or inside a MODEL marker — never loose in
a sentence with nothing watching it.
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "business-plan"))

import model  # noqa: E402

A = model.A
ROWS = model.build()
VAL = model.valuation(ROWS)
Y1, Y7, Y10 = ROWS[0], ROWS[6], ROWS[9]


def retained(price: float) -> float:
    take = price * A.take_fan
    return (take - (price * A.psp_pct + A.psp_fixed_eur)) / take


def blended_cac(r: dict) -> float:
    adds = r["athlete_gross_adds"]
    return (r["cac_per_application"] * r["applications"] / adds) if adds else 0.0


def take_rate_delta() -> float:
    """Y7 revenue forgone by charging 15% on fan revenue instead of 20%."""
    import copy
    alt = copy.deepcopy(A)
    alt.segments = A.segments          # deepcopy would detach the segment objects
    alt.take_fan = 0.20
    original, model.A = model.A, alt
    try:
        return model.build()[6]["revenue"] - Y7["revenue"]
    finally:
        model.A = original


# (document, description, regex capturing one number, expected value, tolerance)
CLAIMS: list[tuple[str, str, str, float, float]] = [
    ("01-revenue-model.md", "EUR 4.99 retains x% of take",
     r"€4\.99 tier retains (\d+)% of our take", retained(4.99) * 100, 0.5),
    ("01-revenue-model.md", "Y7 SaaS revenue",
     r"By Y7 it is €([\d.]+)M of the", Y7["rev_saas"] / 1e6, 0.01),
    ("01-revenue-model.md", "Y7 total revenue",
     r"By Y7 it is €[\d.]+M of the €([\d.]+)M", Y7["revenue"] / 1e6, 0.02),
    ("01-revenue-model.md", "SaaS as share of Y7 gross profit",
     r"which is roughly (\d+)% of gross profit", Y7["rev_saas"] / Y7["gross"] * 100, 0.6),
    ("01-revenue-model.md", "Passes crossover",
     r"cross at \*\*€([\d,]+)/month", 27 / ((A.take_fan - 0.10) - 0.28 / A.avg_fan_txn_eur), 5),

    ("02-cost-model.md", "payments vs infrastructure multiple",
     r"\*\*Payments are (\w+) times larger", Y7["psp"] / Y7["infra"], 0.6),
    ("02-cost-model.md", "Y1 applications behind one athlete",
     r"Applications behind the athlete plan \| ([\d,]+) ", Y1["applications"], 1),
    ("02-cost-model.md", "Y1 manual reviews", r"\| Manual reviews \| ([\d,]+) ", Y1["reviews"], 1),
    ("02-cost-model.md", "peak verification cost",
     r"Verification peaks at\s+€(\d+)k a year", 46.7, 0.6),

    ("07-open-questions.md", "EUR 4.99 retention",
     r"€4\.99 retains (\d+)% of our take", retained(4.99) * 100, 0.5),
    ("07-open-questions.md", "EUR 9.99 retention",
     r"€9\.99 retains (\d+)%", retained(9.99) * 100, 0.5),
    ("07-open-questions.md", "season pass retention",
     r"season pass retains (\d+)%", retained(89) * 100, 0.5),
    ("07-open-questions.md", "revenue forgone by 15% vs 20%",
     r"forfeits €([\d.]+)M of Y7 revenue", take_rate_delta() / 1e6, 0.1),
    ("07-open-questions.md", "DCF headline",
     r"the DCF \(€([\d.]+)M\)", VAL["enterprise_value"] / 1e6, 0.1),

    ("11-admission-and-matching.md", "peak reviewer FTE",
     r"(\d\.\d+) of one\s+reviewer", max(r["review_fte"] for r in ROWS), 0.01),
    ("11-admission-and-matching.md", "Y10 blended admission rate",
     r"admission rate climbs from 20% to (\d+)%", Y10["admit_rate"] * 100, 0.6),
]

WORDS = {"fourteen": 14, "fifteen": 15, "sixteen": 16, "twenty": 20, "ten": 10, "twelve": 12}


def check_duplicated_sport_table() -> list[str]:
    """`admission.py` copies the agent-density column out of `sport_data.py`,
    because the sport index is a planning module outside the API package. A copy
    with nothing watching it is a copy that drifts, and the admission ladder
    would quietly start reading a different sport structure than the index the
    business plan argues from."""
    sys.path.insert(0, str(ROOT / "apps" / "api"))
    from sport_data import SPORTS
    from stride_api.admission import AGENT_DENSITY
    source = {name: density for name, _, _, density in SPORTS}
    out = []
    for sport, density in AGENT_DENSITY.items():
        if source.get(sport) != density:
            out.append(f"admission.py AGENT_DENSITY[{sport!r}]={density} but sport_data.py "
                       f"says {source.get(sport)}")
    for sport in set(source) - set(AGENT_DENSITY):
        out.append(f"sport_data.py has {sport!r}; admission.py does not, so it falls back to neutral")
    return out


def main() -> int:
    failures = check_duplicated_sport_table()
    for doc, label, pattern, expected, tol in CLAIMS:
        path = ROOT / "business-plan" / doc
        text = path.read_text(encoding="utf-8")
        m = re.search(pattern, text)
        if not m:
            failures.append(f"{doc}: claim not found — {label}  /{pattern}/")
            continue
        raw = m.group(1)
        found = float(WORDS.get(raw, raw.replace(",", "")))
        if abs(found - expected) > tol:
            failures.append(f"{doc}: {label} says {found:,.2f}, model says {expected:,.2f}")

    print(f"checked {len(CLAIMS)} prose claims across "
          f"{len({c[0] for c in CLAIMS})} documents, plus the duplicated sport table")
    if failures:
        print(f"\nDRIFT ({len(failures)}):")
        for f in failures:
            print("  -", f)
        return 1
    print("every figure written in prose still matches the model behind it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
