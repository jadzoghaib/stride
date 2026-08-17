"""Stride Sport Opportunity Index — every sport, every country in scope.

    python business-plan/sport_index.py                    # top opportunities, all countries
    python business-plan/sport_index.py --country Spain     # one country ranked
    python business-plan/sport_index.py --sport padel       # one sport across countries
    python business-plan/sport_index.py --athlete Spain padel   # athlete-facing content guidance
    python business-plan/sport_index.py --sponsor Spain padel   # what each sponsor tier sees
    python business-plan/sport_index.py --coverage          # data confidence audit

Four signals, from sport_data.py:

    supply     participants per capita     — how many athletes exist to sign
    demand     followers per capita        — how many people might pay
    gap        1 − agent density           — how much value is still unclaimed
    appetite   participation / (participation + fandom)

`appetite` does the real work. It asks whether the fans of a sport also DO the
sport. A trail runner's audience is other trail runners, who want training
knowledge and will pay for it. A football fan watches and does not want a
training plan. Participatory sports already have the content habit — athletes
publish training logs for free on platforms that pay them nothing — so the
paywall is the only missing piece.

There is no launch sport. The index is CONTEXT, not a gate: it tells an athlete
what content will convert for their audience, tells a sponsor how to read a
score, and normalises `audience_scale` so a 25k-follower trail runner is not
scored as though they were a 25k-follower footballer.
"""

from __future__ import annotations

import math
import sys

from sport_data import (COUNTRIES, SOURCES, SPORTS, confidence_summary,
                        country_row, multiplier, region_of)

WEIGHTS = {"supply": 0.25, "demand": 0.20, "gap": 0.25, "appetite": 0.15, "concentration": 0.15}
POPULAR_THRESHOLD = 0.45   # agent density above which an incumbent exists

# Supply and demand span orders of magnitude, so they are log-normalised against
# the actual range of the whole matrix rather than against a hand-set ceiling.
# A fixed cap made running saturate in every country and buried everything else.
_RANGE: dict[str, tuple[float, float]] = {}

# appetite bands — these drive the athlete-facing content guidance
PRACTITIONER = 0.55
MIXED = 0.30


def _sport(name: str):
    for s in SPORTS:
        if s[0] == name:
            return s
    raise KeyError(name)


def _calibrate() -> None:
    """Learn the matrix's own min/max once, so normalisation is self-calibrating
    rather than hand-tuned — change the data and the scale follows."""
    if _RANGE:
        return
    parts, fans = [], []
    for country, region, activity, media, _ in COUNTRIES:
        for sport, base_part, base_fan, _a in SPORTS:
            m = multiplier(region, sport)
            parts.append(activity * base_part * m)
            fans.append(media * base_fan * m)
    _RANGE["participation"] = (min(parts), max(parts))
    _RANGE["fandom"] = (min(fans), max(fans))


def _lognorm(value: float, lo: float, hi: float) -> float:
    if value <= 0 or hi <= lo:
        return 0.0
    v, a, b = math.log10(value), math.log10(max(lo, 1e-6)), math.log10(hi)
    return max(0.0, min(1.0, (v - a) / (b - a)))


def signals(country: str, sport: str) -> dict:
    _calibrate()
    name, region, activity, media, conf = country_row(country)
    _, base_part, base_fan, agent = _sport(sport)
    m = multiplier(region, sport)

    participation = activity * base_part * m
    fandom = media * base_fan * m
    total = participation + fandom

    return {
        "country": country, "region": region, "sport": sport,
        "participation": participation, "fandom": fandom,
        "agent_density": agent,
        "supply": _lognorm(participation, *_RANGE["participation"]),
        "demand": _lognorm(fandom, *_RANGE["fandom"]),
        "gap": 1.0 - agent,
        "appetite": participation / total if total else 0.0,
        # How much stronger this sport is here than in the world at large. This
        # is what makes padel/Spain a different proposition from padel/Poland,
        # and it is the signal a global average would erase.
        "concentration": min(1.0, math.log10(max(m, 0.1)) / math.log10(7.0) * 0.5 + 0.5),
        "multiplier": m,
        "country_confidence": conf,
    }


def score(country: str, sport: str) -> float:
    s = signals(country, sport)
    return 100 * sum(WEIGHTS[k] * s[k] for k in WEIGHTS)


def segment(sport: str) -> str:
    return "popular" if _sport(sport)[3] >= POPULAR_THRESHOLD else "niche"


def audience_type(appetite: float) -> str:
    if appetite >= PRACTITIONER:
        return "practitioner"
    if appetite >= MIXED:
        return "mixed"
    return "spectator"


# ── Athlete-facing: what content converts for this audience ──────────────────

GUIDANCE = {
    "practitioner": {
        "headline": "Your followers do your sport.",
        "why": "They follow you to get better at the thing you both do, so they will "
               "pay for knowledge rather than for access.",
        "publish": ["Session and training breakdowns", "Technique explainers",
                    "Gear and setup reviews", "Race/competition data and pacing",
                    "Q&A on programming and recovery"],
        "monetise": "Subscription-led. Anchor the €9.99 tier; a season pass sells well "
                    "because training is seasonal.",
        "avoid": "Pure lifestyle content — it competes with everyone and converts worst here.",
    },
    "mixed": {
        "headline": "Your followers are split between doing and watching.",
        "why": "Two audiences with different reasons to pay, so the tier ladder should "
               "separate them rather than average them.",
        "publish": ["Training content for the practitioners",
                    "Competition narrative and results for the watchers",
                    "Behind-the-scenes around events", "Occasional deep technical pieces"],
        "monetise": "Subscription for the base, one-off unlocks around competition moments.",
        "avoid": "One undifferentiated feed — it under-serves both halves.",
    },
    "spectator": {
        "headline": "Your followers watch your sport; they do not play it.",
        "why": "They pay for proximity and personality, not for instruction.",
        "publish": ["Matchday and travel access", "Personality and off-season life",
                    "Reactions and commentary", "Club and teammate content"],
        "monetise": "Access-led. Tips and one-off unlocks around fixtures outperform "
                    "subscriptions; sponsorship is usually the larger engine.",
        "avoid": "Training plans — this audience does not want them, and low conversion "
                 "on them will read as low demand when it is a content mismatch.",
    },
}


