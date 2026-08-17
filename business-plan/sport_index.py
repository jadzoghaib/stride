"""Stride Sport Opportunity Index.

Ranks a sport, in a region, by how well it fits Stride — and classifies it as a
**disintermediation** play (an agent already takes the value) or a **market
creation** play (nobody does).

    python business-plan/sport_index.py            # Spain ranking
    python business-plan/sport_index.py --global   # global ranking
    python business-plan/sport_index.py --explain padel

The four signals, and why each is in the formula:

  supply        participants per 1,000 people — how many athletes we can sign
  demand        followers/spectators per 1,000 — how many people might pay
  gap           1 − agent density — how much of the value is still unclaimed
  appetite      participation / (participation + fandom)

`appetite` is the one that is not obvious and is doing the most work. It asks:
**do the fans of this sport also DO the sport?** A trail runner's audience is
other trail runners, who want training knowledge and will pay for it. A
football fan watches and does not want a training plan. Participatory sports
already have the content habit — athletes publish training logs for free on
platforms that pay them nothing — so the paywall is the only missing piece.

Scores are computed per region and blended with the global score, because an
athlete's audience is mostly local but their ceiling is not. Padel is the
clearest case: globally mid-table, in Spain the single best market in the world.

DATA PROVENANCE: padel figures for Spain are sourced (see SOURCES). Everything
else is a reasoned estimate at the right order of magnitude, marked `est`.
The methodology is the deliverable; the numbers are meant to be replaced with
federation licence data (public via CSD in Spain) and a media-measurement panel.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

SOURCES = {
    "padel_es": "FIP World Padel Report 2025 — ~6.0M active players in Spain (12.7% of population), "
                "109,040 federation licences (2024), 17,300+ courts",
    "padel_global": "FIP 2025 — 35M+ players worldwide, 77,000+ courts",
}


@dataclass
class Sport:
    name: str
    # per 1,000 population
    participation: float      # people who actively do it
    fandom: float             # people who follow/watch it
    agent_density: float      # 0..1 — share of commercially active athletes with representation
    sourced: bool = False     # True where the figure is from a cited source, not an estimate


# ── Spain ────────────────────────────────────────────────────────────────────
# Population ~48.6M. Padel from FIP; the rest are estimates of the right shape.
SPAIN: list[Sport] = [
    Sport("running / trail", participation=150.0, fandom=40.0, agent_density=0.10),
    Sport("padel",           participation=127.0, fandom=90.0, agent_density=0.15, sourced=True),
    Sport("cycling",         participation=60.0,  fandom=120.0, agent_density=0.35),
    Sport("swimming",        participation=25.0,  fandom=35.0,  agent_density=0.25),
    Sport("football",        participation=22.0,  fandom=600.0, agent_density=0.85),
    Sport("tennis",          participation=20.0,  fandom=180.0, agent_density=0.75),
    Sport("climbing",        participation=12.0,  fandom=10.0,  agent_density=0.10),
    Sport("athletics",       participation=12.0,  fandom=60.0,  agent_density=0.45),
    Sport("basketball",      participation=8.0,   fandom=250.0, agent_density=0.70),
    Sport("triathlon",       participation=8.0,   fandom=15.0,  agent_density=0.12),
    Sport("surfing",         participation=6.0,   fandom=20.0,  agent_density=0.20),
    Sport("handball",        participation=4.0,   fandom=45.0,  agent_density=0.40),
    Sport("rowing",          participation=2.0,   fandom=8.0,   agent_density=0.15),
    Sport("motorsport",      participation=1.0,   fandom=200.0, agent_density=0.80),
]

# ── Global ───────────────────────────────────────────────────────────────────
GLOBAL: list[Sport] = [
    Sport("running / trail", participation=90.0, fandom=35.0,  agent_density=0.12),
    Sport("football",        participation=45.0, fandom=700.0, agent_density=0.88),
    Sport("cycling",         participation=40.0, fandom=90.0,  agent_density=0.38),
    Sport("swimming",        participation=30.0, fandom=40.0,  agent_density=0.28),
    Sport("basketball",      participation=28.0, fandom=400.0, agent_density=0.78),
    Sport("tennis",          participation=12.0, fandom=200.0, agent_density=0.78),
    Sport("padel",           participation=4.4,  fandom=6.0,   agent_density=0.18, sourced=True),
    Sport("climbing",        participation=8.0,  fandom=12.0,  agent_density=0.15),
    Sport("athletics",       participation=10.0, fandom=120.0, agent_density=0.50),
    Sport("triathlon",       participation=3.0,  fandom=10.0,  agent_density=0.15),
    Sport("surfing",         participation=5.0,  fandom=25.0,  agent_density=0.25),
    Sport("handball",        participation=4.0,  fandom=30.0,  agent_density=0.42),
    Sport("rowing",          participation=2.0,  fandom=10.0,  agent_density=0.18),
    Sport("motorsport",      participation=0.8,  fandom=180.0, agent_density=0.85),
]

WEIGHTS = {"supply": 0.30, "demand": 0.20, "gap": 0.30, "appetite": 0.20}

REGIONAL_WEIGHT = 0.60   # the athlete's audience is mostly local
GLOBAL_WEIGHT = 0.40     # but the ceiling is not

# Above this share of athletes being represented, an agent is the incumbent and
# the pitch changes from "here is a market" to "here is a better deal".
POPULAR_THRESHOLD = 0.45


def _lognorm(value: float, lo: float, hi: float) -> float:
    """Log-scaled 0..1. Participation and fandom span orders of magnitude, so a
    linear normalisation would let football's fandom flatten everything else."""
    if value <= 0:
        return 0.0
    v, a, b = math.log10(value), math.log10(lo), math.log10(hi)
    return max(0.0, min(1.0, (v - a) / (b - a)))


