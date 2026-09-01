"""Simulated dataset for the first iteration — by design, no real athlete data.

Every athlete gets a CreatorLens identity: platform accounts are "connected"
through the same mock connectors the analytics engine ships with, synced through
the real ingestion pipeline, and scored with the real formula set. Replacing
this module with real onboarding + live connectors is the production path;
nothing downstream changes.

Demo accounts (password for all: stride123)
  athlete@demo.stride  — claims the Kaia Mercer profile (3 platforms connected)
  athlete2@demo.stride — Sofia Brandt, still in the review queue: the applicant a
                         reviewer can decide on and actually write to
  club@demo.stride     — Meridian FC (roster + packages incl. player-direct),
                         verified, like every club in the directory
  club2@demo.stride    — Ironline Combat Club, also verified
  club3@demo.stride    — Northgate Athletic, the applicant: still a draft, so it
                         is not in the directory and is what the admin queue has
                         to decide on
  sponsor@demo.stride  — Northwind Apparel, 2 active campaigns
  fan@demo.stride      — follows a handful of athletes
  admin@demo.stride    — chaos controls + audit access
"""

from __future__ import annotations

import json
import sqlite3

from creatorlens.actions import connect_platform, create_creator, create_target
from creatorlens.analytics.kpis import creator_kpis
from creatorlens.analytics.scoring import InsufficientData, store_scores
from creatorlens.events import log_event
from creatorlens.ingestion import sync_account

# The seeded queue is scored by the real policy rather than typed in: a
# hand-written verdict disagrees with the scorer the first time a threshold moves.
from .admission import (POLICY_VERSION, admission_decision, age_from,
                        athlete_credibility, club_legitimacy)
from .auth import hash_password
# The offer endpoint's own projection, so a seeded deal is priced against the
# same number a real one would be.
from .routers.sponsors import _projected_reach
from .db import now_iso, row, rows

DEMO_PASSWORD = "stride123"

