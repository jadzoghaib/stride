"""Raw comparable-platform data. Sourced facts only — no interpretation here.

This module is the bottom of the evidence chain:

    comparables_data.py  ->  MarketModel sheet  ->  Assumptions sheet  ->  model
    (published facts)        (derives ours)         (what the model uses)

Nothing in this file is an estimate. Every figure is a published number with a
citation, so it can be checked and refreshed independently of anything we
concluded from it. Where a derived ratio disagrees with a platform's own
reported average, both are carried — the disagreement is usually definitional
(accounts vs active creators, gross vs net, memberships vs members) and hiding
it would make the model look more certain than it is.
"""

from __future__ import annotations

# ── Platform economics ───────────────────────────────────────────────────────
# (metric, value, unit, platform, period, source)
PLATFORM_FACTS: list[tuple] = [
    # OnlyFans — FY2024 (year to 30 Nov 2024). These are not press estimates:
    # the parent, Fenix International Limited (company no. 10354575), files at
    # Companies House, and the trade press reported off those filed accounts.
    # The registry is cited first because it outlives the article.
    ("Gross payments (GMV)", 7_220_000_000, "USD", "OnlyFans", "FY2024",
     "Fenix International Ltd filed accounts (Companies House 10354575)"),
    ("Net revenue", 1_410_000_000, "USD", "OnlyFans", "FY2024",
     "Fenix International Ltd filed accounts (Companies House 10354575)"),
    ("Paid to creators", 5_800_000_000, "USD", "OnlyFans", "FY2024",
     "Fenix International Ltd filed accounts — 80.3% of gross"),
    ("Creator accounts", 4_634_000, "count", "OnlyFans", "FY2024",
     "Variety — +13% YoY"),
    ("Fan accounts", 377_500_000, "count", "OnlyFans", "FY2024",
     "Variety — +24% YoY"),
    ("Reported average creator earnings", 131, "USD/month", "OnlyFans", "FY2024",
     "Sci-Tech Today / ElectroIQ — after platform fees"),
    ("Revenue concentration", 0.76, "share to top 0.1%", "OnlyFans", "2025",
     "ElectroIQ — power-law distribution"),

    # Patreon
    ("Creators with >=1 paying member", 286_287, "count", "Patreon", "Feb 2026",
     "Graphtreon"),
    ("Active creators", 300_000, "count", "Patreon", "2025",
     "Jack Conte, Patreon"),
    ("Active paying members", 10_000_000, "count", "Patreon", "2026",
     "Patreon / Backlinko"),
    ("Paid to creators annually", 2_000_000_000, "USD/year", "Patreon", "2026",
     "Patreon / Backlinko"),
    ("Average monthly support per member", 6.10, "USD/month", "Patreon", "Aug 2024",
     "Patreon 2024 Transparency Report; audit of ~1,200 creators"),
    ("Typical patronage band (low)", 8.00, "USD/month", "Patreon", "2026",
     "Creator-economy benchmarks"),
    ("Typical patronage band (high)", 12.00, "USD/month", "Patreon", "2026",
     "Creator-economy benchmarks"),
    ("Monthly churn (low)", 0.10, "share", "Patreon", "2024",
     "Patreon 2024 Transparency Report"),
    ("Monthly churn (high)", 0.15, "share", "Patreon", "2024",
     "Patreon 2024 Transparency Report"),
    ("Annual-plan churn multiplier", 0.333, "x monthly churn", "Patreon", "2024",
     "Patreon 2024 Transparency Report — annual patrons churn at 1/3 the rate"),
    ("Creators with >2,000 patrons", 0.003, "share", "Patreon", "2026",
     "Graphtreon — power-law distribution"),

    # TEKTA — Publicis Sports + 3 Arts Sports + Travis Kelce, launched Aug 2026.
    # An agency, not a platform: the network is addressable supply it can broker,
    # not a user base. Included to size the NIL comparable, not to model it.
    ("Division I athletes in network", 45_000, "count", "TEKTA", "Aug 2026",
     "Publicis Groupe press release, 19 Aug 2026"),
    ("Power Four universities", 68, "count", "TEKTA", "Aug 2026",
     "Publicis Groupe press release"),
    ("Claimed speed-to-market gain", 0.60, "share faster", "TEKTA", "Aug 2026",
     "Publicis — stated 50-70% vs a traditional agency process"),
]

# ── Take rates: what each platform actually costs a creator ──────────────────
# (platform, headline_take, per_txn_usd, monthly_fee_usd, source)
TAKE_RATES: list[tuple] = [
    # Not a claim — arithmetic on the filed accounts above:
    # 1.41bn net revenue / 7.22bn gross fan payments = 19.5%.
    ("OnlyFans", 0.20, 0.00, 0.00, "Derived: 1.41bn / 7.22bn = 19.5% (filed accounts)"),
    # Neither platform publishes its take rate. Checked 2026-09-05: Fanfix's
    # Creator Terms of Use and its FAQ state no percentage, and Fansly's terms
    # render client-side with nothing in the document. The 20% is consistent
    # across secondary reporting and is what the platforms charge in-product,
    # but it is not a published figure and should be re-checked in-app before
    # anyone leans on it.
    ("Fansly", 0.20, 0.00, 0.00, "Not published in terms; widely reported"),
    ("Fanfix", 0.20, 0.00, 0.00, "Not published in terms; widely reported"),
    # The one platform here that publishes a rate outright, and it has changed:
    # the old 8-12%-by-tier structure, with processing billed on top, is gone.
    # patreon.com/pricing now states a single 10% "of the income you earn",
    # explicitly including "payment processing, currency conversion, and payout
    # fees, and applicable taxes". So 10% is all-in, not a midpoint of a range.
    ("Patreon", 0.10, 0.00, 0.00, "Published: 10% all-in, processing included"),
    ("Passes", 0.10, 0.30, 29.00, "Sacra; Passes rebrand release Apr 2026"),
    ("Stride (proposed)", 0.15, 0.00, 0.00, "Our decision — see MarketModel"),
]

