"""Sport & country reference data for the Stride Sport Opportunity Index.

DESIGN: the matrix is decomposed, not enumerated. Authoring
`participation[country][sport]` directly would be 40 countries x 20 sports = 800
hand-typed numbers that nobody could maintain or defend. Instead:

    participation(country, sport) = activity_index(country)
                                  x base_share(sport)
                                  x region_multiplier(region, sport)

    fandom(country, sport)        = media_index(country)
                                  x base_fandom(sport)
                                  x region_multiplier(region, sport)

That needs ~40 country rows, ~20 sport rows, and multipliers only where a region
genuinely differs from the world. It degrades gracefully: an unknown region
falls back to the global baseline rather than to a hole.

CONFIDENCE is tracked per figure, because a plan that cannot say which numbers
are measured and which are guessed is not a plan:

    "measured"  from a cited public dataset
    "derived"   computed from a measured figure
    "estimate"  reasoned, order-of-magnitude, replace when real data arrives

REFRESH CADENCE — see 08-sport-index.md:
    activity_index   Eurobarometer, every ~4 years (next expected 2026)
    licences         national federations, annual
    fandom           estimates today; replaced by Stride's own engagement data
                     once connectors are live (the index becomes self-improving)
"""

from __future__ import annotations

SOURCES = {
    "eb525": "Special Eurobarometer 525, Sport and Physical Activity (Sept 2022). "
             "Share who NEVER exercise: FI 8%, SE 12%, DK 20%, PL 65%, GR 68%, PT 73%; EU-27 average 45%.",
    "fip25": "FIP World Padel Report 2025 — Spain ~6.0M players (12.7% of population), "
             "109,040 federation licences, 17,300+ courts; 35M+ players and 77,000+ courts worldwide.",
}

# ── Countries ────────────────────────────────────────────────────────────────
# activity_index: share of adults doing sport at all (100 − "never exercise" %).
# media_index:    relative intensity of sports following, 0–100.
# EU values marked "measured" come from Eurobarometer 525 directly.

Country = tuple[str, str, float, float, str]   # name, region, activity, media, confidence

COUNTRIES: list[Country] = [
    # ---- Nordics ----
    ("Finland",        "nordics",   92.0, 55.0, "measured"),
    ("Sweden",         "nordics",   88.0, 58.0, "measured"),
    ("Denmark",        "nordics",   80.0, 58.0, "measured"),
    ("Netherlands",    "benelux",   81.0, 62.0, "estimate"),
    # ---- Western Europe ----
    ("Luxembourg",     "benelux",   72.0, 48.0, "estimate"),
    ("Belgium",        "benelux",   65.0, 60.0, "estimate"),
    ("Austria",        "dach",      72.0, 60.0, "estimate"),
    ("Germany",        "dach",      65.0, 72.0, "estimate"),
    ("Ireland",        "uk_ie",     67.0, 68.0, "estimate"),
    ("United Kingdom", "uk_ie",     65.0, 82.0, "estimate"),
    ("France",         "france",    60.0, 70.0, "estimate"),
    # ---- Iberia ----
    ("Spain",          "iberia",    56.0, 80.0, "estimate"),
    ("Portugal",       "iberia",    27.0, 72.0, "measured"),
    # ---- Italy / Greece / Balkans ----
    ("Italy",          "italy",     45.0, 78.0, "estimate"),
    ("Greece",         "balkans",   32.0, 62.0, "measured"),
    ("Croatia",        "balkans",   52.0, 62.0, "estimate"),
    ("Slovenia",       "balkans",   70.0, 55.0, "estimate"),
    ("Bulgaria",       "balkans",   40.0, 50.0, "estimate"),
    ("Romania",        "balkans",   39.0, 52.0, "estimate"),
    ("Cyprus",         "balkans",   42.0, 48.0, "estimate"),
    ("Malta",          "italy",     43.0, 45.0, "estimate"),
    # ---- Central & Eastern Europe ----
    ("Poland",         "cee",       35.0, 60.0, "measured"),
    ("Czechia",        "cee",       60.0, 58.0, "estimate"),
    ("Slovakia",       "cee",       50.0, 52.0, "estimate"),
    ("Hungary",        "cee",       47.0, 55.0, "estimate"),
    ("Estonia",        "cee",       60.0, 48.0, "estimate"),
    ("Latvia",         "cee",       52.0, 46.0, "estimate"),
    ("Lithuania",      "cee",       50.0, 50.0, "estimate"),
    # ---- North America ----
    ("United States",  "north_america", 60.0, 85.0, "estimate"),
    ("Canada",         "north_america", 62.0, 70.0, "estimate"),
    ("Mexico",         "latam",         45.0, 72.0, "estimate"),
    # ---- Rest of demo ----
    ("Brazil",         "latam",         48.0, 85.0, "estimate"),
    ("Australia",      "oceania",       70.0, 78.0, "estimate"),
    ("India",          "south_asia",    40.0, 60.0, "estimate"),
]

# ── Sports ───────────────────────────────────────────────────────────────────
# base_participation: relative share of active people who do it (global baseline)
# base_fandom:        relative share of sports followers who follow it
# agent_density:      0..1 — share of commercially active athletes with representation
#
# The gap between the two columns is the whole point. Running has huge
# participation and modest fandom; motorsport is the reverse.