# Money is EUR throughout. These figures were relabelled from the earlier USD
# columns rather than converted: they are illustrative fixtures picked to be
# readable, not amounts anyone quoted, so running them through an exchange rate
# would have produced false precision. Real amounts arrive with real deals.
#
# slug, name, sport, country, region, topics, deal_types, rate, platforms
ATHLETES = [
    ("kaia-mercer", "Kaia Mercer", "Athletics", "United States", "North America",
     ["running", "training", "mindset"], ["social_post", "content_creation", "brand_ambassador"], 8500,
     ["instagram", "youtube", "tiktok"]),
    ("luca-ferreira", "Luca Ferreira", "Football", "Brazil", "South America",
     ["football", "lifestyle", "training"], ["social_post", "event_appearance"], 15000,
     ["instagram", "tiktok"]),
    ("noa-lindqvist", "Noa Lindqvist", "Cycling", "Germany", "Europe",
     ["cycling", "endurance", "analytics"], ["brand_ambassador", "content_creation"], 6200,
     ["youtube", "instagram"]),
    ("amara-diallo", "Amara Diallo", "Basketball", "France", "Europe",
     ["basketball", "lifestyle", "career"], ["social_post", "brand_ambassador", "event_appearance"], 12000,
     ["instagram", "tiktok"]),
    ("teo-vasquez", "Teo Vasquez", "Boxing", "Mexico", "North America",
     ["training", "mindset", "fitness"], ["social_post", "content_creation"], 4800,
     ["instagram"]),
    ("isla-teague", "Isla Teague", "Swimming", "Australia", "Asia-Pacific",
     ["endurance", "wellness", "training"], ["social_post", "brand_ambassador"], 5400,
     ["instagram", "youtube"]),
    ("dmitri-holt", "Dmitri Holt", "Tennis", "United Kingdom", "Europe",
     ["tennis", "lifestyle", "travel"], ["event_appearance", "brand_ambassador"], 18000,
     ["instagram", "youtube"]),
    ("mira-castellanos", "Mira Castellanos", "Gymnastics", "Spain", "Europe",
     ["fitness", "training", "wellness"], ["social_post", "content_creation"], 3900,
     ["instagram", "tiktok"]),
    ("jonas-berg", "Jonas Berg", "Triathlon", "Germany", "Europe",
     ["endurance", "analytics", "recovery"], ["content_creation", "brand_ambassador"], 4100,
     ["youtube"]),
    ("priya-raman", "Priya Raman", "Climbing", "India", "Asia-Pacific",
     ["climbing", "outdoors", "mindset"], ["social_post", "content_creation"], 2800,
     ["instagram", "youtube"]),
    ("cole-navarro", "Cole Navarro", "Surfing", "United States", "North America",
     ["surfing", "outdoors", "travel"], ["social_post", "product_collab"], 7600,
     ["instagram", "tiktok"]),
    ("elif-kaya", "Elif Kaya", "Volleyball", "France", "Europe",
     ["fitness", "lifestyle", "career"], ["social_post", "event_appearance"], 3200,
     ["instagram"]),
    ("marcus-oyelaran", "Marcus Oyelaran", "Football", "United Kingdom", "Europe",
     ["football", "training", "lifestyle"], ["social_post", "brand_ambassador", "event_appearance"], 22000,
     ["instagram", "youtube", "tiktok"]),
    ("sofia-brandt", "Sofia Brandt", "Athletics", "Canada", "North America",
     ["running", "wellness", "recovery"], ["content_creation", "social_post"], 4600,
     ["instagram", "youtube"]),
    ("rafael-mota", "Rafael Mota", "Skateboarding", "Brazil", "South America",
     ["lifestyle", "outdoors", "travel"], ["social_post", "product_collab", "content_creation"], 5100,
     ["tiktok", "instagram"]),
    ("hana-yoshida", "Hana Yoshida", "Tennis", "Canada", "North America",
     ["tennis", "training", "analytics"], ["brand_ambassador", "content_creation"], 9800,
     ["youtube", "instagram"]),
    ("owen-mcallister", "Owen McAllister", "Golf", "United States", "North America",
     ["career", "travel", "lifestyle"], ["event_appearance", "brand_ambassador"], 16500,
     ["youtube"]),
    ("zara-okafor", "Zara Okafor", "Basketball", "United Kingdom", "Europe",
     ["basketball", "fitness", "career"], ["social_post", "content_creation"], 7200,
     ["instagram", "tiktok"]),
    ("mateo-guzman", "Mateo Guzman", "MMA", "Mexico", "North America",
     ["training", "fitness", "mindset"], ["social_post", "event_appearance", "product_collab"], 8900,
     ["instagram", "youtube", "tiktok"]),
    ("freya-dahl", "Freya Dahl", "Cycling", "Germany", "Europe",
     ["cycling", "endurance", "outdoors"], ["content_creation", "social_post"], 3500,
     ["instagram", "youtube"]),
    ("andre-toussaint", "Andre Toussaint", "Athletics", "France", "Europe",
     ["running", "fitness", "career"], ["social_post", "brand_ambassador"], 6800,
     ["instagram"]),
    ("lena-virtanen", "Lena Virtanen", "Swimming", "Spain", "Europe",
     ["endurance", "wellness", "mindset"], ["social_post", "content_creation"], 2900,
     []),  # no platforms connected — exercises the "commercial signals only" path
    ("darius-cole", "Darius Cole", "Boxing", "United States", "North America",
     ["training", "mindset", "lifestyle"], ["social_post", "event_appearance"], 11000,
     ["tiktok", "instagram"]),
    ("nina-petrova", "Nina Petrova", "Gymnastics", "Australia", "Asia-Pacific",
     ["fitness", "wellness", "recovery"], ["content_creation", "social_post"], 3300,
     []),  # unclaimed and unconnected — pure directory listing
]

BIOS = {
    "kaia-mercer": ("400m specialist turned content-forward athlete; national finalist with a"
                    " training-diary audience that grew through consistency, not virality.",
                    ["National championship finalist, 400m", "Sub-51 season best",
                     "Runs a weekly training-diary series"]),
}

SPONSORS = [
    ("sponsor@demo.stride", "Maya Chen-Ortega", "Northwind Apparel", "Sportswear",
     ["North America", "Europe"], "northwindapparel.example"),
    ("sponsor2@demo.stride", "Daniel Reyes", "Velo Labs", "Technology",
     ["Europe", "North America", "Asia-Pacific"], "velolabs.example"),
    ("sponsor3@demo.stride", "Ines Fontaine", "Solstice Hydration", "Beverages",
     ["North America", "South America"], "solsticehydration.example"),
]

# name, org index, category, objective, deal_types, budget, ages, genders, countries, topics
CAMPAIGNS = [
    ("Spring Performance Line", 0, "Sportswear",
     "Launch the spring performance apparel line with athlete-led training content.",
     ["social_post", "content_creation"], (5000, 25000),
     ["18-24", "25-34"], [], ["US", "GB", "DE", "FR", "CA"],
     ["running", "training", "fitness"]),
    ("Ride Telemetry Launch", 1, "Technology",
     "Introduce the Velo Labs ride-telemetry platform through credible endurance voices.",
     ["brand_ambassador", "content_creation"], (10000, 50000),
     ["18-24", "25-34", "35-44"], [], ["US", "GB", "DE", "IN"],
     ["cycling", "endurance", "analytics"]),
    ("Summer Endurance Series", 2, "Beverages",
     "Own the summer endurance conversation across the Americas.",
     ["social_post", "event_appearance"], (2000, 10000),
     ["18-24", "25-34"], [], ["US", "BR", "MX", "AU"],
     ["endurance", "fitness", "wellness"]),
]