# ── Intermediaries the athlete already pays ─────────────────────────────────
INTERMEDIARY_RATES: list[tuple] = [
    # Endorsement work sits *outside* the union caps below -- the NBPA
    # regulations do not use the word "endorsement" once -- which is the
    # structural reason marketing commissions run several times the rate a
    # union permits on a playing contract. The range is widely reported and
    # not published by any governing body; treat it as an estimate.
    ("Sports agent — endorsement", 0.10, 0.20, "Unregulated; widely reported, no primary source"),
    # Capped by the governing bodies, and the caps are public documents.
    # NBPA: 2% where the player earns the CBA minimum, 4% above it.
    # FIFA FFAR art. 15: 5% at or below USD 200k annual remuneration, 3% above,
    # for representing the player.
    ("Sports agent — playing contract", 0.02, 0.05, "NBPA reg. 4.B (Sept 2025); FIFA FFAR art. 15"),
    ("OnlyFans management agency", 0.20, 0.50, "Aruna Talent rate guide 2026 — on top of the 20%"),
]

# ── Market size inputs ──────────────────────────────────────────────────────
# Population is needed to turn Eurobarometer participation rates into headcounts.
# Millions, rounded; Eurostat / national statistics offices, 2025-26.
POPULATION_M: dict[str, float] = {
    "Spain": 48.6, "Portugal": 10.6, "France": 68.4, "Italy": 58.9, "Germany": 83.5,
    "United Kingdom": 68.3, "Netherlands": 17.9, "Belgium": 11.8, "Sweden": 10.6,
    "Denmark": 6.0, "Finland": 5.6, "Ireland": 5.3, "Austria": 9.2, "Poland": 36.7,
    "Czechia": 10.9, "Greece": 10.4, "Romania": 19.0, "Hungary": 9.6, "Bulgaria": 6.4,
    "Croatia": 3.9, "Slovakia": 5.4, "Slovenia": 2.1, "Lithuania": 2.9, "Latvia": 1.9,
    "Estonia": 1.4, "Cyprus": 1.0, "Malta": 0.6, "Luxembourg": 0.7,
    "United States": 342.0, "Canada": 41.5, "Mexico": 130.9, "Brazil": 217.0,
    "Australia": 27.2, "India": 1_450.0,
}

#: Sources checked 2026-09-05. Two entries that had gone 410 -- a cryptocurrency
#: exchange's news page and a hash-slugged blog -- have been replaced rather than
#: patched, because neither was a primary source for what it was carrying.
#:
#: The agent caps now come from the bodies that set them, and the numbers moved:
#: playing-contract representation is 2-5%, not the 4-10% those pages reported.
#:
#: The platform take rates split three ways once actually chased down:
#:
#:   Patreon publishes one, and ours was stale -- it is a flat 10% including
#:   payment processing, not 8-12% by tier with fees billed on top.
#:   OnlyFans does not publish a rate, but its parent files accounts, so 20%
#:   is recoverable as arithmetic rather than taken on trust.
#:   Fansly and Fanfix publish nothing and file nothing. Those two stay at the
#:   reported 20% and stay labelled as estimates. An absent primary source is
#:   recorded as absent rather than papered over with another blog.
SOURCE_URLS = {
    "OnlyFans FY2024 filed accounts (Fenix International Ltd)":
        "https://find-and-update.company-information.service.gov.uk/company/10354575/filing-history",
    "OnlyFans FY2024 as reported": "https://variety.com/2025/digital/news/onlyfans-fiscal-2024-revenue-earnings-1236495750/",
    "Patreon published take rate": "https://www.patreon.com/pricing",
    "Patreon creators": "https://backlinko.com/patreon-users",
    "Passes economics": "https://sacra.com/c/passes/",
    "Fanfix creator terms (states no take rate)": "https://auth.fanfix.io/creator-terms-of-use",
    "Agency commissions": "https://arunatalent.com/blog/onlyfans-agency-commission-rates/",
    "NBPA agent fee cap (amended Sept 2025)": "https://imgix.cosmicjs.com/cd844850-97c7-11f0-91fa-d9e1671c2776-NBPA-REGULATIONS-GOVERNING-PLAYER-AGENTS-09-2025.pdf",
    "FIFA Football Agent Regulations art. 15": "https://digitalhub.fifa.com/m/1e7b741fa0fae779/original/FIFA-Football-Agent-Regulations.pdf",
    "CJEU upholds the FIFA fee cap (16 Jul 2026)": "https://inside.fifa.com/news/welcomes-court-of-justice-european-union-decision-football-agent-regulations",
    "Eurobarometer 525": "https://europa.eu/eurobarometer/surveys/detail/2668",
    "FIP World Padel Report 2025": "https://www.padelfip.com/2025/12/online-the-fip-world-padel-report-2025-a-comprehensive-analysis-of-a-sport-in-constant-growth/",
    "Stripe EU pricing": "https://stripe.com/es/pricing",
    "TEKTA launch": "https://www.publicisgroupe.com/en/news/press-releases/publicis-sports-and-travis-kelce-s-tekta-join-forces-to-reimagine-the-future-of-nil-marketing",
    "Stripe Connect age": "https://support.stripe.com/questions/age-requirement-to-create-a-stripe-account",
}