# ── Sponsor-facing: tiered visibility ────────────────────────────────────────
# Lower tiers see the normalised (sport-relative) figure only; the top tier also
# sees the raw absolute. Normalisation must never hide its basis — the product's
# whole claim is that a score decomposes.

TIER_VISIBILITY = {
    "Scout Free": {"normalised": True, "raw": False, "components": False},
    "Scout Pro": {"normalised": True, "raw": True, "components": False},
    "Scout Agency": {"normalised": True, "raw": True, "components": True},
}


def table(head: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(r) for r in rows]
    return "\n".join(r if r.endswith("|") else r + " |" for r in out)


def all_pairs() -> list[dict]:
    out = []
    for country, *_ in COUNTRIES:
        for sport, *_ in SPORTS:
            s = signals(country, sport)
            out.append({**s, "score": score(country, sport), "segment": segment(sport)})
    return out


def main() -> None:
    argv = sys.argv[1:]

    if "--coverage" in argv:
        print("\n## Data confidence\n")
        print(table(["Confidence", "Countries"],
                    [[k, str(v)] for k, v in sorted(confidence_summary().items())]))
        print(f"\n{len(COUNTRIES)} countries x {len(SPORTS)} sports = "
              f"{len(COUNTRIES) * len(SPORTS)} pairs, from "
              f"{len(COUNTRIES)} country rows + {len(SPORTS)} sport rows + regional multipliers.")
        print("\nSources:")
        for k, v in SOURCES.items():
            print(f"  {k}: {v}")
        return

    if "--athlete" in argv:
        country, sport = argv[argv.index("--athlete") + 1], argv[argv.index("--athlete") + 2]
        s = signals(country, sport)
        kind = audience_type(s["appetite"])
        g = GUIDANCE[kind]
        print(f"\n## {sport} in {country} — audience profile\n")
        print(f"**{g['headline']}** ({kind}, appetite {s['appetite']:.2f})\n")
        print(g["why"] + "\n")
        print("**Publish**")
        for item in g["publish"]:
            print(f"  - {item}")
        print(f"\n**Monetise**  {g['monetise']}")
        print(f"**Avoid**     {g['avoid']}")
        return

    if "--sponsor" in argv:
        country, sport = argv[argv.index("--sponsor") + 1], argv[argv.index("--sponsor") + 2]
        s = signals(country, sport)
        print(f"\n## {sport} in {country} — what each sponsor tier sees\n")
        rows = []
        for tier, v in TIER_VISIBILITY.items():
            shown = ["sport-relative percentile"]
            if v["raw"]:
                shown.append("raw follower scale")
            if v["components"]:
                shown.append("index components + API")
            rows.append([tier, "yes" if v["normalised"] else "-",
                         "yes" if v["raw"] else "-", "yes" if v["components"] else "-",
                         ", ".join(shown)])
        print(table(["Tier", "Normalised", "Raw", "Components", "Sees"], rows))
        print(f"\nContext for this pair: appetite {s['appetite']:.2f} "
              f"({audience_type(s['appetite'])}), agent density {s['agent_density']:.0%}, "
              f"segment {segment(sport)}.")
        return

    if "--country" in argv:
        country = argv[argv.index("--country") + 1]
        rows = sorted(((sport, score(country, sport)) for sport, *_ in SPORTS),
                      key=lambda r: -r[1])
        print(f"\n## {country} — sports ranked\n")
        print(table(["Sport", "Score", "Segment", "Audience"],
                    [[s, f"{v:.1f}", segment(s), audience_type(signals(country, s)['appetite'])]
                     for s, v in rows]))
        return

    if "--sport" in argv:
        sport = argv[argv.index("--sport") + 1]
        rows = sorted(((c, score(c, sport)) for c, *_ in COUNTRIES), key=lambda r: -r[1])
        print(f"\n## {sport} — countries ranked\n")
        print(table(["Country", "Score", "Confidence"],
                    [[c, f"{v:.1f}", country_row(c)[4]] for c, v in rows[:15]]))
        return

    pairs = sorted(all_pairs(), key=lambda p: -p["score"])
    print("\n## Top 25 country x sport opportunities\n")
    print(table(["#", "Sport", "Country", "Score", "Segment", "Audience"],
                [[str(i + 1), p["sport"], p["country"], f"{p['score']:.1f}",
                  p["segment"], audience_type(p["appetite"])]
                 for i, p in enumerate(pairs[:25])]))

    niche = [p for p in pairs if p["segment"] == "niche"]
    top50 = pairs[:50]
    print(f"\n{len(pairs)} pairs scored. Niche is {len(niche)/len(pairs):.0%} of all pairs "
          f"and {len([p for p in top50 if p['segment']=='niche'])/len(top50):.0%} of the top 50.")
    by_type: dict[str, int] = {}
    for p in top50:
        k = audience_type(p["appetite"])
        by_type[k] = by_type.get(k, 0) + 1
    print("Audience type in the top 50: " + ", ".join(f"{k} {v}" for k, v in by_type.items()))


if __name__ == "__main__":
    main()