def components(s: Sport) -> dict[str, float]:
    return {
        "supply": _lognorm(s.participation, 0.5, 160.0),
        "demand": _lognorm(s.fandom, 5.0, 700.0),
        "gap": 1.0 - s.agent_density,
        "appetite": s.participation / (s.participation + s.fandom),
    }


def score(s: Sport) -> float:
    c = components(s)
    return 100 * sum(WEIGHTS[k] * c[k] for k in WEIGHTS)


def segment(s: Sport) -> str:
    return "popular" if s.agent_density >= POPULAR_THRESHOLD else "niche"


def blended(name: str) -> dict:
    """Regional (Spain) blended with global — the number that should drive
    go-to-market, and the one that belongs in the product."""
    es = next((x for x in SPAIN if x.name == name), None)
    gl = next((x for x in GLOBAL if x.name == name), None)
    if es is None or gl is None:
        raise KeyError(name)
    b = REGIONAL_WEIGHT * score(es) + GLOBAL_WEIGHT * score(gl)
    return {
        "sport": name,
        "regional": score(es),
        "global": score(gl),
        "blended": b,
        "segment": segment(es),
        "play": "disintermediation" if segment(es) == "popular" else "market creation",
        "sourced": es.sourced,
    }


def table(rows: list[list[str]], head: list[str]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


def ranking() -> list[dict]:
    return sorted((blended(s.name) for s in SPAIN), key=lambda r: -r["blended"])


def main() -> None:
    if "--explain" in sys.argv:
        name = sys.argv[sys.argv.index("--explain") + 1]
        s = next(x for x in SPAIN if x.name.startswith(name))
        c = components(s)
        print(f"\n{s.name} — Spain\n")
        print(table(
            [[k, f"{c[k]:.3f}", f"{WEIGHTS[k]:.2f}", f"{c[k] * WEIGHTS[k] * 100:.1f}"] for k in WEIGHTS],
            ["Component", "Value", "Weight", "Contribution"]))
        print(f"\nScore {score(s):.1f} · segment {segment(s)} · agent density {s.agent_density:.0%}")
        return

    if "--global" in sys.argv:
        rows = sorted(GLOBAL, key=lambda s: -score(s))
        print("\n## Global ranking\n")
        print(table([[s.name, f"{score(s):.1f}", segment(s)] for s in rows],
                    ["Sport", "Score", "Segment"]))
        return

    print("\n## Stride Sport Opportunity Index — Spain\n")
    rows = []
    for r in ranking():
        rows.append([
            f"**{r['sport']}**" if r["blended"] >= 60 else r["sport"],
            f"{r['regional']:.1f}",
            f"{r['global']:.1f}",
            f"**{r['blended']:.1f}**",
            r["segment"],
            r["play"],
            "sourced" if r["sourced"] else "est",
        ])
    print(table(rows, ["Sport", "Spain", "Global", "Blended", "Segment", "Play", "Data"]))

    top = ranking()[:2]
    print(f"\nTop two: {top[0]['sport']} ({top[0]['blended']:.1f}), "
          f"{top[1]['sport']} ({top[1]['blended']:.1f})")

    niche = [r for r in ranking() if r["segment"] == "niche"]
    popular = [r for r in ranking() if r["segment"] == "popular"]
    print(f"Niche: {len(niche)} sports · Popular: {len(popular)} sports")
    print(f"Mean score — niche {sum(r['blended'] for r in niche)/len(niche):.1f}, "
          f"popular {sum(r['blended'] for r in popular)/len(popular):.1f}")

    print("\nSources:")
    for k, v in SOURCES.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
