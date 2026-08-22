"""Provenance for every assumption in the model.

One row per assumption: how it was set, what it was measured against, the
source, how much to trust it, and what would replace it. Kept separate from
build_workbook.py so the evidence can be reviewed without reading layout code,
and so a source can be updated without touching the workbook generator.

METHOD:
    SOURCED       a published figure
    BENCHMARKED   set against named comparables
    DERIVED       computed from other assumptions
    ESTIMATE      judgement, with no benchmark behind it yet

`key` links the row to the Assumptions sheet, so the workbook shows the LIVE
value beside the evidence that justified it. Change the assumption and this tab
shows the new number against the old reasoning — which is the point.
"""

from __future__ import annotations

# (label, assumptions_key, method, benchmark, source, confidence, what_would_improve_it)
ROWS: list[tuple] = [
    ("— PRICING & TAKE RATE —",),
    ("Take rate on fan revenue", "take_fan", "BENCHMARKED",
     "Passes charges 10% but adds $0.30/txn and a $29/month creator fee; OnlyFans, Fansly and "
     "Fanfix are all 20%; Patreon 8-12%. A flat 15% with no monthly fee pays an athlete more "
     "than Passes for anyone under EUR 1,380/month of fan revenue.",
     "Sacra company profile (Passes); Passes rebrand release, Apr 2026; MEXC platform "
     "comparison 2026",
     "High", "Nothing. This is a pricing decision and the comparables are public."),
    ("Take rate on sponsorship", "take_sp", "BENCHMARKED",
     "Sports agents take 10-20% of an endorsement and 4-10% of a playing contract. On "
     "OnlyFans, management agencies take a further 20-50% on top of the platform's 20%.",
     "Oreate and Sapling agent-commission surveys; Aruna Talent agency rate guide 2026",
     "High", "Observed deal data once the marketplace is running."),
    ("Suggested tiers 4.99 / 9.99 / 24.99", "", "BENCHMARKED",
     "Patreon's typical patronage is quoted at $8-12/month, so the EUR 9.99 anchor sits inside "
     "the observed band. EUR 4.99 retains only 54% of our take after payment fees, against 71% "
     "at EUR 9.99 — which is why the floor matters more than the take rate.",
     "Patreon 2024 Transparency Report; independent audits of ~1,200 creators",
     "Medium", "Our own tier mix after P1."),
    ("Season pass / annual billing", "", "SOURCED",
     "Patreon reports that annual patrons churn at ONE THIRD the rate of monthly patrons. This "
     "is the single strongest piece of evidence in the plan for pushing annual billing.",
     "Patreon 2024 Transparency Report",
     "High", "Already strong. Confirm on our own cohorts."),

    ("— FAN ECONOMICS —",),
    ("Fan ARPU per month", "niche_arpu", "BENCHMARKED",
     "Patreon's average monthly support rose from $5.40 to $6.10 during 2024, with typical "
     "patronage quoted at $8-12. Our EUR 8.00-9.50 sits in the upper-middle of that range.",
     "Patreon 2024 Transparency Report",
     "Medium", "Actual ARPU by tier and sport after P1."),
    ("Fan churn per month", "niche_fchurn", "ESTIMATE",
     "OPTIMISTIC AGAINST BENCHMARK. Patreon runs 10-15% monthly. We assume 6-9% (niche) and "
     "9-13% (popular), arguing that training content is habitual and that competitive seasons "
     "create natural renewal moments. That argument is currently untested.",
     "Patreon 2024 Transparency Report (10-15%/month)",
     "Low", "THE most important number to measure in P1. Three months of real cohorts settles "
            "it. Until then the conservative case should be treated as the plan."),
    ("Paying fans per monetising athlete", "niche_fpa", "DERIVED",
     "20 rising to 48 over ten years. Cross-check: Patreon creators average $350/month and our "
     "modelled niche athlete at maturity earns about EUR 313/month — closely aligned, which is "
     "reassuring for an assumption built bottom-up rather than from a comparable.",
     "Patreon 2024 Transparency Report (creator average $350/month)",
     "Medium", "Observed fans per athlete, banded by follower count."),
    ("Share of athletes who monetise", "niche_monetise", "ESTIMATE",
     "28% rising to 50% for niche sports. No direct comparable exists — neither Patreon nor "
     "OnlyFans publishes activation rates for creators who sign up but never charge.",
     "None found",
     "Low", "Our own activation funnel, available from P1 onward."),
    ("Fan acquisition capacity", "", "ESTIMATE",
     "An athlete can recruit 30-69 new paying fans a year depending on segment. This ceiling "
     "is what makes churn bite in the model: without it, higher churn perversely RAISED "
     "revenue, because the year-end target was reachable at any churn rate.",
     "None — introduced to fix a modelling flaw found by stress testing",
     "Low", "Observed gross adds per athlete per year."),

    ("— PAYMENT RAILS —",),
    ("PSP percentage fee", "psp_pct", "SOURCED",
     "Stripe for a Spanish entity: 1.5% + EUR 0.25 on EEA domestic cards, 2.5% on UK cards, "
     "3.25% on non-EEA. 1.9% is the blend for a mostly-European fan base. CORRECTION: an "
     "earlier version of this model used the US headline of 2.9% and overstated the largest "
     "cost line in the business by about a third.",
     "Stripe published EU/EEA pricing, 2026",
     "High", "Interchange-plus terms become negotiable above roughly EUR 5M processed."),
    ("PSP fixed fee per transaction", "psp_fix", "SOURCED",
     "EUR 0.25 per transaction. On a EUR 4.99 tier that single fee is a third of our take, "
     "which is why the tier floor and annual billing move more margin than the take rate does.",
     "Stripe published pricing, 2026",
     "High", "Volume renegotiation; annual billing turns twelve fees into one."),
    ("Payout fees", "payout_pct", "SOURCED",
     "Stripe Connect Express: roughly 0.25% + EUR 0.25 per payout, plus a monthly "
     "active-account fee that is not modelled as a separate line.",
     "Stripe Connect pricing, 2026",
     "Medium", "Actual payout frequency once athletes are onboarded."),

    ("— MARKET SIZING —",),
    ("Sport participation by country", "", "SOURCED",
     "Eurobarometer 525, share who NEVER exercise: Finland 8%, Sweden 12%, Denmark 20%, "
     "Poland 65%, Greece 68%, Portugal 73%, EU-27 average 45%. Six of the 34 countries in the "
     "index are measured; the other 28 are estimates placed inside that distribution.",
     "Special Eurobarometer 525, Sport and Physical Activity, September 2022",
     "High", "Federation licence counts — published annually and free (CSD in Spain)."),
    ("Padel market size", "", "SOURCED",
     "Spain has ~6.0M active players (12.7% of the population), 109,040 federation licences and "
     "17,300+ courts; globally 35M+ players and 77,000+ courts. This is the clearest case for "
     "weighting a sport regionally rather than globally — padel scores 77.7 in Spain and 45.1 "
     "worldwide.",
     "FIP World Padel Report 2025",
     "High", "Annual FIP refresh."),
    ("Sports fandom by country", "", "ESTIMATE",
     "The weakest layer of the sport index, and it drives both the `demand` and `appetite` "
     "signals. Commercial audience panels (Nielsen Sports, YouGov) cost more than the entire "
     "Y1-Y2 analytics budget.",
     "None — reasoned estimates only",
     "Low", "Our own engagement data per sport per country once connectors are live. This is "
            "what makes the index self-improving rather than something anyone could copy."),
    ("Athlete count trajectory", "athletes", "ESTIMATE",
     "400 rising to 85,000 over ten years. This is the PLAN, not a benchmark: marketing spend "
     "is derived from it at segment CAC, not the other way round. Everything in the model "
     "scales off this line.",
     "None — it is a target",
     "Low", "The pre-seed gate tests it directly: 400 athletes and EUR 10k MRR."),

    ("— COSTS —",),
    ("Athlete CAC", "niche_cac", "ESTIMATE",
     "EUR 16-36 for niche, EUR 40-88 for popular. The gap reflects displacing an existing agent "
     "relationship versus reaching someone with no representation at all. No published "
     "comparable exists for athlete acquisition in this segment.",
     "None found",
     "Low", "Measured CAC by channel from the first federation partnership."),
    ("Loaded salary, Spain", "salary", "BENCHMARKED",
     "EUR 38k-76k loaded. Spanish employer social security adds roughly 31% on top of gross, so "
     "a senior engineer at ~EUR 55k gross costs ~EUR 72k — around half the London equivalent, "
     "which is a real argument for being in Spain rather than an accident of geography.",
     "Spanish Seguridad Social employer contribution rates",
     "Medium", "Actual offers accepted."),
    ("AWS infrastructure", "aws", "BENCHMARKED",
     "Built up per stage from list prices: Fargate, RDS then Aurora, ElastiCache, S3, "
     "MediaConvert, CloudWatch. Reserved capacity and Savings Plans (25-40%) are deliberately "
     "excluded and treated as upside.",
     "AWS published list pricing, 2026",
     "Medium", "Actual bills; commit to Savings Plans once usage is stable."),
    ("Media egress", "egress", "SOURCED",
     "EUR 0.008/GB behind a zero-egress object store versus EUR 0.075/GB at CloudFront list "
     "price. At Y10 volumes that single architectural choice is worth over EUR 1M a year — the "
     "largest cost decision in the plan that is settled by engineering rather than negotiation.",
     "Cloudflare R2 and Backblaze B2 pricing; AWS CloudFront list price",
     "High", "Nothing. Both are published."),
    ("Moderation cost", "mod_rate", "ESTIMATE",
     "EUR 22 per 1,000 items reviewed, on a hybrid of automated classification and human "
     "review. Vendor pricing varies widely with SLA and content type.",
     "None cited",
     "Low", "Vendor quotes once P2 scope is fixed."),

    ("— TAX, CAPITAL & VALUATION —",),
    ("Corporate tax rates", "tax_low", "SOURCED",
     "15% for the first four profitable years under the Spanish Startup Law, then the 25% "
     "standard rate. Modelled with loss carryforward against the Y1-Y4 losses.",
     "Ley de Startups (Spain); Impuesto sobre Sociedades",
     "High", "Confirm eligibility with a Spanish tax adviser before filing."),
    ("Risk-free rate", "rf", "SOURCED",
     "Spanish 10-year sovereign yield, ~3.2% in mid-2026. Used as the floor for the founder "
     "opportunity-cost calculation rather than as the discount rate.",
     "Spanish 10Y government bond yield",
     "High", "Refresh at the date of any raise."),
    ("WACC / discount rate", "wacc", "BENCHMARKED",
     "25%. The conventional range for pre-revenue to early-revenue venture is 20-35% and we sit "
     "mid-range. The sensitivity grid runs 18-30% precisely because this is arguable rather "
     "than knowable.",
     "Standard venture valuation practice",
     "Medium", "An actual term sheet prices this for you."),
    ("Exit revenue multiple", "exit_mult", "BENCHMARKED",
     "6.5x blended. Marketplace comparables trade around 4x revenue and high-growth SaaS around "
     "9x; our Y10 mix is roughly 55% marketplace take and 12% SaaS.",
     "Public marketplace and SaaS trading multiples",
     "Medium", "Comparable private transactions nearer an exit."),
    ("Terminal growth", "tg", "BENCHMARKED",
     "3%, approximating long-run nominal GDP. Ten explicit forecast years were chosen partly so "
     "this assumption carries less of the valuation than it would at Y7.",
     "Standard DCF convention",
     "Medium", "Nothing — it is a convention, and the grid shows its effect."),

    ("— COMPLIANCE —",),
    ("Payout age floor", "", "SOURCED",
     "Stripe Express and Custom Connect require 18. Standard Connect allows 13+, but a legal "
     "guardian must own the account and hold the bank account the money lands in.",
     "Stripe Connect documentation",
     "High", "Nothing — it is a hard platform rule."),
    ("Digital consent age, Spain", "", "SOURCED",
     "14 today under LOPDGDD Art. 7. A draft Organic Law on the Protection of Minors in Digital "
     "Environments would raise it to 16 and make age verification mandatory — which is why 16 "
     "is the forward-compatible floor for an account.",
     "LOPDGDD Art. 7; draft Organic Law, Council of Ministers, March 2025",
     "High", "Track the bill through Parliament."),
]

MOST_LIKELY_WRONG = [
    "1. Fan churn. We assume 6-13%/month; Patreon reports 10-15%. If Patreon is right, Y10 "
    "revenue falls from about EUR 58M to EUR 51M and the capital requirement roughly doubles.",
    "2. Athlete count. The trajectory is a target, not a forecast, and everything scales off it.",
    "3. Share of athletes who monetise. No published comparable exists at all.",
    "",
    "All three are answered by the same thing: three months of real cohort data from P1.",
]