Sport = tuple[str, float, float, float]   # name, base_participation, base_fandom, agent_density

SPORTS: list[Sport] = [
    ("running / trail",  0.220, 0.030, 0.10),
    ("cycling",          0.110, 0.055, 0.35),
    ("swimming",         0.095, 0.030, 0.25),
    ("football",         0.090, 0.330, 0.88),
    ("fitness / gym",    0.130, 0.010, 0.08),
    ("padel",            0.020, 0.008, 0.15),
    ("tennis",           0.035, 0.075, 0.78),
    ("basketball",       0.045, 0.120, 0.78),
    ("volleyball",       0.030, 0.030, 0.45),
    ("climbing",         0.018, 0.007, 0.12),
    ("athletics",        0.040, 0.055, 0.48),
    ("triathlon",        0.010, 0.008, 0.14),
    ("surfing",          0.012, 0.014, 0.22),
    ("golf",             0.025, 0.045, 0.72),
    ("boxing",           0.016, 0.040, 0.70),
    ("MMA",              0.012, 0.048, 0.66),
    ("gymnastics",       0.014, 0.020, 0.42),
    ("handball",         0.012, 0.022, 0.42),
    ("rowing",           0.006, 0.006, 0.18),
    ("skateboarding",    0.014, 0.012, 0.28),
    ("motorsport",       0.003, 0.075, 0.85),
]

# ── Regional multipliers ─────────────────────────────────────────────────────
# Only where a region genuinely departs from the global baseline. Anything
# unlisted is 1.0. Applied to BOTH participation and fandom unless the sport
# appears in FANDOM_ONLY / PARTICIPATION_ONLY.

REGION_MULTIPLIERS: dict[str, dict[str, float]] = {
    "iberia": {
        "padel": 7.0,        # FIP: 12.7% of Spaniards play — the outlier that proves regional weighting
        "football": 1.5, "cycling": 1.25, "handball": 1.3, "basketball": 1.2,
        "motorsport": 1.3, "golf": 0.7, "skateboarding": 0.8,
    },
    "nordics": {
        "padel": 4.0,        # Sweden is the second padel nation
        "running / trail": 1.4, "handball": 2.2, "climbing": 1.5, "rowing": 1.2,
        "football": 0.9, "motorsport": 0.8, "boxing": 0.6, "MMA": 0.7,
    },
    "dach": {
        "football": 1.3, "handball": 2.0, "climbing": 1.8, "cycling": 1.3,
        "motorsport": 1.4, "padel": 0.5, "golf": 0.9,
    },
    "france": {
        "cycling": 1.6, "handball": 1.6, "rugby-adjacent": 1.0, "football": 1.2,
        "climbing": 1.3, "padel": 1.2, "tennis": 1.2,
    },
    "italy": {
        "football": 1.6, "cycling": 1.5, "volleyball": 1.8, "motorsport": 1.5,
        "padel": 2.5, "basketball": 1.1,
    },
    "uk_ie": {
        "football": 1.6, "golf": 1.3, "boxing": 1.5, "motorsport": 1.4,
        "running / trail": 1.2, "padel": 0.8, "rowing": 1.5,
    },
    "benelux": {
        "cycling": 2.0, "football": 1.2, "hockey-adjacent": 1.0, "padel": 1.5,
        "swimming": 1.2, "climbing": 1.2,
    },
    "cee": {
        "football": 1.3, "handball": 1.4, "volleyball": 1.5, "athletics": 1.2,
        "padel": 0.3, "golf": 0.4, "surfing": 0.1,
    },
    "balkans": {
        "football": 1.5, "basketball": 1.6, "handball": 1.6, "volleyball": 1.4,
        "padel": 0.4, "golf": 0.3, "surfing": 0.3,
    },
    "north_america": {
        "basketball": 2.4, "golf": 1.8, "skateboarding": 1.5, "MMA": 1.5,
        "boxing": 1.2, "football": 0.45, "running / trail": 1.2,
        "padel": 0.35, "handball": 0.1, "cycling": 0.7,
    },
    "latam": {
        "football": 2.2, "volleyball": 1.5, "MMA": 1.4, "boxing": 1.6,
        "surfing": 1.6, "padel": 1.2, "golf": 0.5, "handball": 0.4,
        "motorsport": 1.2,
    },
    "oceania": {
        "surfing": 3.0, "swimming": 1.8, "cycling": 1.2, "running / trail": 1.3,
        "football": 0.7, "basketball": 1.1, "padel": 0.5, "handball": 0.2,
    },
    "south_asia": {
        "football": 0.5, "athletics": 0.9, "boxing": 1.1, "MMA": 0.8,
        "padel": 0.2, "surfing": 0.2, "golf": 0.6, "handball": 0.3,
        "swimming": 0.6, "climbing": 0.3,
    },
}


def region_of(country: str) -> str:
    for name, region, *_ in COUNTRIES:
        if name == country:
            return region
    raise KeyError(country)


def country_row(country: str) -> Country:
    for row in COUNTRIES:
        if row[0] == country:
            return row
    raise KeyError(country)


def multiplier(region: str, sport: str) -> float:
    return REGION_MULTIPLIERS.get(region, {}).get(sport, 1.0)


def confidence_summary() -> dict[str, int]:
    out: dict[str, int] = {}
    for *_, conf in COUNTRIES:
        out[conf] = out.get(conf, 0) + 1
    return out
