"""The campaign, measured — and the two ways that measurement can lie.

Everything here is the per-deal performance endpoint summed across a campaign,
so the tests worth having are about aggregation: what counts toward spend, what
counts toward reach, and what a missing measurement must not be turned into.
"""

from __future__ import annotations

import pytest

from stride_api.db import row, rows


#: The seeded campaign, by name. Not `campaigns[0]`: other tests in the suite
#: create campaigns through the API, so the first one in the workspace is
#: whichever empty campaign a neighbouring test happened to make -- these tests
#: passed alone and failed in the suite, which is the signature of that mistake.
SEEDED = "Spring Performance Line"


def _campaign(sponsor) -> dict:
    ws = sponsor.get("/api/sponsor/workspace").json()
    seeded = [c for c in ws["campaigns"] if c["name"] == SEEDED]
    assert seeded, f"the seed should still carry a campaign named {SEEDED!r}"
    return seeded[0]


def test_a_sponsor_reads_their_own_campaign(sponsor):
    got = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics")
    assert got.status_code == 200
    body = got.json()
    assert body["campaign"]["name"]
    assert body["athletes"], "the seeded campaign has deals on it"


def test_a_sponsor_cannot_read_somebody_elses_campaign(sponsor, db):
    """404 rather than 403 — a campaign belonging to another org should not be
    confirmed to exist by the shape of the refusal."""
    # A campaign belonging to a different *org* -- "any other id" is not enough,
    # because this sponsor owns several by the time the suite gets here and the
    # test would then be asserting a 404 on something they can legitimately read.
    mine = row(db, """
        SELECT o.id FROM sponsor_orgs o JOIN campaigns c ON c.org_id = o.id
        WHERE c.id = ?""", (_campaign(sponsor)["id"],))["id"]
    other = row(db, "SELECT id FROM campaigns WHERE org_id <> ? LIMIT 1", (mine,))
    assert other, "the seed has campaigns under more than one org"
    assert sponsor.get(f"/api/campaigns/{other['id']}/analytics").status_code == 404


def test_only_sponsors_get_here(client, athlete, fan, clubu, sponsor):
    cid = _campaign(sponsor)["id"]
    assert client.get(f"/api/campaigns/{cid}/analytics").status_code == 401
    for who in (athlete, fan, clubu):
        assert who.get(f"/api/campaigns/{cid}/analytics").status_code == 403


def test_an_unanswered_offer_costs_nothing(sponsor, db):
    """Spend is what was committed. An offer nobody has accepted is not money
    spent, and counting it would dilute every cost figure below it."""
    body = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics").json()
    live = [a for a in body["athletes"] if a["status"] in ("accepted", "completed")]
    assert body["totals"]["committed_eur"] == sum(a["amount_eur"] for a in live)
    assert body["totals"]["athletes_live"] == len(live)
    assert any(a["status"] == "offered" for a in body["athletes"]), \
        "the seed should still carry an unanswered offer for this to prove anything"


def test_nothing_attached_reads_as_unmeasured_not_as_zero(sponsor):
    """The product rule, at campaign scale: a missing measurement is null.

    Zero would say an athlete reached nobody. The truth is that they have not
    posted yet, and those are different statements about a person.
    """
    body = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics").json()
    waiting = [a for a in body["athletes"]
               if a["status"] in ("accepted", "completed") and a["posts"] == 0]
    assert waiting, "the seed keeps one accepted deal with nothing attached"
    for a in waiting:
        assert a["reach"] is None
        assert a["engagements"] is None
        assert a["cost_per_1k_reach"] is None
        assert a["variance_pct"] is None


def test_cost_per_1k_only_charges_the_spend_that_bought_measured_reach(sponsor):
    """Dividing *total* spend by *measured* reach bills the athletes who have
    delivered for the ones who have not, and the campaign reads as more
    expensive than it is every time somebody is slow to post."""
    body = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics").json()
    totals = body["totals"]
    if totals["reach"] is None or not totals["cost_per_1k_reach"]:
        pytest.skip("nothing measured in this campaign")

    measured_spend = sum(a["amount_eur"] for a in body["athletes"]
                         if a["posts"] and a["status"] in ("accepted", "completed"))
    assert measured_spend < totals["committed_eur"], \
        "this only proves anything while some committed deal is still unmeasured"
    assert totals["cost_per_1k_reach"] == pytest.approx(
        measured_spend / (totals["reach"] / 1000), rel=0.01)


def test_variance_compares_one_post_against_a_one_post_projection(sponsor):
    """`projected_reach` is the expected reach of a single post.

    Comparing it against the sum over every attached post scored an athlete on
    how many they attached rather than on how each performed: two ordinary posts
    beat the projection, one strong post missed it.
    """
    body = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics").json()
    multi = [a for a in body["athletes"]
             if a["posts"] > 1 and a["projected_reach"] and a["reach"]]
    assert multi, "the seed attaches more than one post to at least one deal"
    for a in multi:
        per_post = a["reach"] / a["posts"]
        assert a["variance_pct"] == pytest.approx(
            100 * (per_post - a["projected_reach"]) / a["projected_reach"], rel=0.01)


def test_the_country_split_is_shares_and_says_it_is_an_estimate(sponsor):
    """No platform reports per-impression geography at post level. This is the
    athlete's audience mix weighted by delivered reach, which is a derivation —
    presenting it as measured reach per country would be the easiest lie in the
    product to tell, so the payload carries its own basis."""
    body = sponsor.get(f"/api/campaigns/{_campaign(sponsor)['id']}/analytics").json()
    est = body["audience_estimate"]
    assert est["basis"], "the estimate states what it is derived from"
    if est["by_country"]:
        assert sum(est["by_country"].values()) == pytest.approx(1.0, abs=0.01)
        assert all(0 <= v <= 1 for v in est["by_country"].values())
        assert 0 <= est["on_target_share"] <= 1


def test_the_sponsor_only_sees_posts_that_were_attached(sponsor, db):
    """The permission boundary. A sponsor reads the metrics of posts an athlete
    deliberately attached to this deal — not everything else on that account."""
    campaign = _campaign(sponsor)
    body = sponsor.get(f"/api/campaigns/{campaign['id']}/analytics").json()
    reported = sum(a["posts"] for a in body["athletes"])

    attached = row(db, """
        SELECT COUNT(*) AS n FROM deal_deliverables dd
        JOIN deals d ON d.id = dd.deal_id
        WHERE d.campaign_id = ?""", (campaign["id"],))["n"]
    assert reported <= attached, "reported no more posts than were attached"

    # and the athletes on this campaign have far more posts than that in total
    total_posts = row(db, """
        SELECT COUNT(*) AS n FROM posts p
        JOIN platform_accounts pa ON pa.id = p.account_id
        JOIN athlete_profiles a ON a.creatorlens_creator_id = pa.creator_id
        JOIN deals d ON d.athlete_id = a.id
        WHERE d.campaign_id = ?""", (campaign["id"],))["n"]
    assert total_posts > attached, \
        "the point is that most of an athlete's posts are none of the sponsor's business"