def _insert_user(conn, email, name, role, password=DEMO_PASSWORD) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, role, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, hash_password(password), role, name, now_iso()))
    log_event(conn, "system", "user.registered", "user", cur.lastrowid, {"email": email, "role": role})
    return cur.lastrowid


def seed(conn: sqlite3.Connection) -> dict:
    summary = {"athletes": 0, "users": 0, "orgs": 0, "campaigns": 0, "deals": 0, "synced_accounts": 0}

    admin_id = _insert_user(conn, "admin@demo.stride", "Platform Admin", "admin")
    summary["users"] += 1

    # ---- athletes + CreatorLens identities ---------------------------------
    athlete_ids: dict[str, int] = {}
    athlete_sports: dict[str, str] = {}
    for slug, name, sport, country, region, topics, deal_types, rate, platforms in ATHLETES:
        creator = create_creator(conn, handle=slug, display_name=name,
                                 primary_topic=topics[0], actor="system")
        bio, highlights = BIOS.get(slug, (
            f"{sport} athlete from {country} building a durable audience around "
            f"{topics[0]} and {topics[1]} content.",
            [f"Ranked nationally in {sport}", "Multi-season sponsorship track record"]))
        cur = conn.execute(
            "INSERT INTO athlete_profiles (slug, display_name, sport, country, region, bio,"
            " career_highlights, topics, deal_types, base_rate_eur, status, creatorlens_creator_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'listed', ?, ?)",
            (slug, name, sport, country, region, bio, json.dumps(highlights),
             json.dumps(topics), json.dumps(deal_types), rate, creator["id"], now_iso()))
        athlete_ids[slug] = cur.lastrowid
        athlete_sports[slug] = sport      # competition level is read per sport
        summary["athletes"] += 1
        for platform in platforms:
            account = connect_platform(conn, creator["id"], platform, actor="system")
            sync_account(conn, account["id"], trigger="seed")
            summary["synced_accounts"] += 1

    # ---- sponsors, campaigns (each campaign gets a CreatorLens target) -----
    org_ids = []
    for email, contact, org_name, industry, regions, site in SPONSORS:
        uid = _insert_user(conn, email, contact, "sponsor")
        cur = conn.execute(
            "INSERT INTO sponsor_orgs (user_id, name, industry, regions, website, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (uid, org_name, industry, json.dumps(regions), site, now_iso()))
        org_ids.append(cur.lastrowid)
        summary["users"] += 1
        summary["orgs"] += 1

    campaign_ids = []
    first_target_id = None
    for name, org_idx, category, objective, dts, (lo, hi), ages, genders, countries, topics in CAMPAIGNS:
        target = create_target(conn, f"{name} target", ages, genders, countries, topics, actor="system")
        first_target_id = first_target_id or target["id"]
        cur = conn.execute(
            "INSERT INTO campaigns (org_id, name, objective, category, deal_types, budget_eur_min,"
            " budget_eur_max, target_age_buckets, target_genders, target_countries, target_topics,"
            " sponsor_target_id, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
            (org_ids[org_idx], name, objective, category, json.dumps(dts), lo, hi,
             json.dumps(ages), json.dumps(genders), json.dumps(countries), json.dumps(topics),
             target["id"], now_iso()))
        campaign_ids.append(cur.lastrowid)
        log_event(conn, "system", "campaign.created", "campaign", cur.lastrowid,
                  {"name": name, "org_id": org_ids[org_idx]})
        summary["campaigns"] += 1

    # baseline marketability snapshots (dashboards render immediately)
    for slug, aid in athlete_ids.items():
        creator_id = row(conn, "SELECT creatorlens_creator_id AS c FROM athlete_profiles WHERE id = ?",
                         (aid,))["c"]
        try:
            store_scores(conn, creator_id, target_id=first_target_id, actor="system")
        except InsufficientData:
            pass

    # ---- demo athlete claims a seeded profile ------------------------------
    athlete_uid = _insert_user(conn, "athlete@demo.stride", "Kaia Mercer", "athlete")
    conn.execute("UPDATE athlete_profiles SET user_id = ? WHERE slug = 'kaia-mercer'", (athlete_uid,))
    summary["users"] += 1
    # A second claimed athlete, and deliberately one still waiting on the review
    # queue. Both seeded applicants were unclaimed profiles, so deciding either
    # of them wrote no email and had nobody to notify -- correct behaviour, and
    # it made the whole review-and-tell-them path invisible in the demo. This is
    # the applicant a reviewer can actually answer.
    applicant_uid = _insert_user(conn, "athlete2@demo.stride", "Sofia Brandt", "athlete")
    conn.execute("UPDATE athlete_profiles SET user_id = ? WHERE slug = 'sofia-brandt'",
                 (applicant_uid,))
    summary["users"] += 1

    # ---- deals in every lifecycle state ------------------------------------
    kaia = athlete_ids["kaia-mercer"]
    deals = [
        (campaign_ids[0], org_ids[0], kaia, "social_post", 7500,
         "Three-post spring line story arc across April.", "offered", None),
        (campaign_ids[2], org_ids[2], kaia, "social_post", 4000,
         "Two summer series posts, US audience focus.", "offered", None),
        (campaign_ids[0], org_ids[0], athlete_ids["sofia-brandt"], "content_creation", 5000,
         "Long-form training video featuring the new line.", "accepted", now_iso()),
        (campaign_ids[1], org_ids[1], athlete_ids["noa-lindqvist"], "brand_ambassador", 14000,
         "Season-long telemetry ambassadorship.", "accepted", now_iso()),
        (campaign_ids[1], org_ids[1], athlete_ids["dmitri-holt"], "brand_ambassador", 12000,
         "Ambassador slot, tennis crossover.", "declined", now_iso()),
        (campaign_ids[2], org_ids[2], athlete_ids["luca-ferreira"], "event_appearance", 6000,
         "Rio launch event appearance.", "completed", now_iso()),
        # Two more on the demo sponsor's own campaign, so the campaign analytics
        # it opens on has something measured in it. Campaign 1 now carries one
        # deal in each state -- offered, accepted-and-waiting, accepted-and-
        # delivered, completed -- which is what the table is for.
        (campaign_ids[0], org_ids[0], athlete_ids["marcus-oyelaran"], "social_post", 3200,
         "Two-post spring line feature, training-diary framing.", "accepted", now_iso()),
        (campaign_ids[0], org_ids[0], athlete_ids["priya-raman"], "content_creation", 4500,
         "Studio session film for the spring line.", "completed", now_iso()),
    ]
    # Deliverables to attach once the deals exist, keyed by athlete slug: how
    # many of that athlete's real synced posts to hand to the sponsor as proof of
    # delivery. Sofia is deliberately absent -- an accepted deal with nothing
    # attached yet is a state the pipeline has to show, and seeding every deal
    # complete would hide it.
    delivered = {"luca-ferreira": 2, "noa-lindqvist": 1,
                 "marcus-oyelaran": 2, "priya-raman": 1}

    deal_ids: dict[int, str] = {}
    for cid, oid, aid, dt, amount, msg, status, responded in deals:
        # Captured at offer time, by the same function the offer endpoint uses.
        # Writing a plausible number here instead would make every variance in
        # the demo a fiction about a projection nothing ever made.
        creator = row(conn, "SELECT creatorlens_creator_id FROM athlete_profiles WHERE id = ?",
                      (aid,))
        projected = _projected_reach(conn, creator["creatorlens_creator_id"] if creator else None)
        completed = now_iso() if status == "completed" else None
        cur = conn.execute(
            "INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_eur, message,"
            " status, created_at, responded_at, completed_at, projected_reach)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, oid, aid, dt, amount, msg, status, now_iso(), responded, completed, projected))
        deal_ids[cur.lastrowid] = next(
            (slug for slug, pid in athlete_ids.items() if pid == aid), "")
        log_event(conn, "system", "deal.created", "deal", cur.lastrowid,
                  {"athlete_id": aid, "campaign_id": cid, "status": status, "amount_eur": amount})
        summary["deals"] += 1

    # ---- what was actually delivered ----------------------------------------
    #
    # The measurement chain, end to end: the athlete attaches posts they really
    # published, and the sponsor reads *those posts'* metrics and nothing else on
    # the account. Without this the whole analytics surface renders as dashes,
    # which is honest about an empty database and useless as a demonstration of
    # the thing being demonstrated.
    #
    # Posts are chosen by recency from the athlete's own synced accounts, and
    # only ones that actually carry a captured metric row -- attaching a post
    # with no metrics is a real state, but it is not the one being seeded here.
    for deal_id, slug in deal_ids.items():
        want = delivered.get(slug, 0)
        if not want:
            continue
        creator = row(conn, "SELECT creatorlens_creator_id FROM athlete_profiles WHERE slug = ?",
                      (slug,))
        if not creator or not creator["creatorlens_creator_id"]:
            continue
        # From the channel the offer was priced against, not simply the most
        # recent posts. `_projected_reach` quotes the athlete's *best* channel by
        # median reach, so attaching whatever they posted last compares a TikTok
        # clip to a YouTube projection -- every athlete in the demo then read as
        # ~88% under plan, which is an artefact of the seed rather than anything
        # about their delivery. A sponsor who buys a post on one platform is
        # delivered a post on that platform.
        kpis = creator_kpis(conn, creator["creatorlens_creator_id"])
        best = max(kpis.values(), key=lambda k: k["median_reach"] or 0, default=None)
        if not best:
            continue
        for post in rows(conn, """
                SELECT p.id FROM posts p
                WHERE p.account_id = ?
                  AND EXISTS (SELECT 1 FROM post_metrics m
                              WHERE m.post_id = p.id AND m.reach IS NOT NULL)
                ORDER BY p.published_at DESC LIMIT ?""",
                (best["account_id"], want)):
            conn.execute("INSERT INTO deal_deliverables (deal_id, post_id, added_at)"
                         " VALUES (?, ?, ?)", (deal_id, post["id"], now_iso()))
            summary["deliverables"] = summary.get("deliverables", 0) + 1

    # ---- clubs: rosters + sponsorship packages (incl. player-direct) --------
    clubs_spec = [
        ("club@demo.stride", "Elena Marsh", "Meridian FC", "meridian-fc", "Football",
         "United Kingdom", "Europe",
         "South London football club with a first team and a development academy;"
         " commercial program built around measurable player audiences.",
         [("luca-ferreira", "Forward"), ("marcus-oyelaran", "Midfield")],
         [("Front-of-Shirt Partner", "club", 40000,
           "Season-long shirt placement plus home-ground branding.", None,
           ["Shirt front placement", "Stadium boards", "Content days with first team"]),
          ("Academy Player Sponsorship: Luca Ferreira", "player_direct", 12000,
           "Direct backing of Luca's season - the club routes the package,"
           " the sponsor gets the player's audience.", "luca-ferreira",
           ["Two social posts per month", "Boot + kit placement", "Meet-and-greet day"]),
          ("First-Team Player Partner: Marcus Oyelaran", "player_direct", 20000,
           "Season partnership with our highest-reach first-team player.", "marcus-oyelaran",
           ["Monthly long-form content", "Match-day appearances", "Full analytics access"])]),
        ("club2@demo.stride", "Rafael Ortiz", "Ironline Combat Club", "ironline-combat", "Boxing",
         "Mexico", "North America",
         "Mexico City combat sports gym producing ranked boxers and MMA athletes.",
         [("teo-vasquez", "Boxer"), ("mateo-guzman", "MMA"), ("darius-cole", "Boxer")],
         [("Gym Title Partner", "club", 15000,
           "Naming rights across the gym, fight-night banners, and team apparel.", None,
           ["Gym naming", "Fight-night banners", "Team apparel logo"]),
          ("Fight-Night Corner: Mateo Guzman", "player_direct", 6000,
           "Corner branding and social coverage for Mateo's next three fights.", "mateo-guzman",
           ["Corner branding", "Fight-week social series", "Walkout apparel"])]),
    ]
    first_pkg_ids: dict[str, int] = {}
    for email, contact, cname, cslug, sport, country, region, bio, members, packages in clubs_spec:
        uid = _insert_user(conn, email, contact, "club")
        cur = conn.execute(
            "INSERT INTO clubs (user_id, slug, name, sport, country, region, bio, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 'listed', ?)",
            (uid, cslug, cname, sport, country, region, bio, now_iso()))
        club_id = cur.lastrowid
        log_event(conn, "system", "club.created", "club", club_id, {"name": cname})
        summary["users"] += 1
        for slug, position in members:
            # `active` explicitly: the column now defaults to `invited`, because a
            # club adding an athlete is a request. These are established members
            # of a seeded club, not pending asks — without this the whole demo
            # roster silently became a pile of unanswered invitations.
            conn.execute("INSERT INTO club_members (club_id, athlete_id, position, status, joined_at)"
                         " VALUES (?, ?, ?, 'active', ?)",
                         (club_id, athlete_ids[slug], position, now_iso()))
        for pname, ptype, price, desc, athlete_slug, perks in packages:
            cur = conn.execute(
                "INSERT INTO club_packages (club_id, athlete_id, name, description, package_type,"
                " price_eur, perks, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (club_id, athlete_ids[athlete_slug] if athlete_slug else None,
                 pname, desc, ptype, price, json.dumps(perks), now_iso()))
            first_pkg_ids.setdefault(cslug, cur.lastrowid)
    summary["clubs"] = len(clubs_spec)

    # one live commitment so club revenue + sponsor spend render immediately:
    # Solstice Hydration backs Ironline's title partnership
    ironline_pkg = first_pkg_ids["ironline-combat"]
    pkg = row(conn, "SELECT price_eur, athlete_id FROM club_packages WHERE id = ?", (ironline_pkg,))
    cur = conn.execute(
        "INSERT INTO package_commitments (package_id, org_id, amount_eur, created_at)"
        " VALUES (?, ?, ?, ?)", (ironline_pkg, org_ids[2], pkg["price_eur"], now_iso()))
    log_event(conn, "system", "package.committed", "package_commitment", cur.lastrowid,
              {"package_id": ironline_pkg, "org_id": org_ids[2], "amount_eur": pkg["price_eur"],
               "athlete_id": pkg["athlete_id"]})

    # ---- applications waiting on a human ------------------------------------
    # Without these the admission queue is empty on a fresh install, so the
    # reviewer path — open the link, decide whether it names the applicant — is
    # unreachable until somebody submits something, and the auto-checker has
    # nothing to run against.
    #
    # Kaia is deliberately left out: she is the demo athlete account, and her
    # eligibility form should open blank so that submitting one is part of the
    # walkthrough rather than something already done for you.
    #
    # Every verdict here is computed by the real policy. Typing `review` into
    # the seed would produce a queue that disagrees with the scorer the first
    # time a threshold moves.
    applications = [
        # a strong claim with a page to open: the reviewer's main path
        ("sofia-brandt", dict(
            discipline="Marathon", club_name="Halifax Harriers", league_name="Athletics Canada",
            competition_level="national", years_competing=7, birth_year=1999,
            proof_url="https://athletics.example/ca/rankings/marathon",
            proof_kind="results", proof_status="pending")),
        # a weaker claim behind a different kind of page, so the queue is ranked
        # rather than a single row — the reviewer sees the ordering the policy
        # produces, not just one decision
        ("elif-kaya", dict(
            discipline="Outside hitter", club_name="Lyon Volley", league_name="Ligue A",
            competition_level="regional", years_competing=4, birth_year=2003,
            proof_url="https://lyonvolley.example/equipe/effectif",
            proof_kind="roster", proof_status="pending")),
    ]
    for slug, fields in applications:
        scored = athlete_credibility({**fields, "sport": athlete_sports[slug]})
        verdict = admission_decision(
            scored["credibility"], proof_status=fields["proof_status"],
            social_score=None, age=age_from(fields["birth_year"]),
            club_floor=None, scoreable=scored["scoreable"])
        conn.execute(
            "INSERT INTO athlete_applications (athlete_id, discipline, club_name, league_name,"
            " competition_level, years_competing, birth_year, proof_url, proof_kind,"
            " proof_status, credibility, decision, decision_rule, policy_version,"
            " submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (athlete_ids[slug], fields["discipline"], fields["club_name"], fields["league_name"],
             fields["competition_level"], fields["years_competing"], fields["birth_year"],
             fields["proof_url"], fields["proof_kind"], fields["proof_status"],
             scored["credibility"], verdict["decision"], verdict["rule"], POLICY_VERSION,
             now_iso(), now_iso()))
        summary["applications"] = summary.get("applications", 0) + 1

    # Verified, like every club that appears in the directory.
    #
    # This used to be seeded `pending` so the verification step had something to
    # act on, while the club itself was `listed` -- which broke the rule the rest
    # of the product is built on: **a listed club is a verified club.** Meridian
    # showed up in the public directory beside Ironline and then told its own
    # owner it was not verified yet, which is two different answers to the same
    # question depending on who was asking.
    #
    # The review demo does not need a contradiction to exist. It needs an
    # applicant, and an applicant is precisely a club that is *not* listed yet --
    # see `pending_club_spec` below, which is seeded `draft` and becomes listed
    # when a reviewer verifies it. That is the real state machine, so it is the
    # one the demo shows.
    club_fields = dict(
        legal_name="Meridian Football Club Ltd", registration_id="09823117",
        federation_name="London FA", federation_id="LFA-4471", founded_year=1968,
        competition_level="regional", teams_count=7, registered_athletes=24,
        roster_url="https://meridianfc.example/first-team", proof_kind="roster",
        proof_status="verified")
    club_scored = club_legitimacy(club_fields)
    meridian = row(conn, "SELECT id FROM clubs WHERE slug = 'meridian-fc'")
    conn.execute(
        "INSERT INTO club_applications (club_id, legal_name, registration_id, federation_name,"
        " federation_id, founded_year, competition_level, teams_count, registered_athletes,"
        " roster_url, proof_kind, proof_status, legitimacy, decision, policy_version,"
        " submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (meridian["id"], club_fields["legal_name"], club_fields["registration_id"],
         club_fields["federation_name"], club_fields["federation_id"],
         club_fields["founded_year"], club_fields["competition_level"],
         club_fields["teams_count"], club_fields["registered_athletes"],
         club_fields["roster_url"], club_fields["proof_kind"], club_fields["proof_status"],
         club_scored["legitimacy"], club_scored["decision"], POLICY_VERSION,
         now_iso(), now_iso()))

    # Ironline, verified the same way. Both signed-in club accounts can therefore
    # nominate athletes and mint invite links without first playing an admin --
    # the features exist to be looked at, and a demo that hides half of them
    # behind a role switch is demonstrating the wall rather than the product.
    ironline_fields = dict(
        legal_name="Ironline Combat Club SA de CV", registration_id="IRN-771204",
        federation_name="Federación Mexicana de Boxeo", federation_id="FMB-3320",
        founded_year=2009, competition_level="national", teams_count=3,
        registered_athletes=18, roster_url="https://ironline.example/roster",
        proof_kind="roster", proof_status="verified")
    ironline_scored = club_legitimacy(ironline_fields)
    ironline = row(conn, "SELECT id FROM clubs WHERE slug = 'ironline-combat'")
    conn.execute(
        "INSERT INTO club_applications (club_id, legal_name, registration_id, federation_name,"
        " federation_id, founded_year, competition_level, teams_count, registered_athletes,"
        " roster_url, proof_kind, proof_status, legitimacy, decision, policy_version,"
        " submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'verified',"
        " ?, ?, ?)",
        (ironline["id"], ironline_fields["legal_name"], ironline_fields["registration_id"],
         ironline_fields["federation_name"], ironline_fields["federation_id"],
         ironline_fields["founded_year"], ironline_fields["competition_level"],
         ironline_fields["teams_count"], ironline_fields["registered_athletes"],
         ironline_fields["roster_url"], ironline_fields["proof_kind"],
         ironline_fields["proof_status"], ironline_scored["legitimacy"], POLICY_VERSION,
         now_iso(), now_iso()))
    summary["applications"] = summary.get("applications", 0) + 1

    # ---- a club still waiting on a reviewer ----------------------------------
    #
    # The applicant, and the reason the two clubs above can both be verified.
    # Northgate is seeded `draft`: it does not appear in the public directory,
    # cannot nominate, and holds a `pending` application for the admin queue to
    # decide on. Verifying it is what makes it listed.
    #
    # That ordering is the whole invariant -- **listed implies verified** -- and
    # seeding an applicant this way states it rather than contradicting it. Sign
    # in as admin to find it in the review queue; sign in as either club account
    # to find everything already unlocked.
    pending_club_spec = dict(
        email="club3@demo.stride", contact="Tomas Vidal", name="Northgate Athletic",
        slug="northgate-athletic", sport="Football", country="Spain", region="Catalonia",
        bio="Girona club with a first team and youth academy; applying to Stride, roster page pending review.")
    pending_uid = _insert_user(conn, pending_club_spec["email"], pending_club_spec["contact"], "club")
    cur = conn.execute(
        "INSERT INTO clubs (user_id, slug, name, sport, country, region, bio, status, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?)",
        (pending_uid, pending_club_spec["slug"], pending_club_spec["name"],
         pending_club_spec["sport"], pending_club_spec["country"], pending_club_spec["region"],
         pending_club_spec["bio"], now_iso()))
    pending_club_id = cur.lastrowid
    log_event(conn, "system", "club.created", "club", pending_club_id,
              {"name": pending_club_spec["name"]})
    summary["users"] += 1
    summary["clubs"] = summary.get("clubs", 0) + 1

    # Deliberately a *strong* application: full registration, named federation,
    # long history, a roster page a reviewer can open. It scores 70 -- above the
    # 65 verify threshold -- and is still `review`, because the roster page has
    # not been read by a human yet. That is the rule the admission policy exists
    # to state: clearing the bar earns you a reviewer, not a verdict.
    #
    # A weak applicant would demo nothing. Anyone can accept that a club with no
    # registration number waits; the interesting claim is that a good one does.
    northgate_fields = dict(
        legal_name="Club Atlètic Northgate", registration_id="B-6641902",
        federation_name="Federació Catalana de Futbol", federation_id="FCF-8812",
        founded_year=1998, competition_level="regional", teams_count=6,
        registered_athletes=94, roster_url="https://northgate.example/plantilla",
        proof_kind="roster", proof_status="pending")
    northgate_scored = club_legitimacy(northgate_fields)
    northgate_verdict = northgate_scored["decision"]
    conn.execute(
        "INSERT INTO club_applications (club_id, legal_name, registration_id, federation_name,"
        " federation_id, founded_year, competition_level, teams_count, registered_athletes,"
        " roster_url, proof_kind, proof_status, legitimacy, decision, policy_version,"
        " submitted_at, decided_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (pending_club_id, northgate_fields["legal_name"], northgate_fields["registration_id"],
         northgate_fields["federation_name"], northgate_fields["federation_id"],
         northgate_fields["founded_year"], northgate_fields["competition_level"],
         northgate_fields["teams_count"], northgate_fields["registered_athletes"],
         northgate_fields["roster_url"], northgate_fields["proof_kind"],
         northgate_fields["proof_status"], northgate_scored["legitimacy"],
         northgate_verdict, POLICY_VERSION, now_iso(), now_iso()))
    summary["applications"] = summary.get("applications", 0) + 1

    # ---- fans ----------------------------------------------------------------
    fan_id = _insert_user(conn, "fan@demo.stride", "Jordan Ellis", "fan")
    summary["users"] += 1
    for slug in ("kaia-mercer", "marcus-oyelaran", "priya-raman", "cole-navarro"):
        conn.execute("INSERT INTO follows (user_id, athlete_id, created_at) VALUES (?, ?, ?)",
                     (fan_id, athlete_ids[slug], now_iso()))
    for i in range(2, 6):
        _insert_user(conn, f"fan{i}@demo.stride", f"Fan Account {i}", "fan")
        summary["users"] += 1

    # ---- a wall with something on it -----------------------------------------
    # A profile whose wall is empty demos the shape of the feature and none of
    # the point. Two authors, one of each kind that matters: a course with a
    # part (the shelf), a dated event (the scarce one that pins to the top), and
    # a free post (the one a stranger can actually read). Platform news fills in
    # around them on its own, from the synced accounts above.
    def _content(author: str, owner_id: int, **f) -> int:
        cur = conn.execute(
            f"INSERT INTO content_items ({author}, kind, title, body, min_tier, label,"
            " sponsor_name, part_of, position, starts_at, location, capacity, external_url,"
            " media_url, media_kind, status, published_at, created_at)"
            " VALUES (?, ?, ?, ?, ?, '', '', ?, ?, ?, ?, ?, ?, ?, ?, 'published', ?, ?)",
            (owner_id, f["kind"], f["title"], f.get("body", ""), f.get("min_tier", ""),
             f.get("part_of"), f.get("position"), f.get("starts_at"), f.get("location", ""),
             f.get("capacity"), f.get("external_url", ""), f.get("media_url", ""),
             f.get("media_kind", ""), now_iso(), now_iso()))
        return cur.lastrowid

    kaia = athlete_ids["kaia-mercer"]
    block = _content("athlete_id", kaia, kind="course", title="Twelve-week hill block",
                     body="A winter of climbing, week by week, with the sessions I actually ran.",
                     min_tier="insider")
    _content("athlete_id", kaia, kind="post", title="Week 1 — easy volume", part_of=block,
             position=1, min_tier="insider",
             body="Two sessions, both easy. The point of week one is finishing it.")
    _content("athlete_id", kaia, kind="event", title="Come train with me — Montseny",
             min_tier="inner_circle", starts_at="2027-03-14T09:00:00Z",
             location="Montseny", capacity=8,
             body="A morning on the trails, eight people, breakfast after.")
    # A picture, a poll and something held back: the three shapes a wall has to
    # be able to show before it demonstrates anything.
    _content("athlete_id", kaia, kind="post", title="Altitude camp, day nine",
             media_url="/demo/altitude-camp.svg", media_kind="image",
             body="Nine days at 2,400m. Legs finally stopped arguing on the climbs.")
    poll = _content("athlete_id", kaia, kind="poll", title="What should the winter block be?",
                    body="You pick, I suffer.")
    for position, label in enumerate(("Hills", "Track", "Trails")):
        conn.execute("INSERT INTO poll_options (content_id, position, label) VALUES (?, ?, ?)",
                     (poll, position, label))
    _content("athlete_id", kaia, kind="post", title="The session I do not put on Instagram",
             min_tier="supporter",
             media_url="/demo/session.svg", media_kind="image",
             body="The full set, the splits, and why the third rep is the one that matters.")
    _content("athlete_id", kaia, kind="post", title="Race report: what went wrong on the descent",
             min_tier="", body="I went out too hard and paid for it in the last three kilometres."
                               " Splits and what I would do differently.")
    _content("athlete_id", kaia, kind="product", title="Signed trail cap",
             external_url="https://shop.example/kaia-mercer/trail-cap",
             body="Cotton, one size, signed on the brim. Ships from the store, not from Stride.")
    _content("club_id", meridian["id"], kind="session", title="Open training — first team",
             min_tier="supporter", starts_at="2027-04-08T17:30:00Z",
             location="Meridian Ground", capacity=40,
             body="Watch a full session from the touchline, then meet the squad.")

    # A fan wall with something on it. An empty one demonstrates the tab and
    # not the reason for it: the argument is that a profile with only broadcast
    # on it is a brochure, which you cannot see on a page where nobody has
    # spoken.
    kaia_profile = athlete_ids["kaia-mercer"]
    for author, note in ((fan_id, "Watched the Montseny descent three times. Ruthless."),
                         (athlete_uid, "Ha — three times more than I want to. Report is up.")):
        conn.execute("INSERT INTO fan_posts (athlete_id, user_id, body, created_at)"
                     " VALUES (?, ?, ?, ?)", (kaia_profile, author, note, now_iso()))

    conn.commit()
    return summary


def is_seeded(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] > 0
