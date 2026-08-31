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
  club@demo.stride     — Meridian FC (roster + packages incl. player-direct)
  sponsor@demo.stride  — Northwind Apparel, 2 active campaigns
  fan@demo.stride      — follows a handful of athletes
  admin@demo.stride    — chaos controls + audit access
"""

from __future__ import annotations

import json
import sqlite3

from creatorlens.actions import connect_platform, create_creator, create_target
from creatorlens.analytics.scoring import InsufficientData, store_scores
from creatorlens.events import log_event
from creatorlens.ingestion import sync_account

# The seeded queue is scored by the real policy rather than typed in: a
# hand-written verdict disagrees with the scorer the first time a threshold moves.
from .admission import (POLICY_VERSION, admission_decision, age_from,
                        athlete_credibility, club_legitimacy)
from .auth import hash_password
from .db import now_iso, row

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
    ]
    for cid, oid, aid, dt, amount, msg, status, responded in deals:
        cur = conn.execute(
            "INSERT INTO deals (campaign_id, org_id, athlete_id, deal_type, amount_eur, message,"
            " status, created_at, responded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cid, oid, aid, dt, amount, msg, status, now_iso(), responded))
        log_event(conn, "system", "deal.created", "deal", cur.lastrowid,
                  {"athlete_id": aid, "campaign_id": cid, "status": status, "amount_eur": amount})
        summary["deals"] += 1

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

    # The club's own application, left at whatever the policy makes of it. It is
    # not pre-verified on purpose: a club cannot nominate until a human has
    # checked its roster page, and watching that unlock is the point of the
    # club onboarding demo. Seeding it verified would skip the argument.
    club_fields = dict(
        legal_name="Meridian Football Club Ltd", registration_id="09823117",
        federation_name="London FA", federation_id="LFA-4471", founded_year=1968,
        competition_level="regional", teams_count=7, registered_athletes=24,
        roster_url="https://meridianfc.example/first-team", proof_kind="roster",
        proof_status="pending")
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

    conn.commit()
    return summary


def is_seeded(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] > 0
