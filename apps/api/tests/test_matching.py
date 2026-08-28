"""Unit + property tests for the matching engines (no HTTP)."""

from __future__ import annotations

import stride_api.matching as matching
from stride_api.matching import (ANALYTICS_KEYS, COMMERCIAL_KEYS, WEIGHTS, _budget_alignment,
                                _effective_weights, fan_ranking, sponsor_matches)


def test_weights_are_a_complete_partition():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    assert all(w > 0 for w in WEIGHTS.values())
    # the two groups partition the weight set exactly — _effective_weights
    # redistributes within a group, so a key in neither would silently vanish
    assert set(ANALYTICS_KEYS) | set(COMMERCIAL_KEYS) == set(WEIGHTS)
    assert not set(ANALYTICS_KEYS) & set(COMMERCIAL_KEYS)


def test_budget_alignment_bands():
    assert _budget_alignment(5000, 1000, 10000)[0] == 1.0     # inside
    assert _budget_alignment(500, 1000, 10000)[0] == 0.85     # under budget
    assert _budget_alignment(15000, 1000, 10000)[0] == 0.4    # negotiable (< 2x)
    assert _budget_alignment(25000, 1000, 10000)[0] == 0.0    # out of reach
    # boundary: exactly max is inside; exactly 2x max is still negotiable
    assert _budget_alignment(10000, 1000, 10000)[0] == 1.0
    assert _budget_alignment(20000, 1000, 10000)[0] == 0.4


def test_sponsor_matches_bounded_sorted_and_explained(client, db):
    campaign = db.execute("SELECT * FROM campaigns ORDER BY id LIMIT 1").fetchone()
    matches = sponsor_matches(db, dict(campaign))
    assert matches
    for m in matches:
        assert 0 <= m["score"] <= 100
        assert set(m["components"]) == set(WEIGHTS) == set(m["effective_weights"])
        # the reported score is exactly the effective-weighted sum over the
        # components that were measured (no hidden terms, no zero-filled ones)
        recomputed = round(100 * sum(m["effective_weights"][k] * m["components"][k]
                                     for k in WEIGHTS if m["components"][k] is not None), 1)
        assert abs(m["score"] - recomputed) <= 0.11  # component rounding tolerance
        # a component is measured iff it carries an effective weight
        for k in WEIGHTS:
            assert (m["components"][k] is None) == (m["effective_weights"][k] is None)
    assert all(matches[i]["score"] >= matches[i + 1]["score"] for i in range(len(matches) - 1))


def test_match_ties_break_alphabetically(client, db):
    campaign = db.execute("SELECT * FROM campaigns ORDER BY id LIMIT 1").fetchone()
    matches = sponsor_matches(db, dict(campaign))
    for a, b in zip(matches, matches[1:]):
        if a["score"] == b["score"]:
            assert a["display_name"] <= b["display_name"]


# ---- missing data is excluded, never scored as zero --------------------------


def test_effective_weights_match_nominal_when_everything_is_measured():
    components = {k: 0.5 for k in WEIGHTS}
    effective = _effective_weights(components)
    assert effective == {k: WEIGHTS[k] for k in WEIGHTS}


def test_effective_weights_redistribute_inside_the_analytics_group():
    components = {k: 0.5 for k in WEIGHTS} | {"growth": None}
    effective = _effective_weights(components)

    assert effective["growth"] is None
    # growth's 0.08 is shared among the other four analytics dimensions...
    assert abs(sum(effective[k] for k in ANALYTICS_KEYS if k != "growth") - 0.78) < 1e-9
    # ...and never leaks into the commercial group
    for k in COMMERCIAL_KEYS:
        assert abs(effective[k] - WEIGHTS[k]) < 1e-9
    assert abs(sum(v for v in effective.values() if v is not None) - 1.0) < 1e-9


def test_whole_group_unmeasured_forfeits_its_weight():
    """An athlete with no analytics must not be scored purely on commercial fit —
    the analytics weight is forfeited, capping them below any measured athlete."""
    components = {k: (None if k in ANALYTICS_KEYS else 1.0) for k in WEIGHTS}
    effective = _effective_weights(components)

    assert all(effective[k] is None for k in ANALYTICS_KEYS)
    assert abs(sum(v for v in effective.values() if v is not None) - 0.22) < 1e-9
    score = 100 * sum(effective[k] * components[k] for k in COMMERCIAL_KEYS)
    assert abs(score - 22.0) < 1e-9  # perfect commercial fit, still capped at 22


def test_unmeasured_dimension_is_excluded_from_the_score(client, db, monkeypatch):
    """Regression for the zero-fill bug: a null dimension must raise the score
    relative to treating it as zero, and say so in the caveats."""
    campaign = dict(db.execute("SELECT * FROM campaigns ORDER BY id LIMIT 1").fetchone())
    # patched at `analytics_for`, which is where matching now gets its
    # dimensions from — it reads four of them back off the score snapshot and
    # only falls through to compute_scores when there is none
    real = matching.analytics_for

    def without_growth(conn, creator_id, target_id=None):
        result = real(conn, creator_id, target_id)
        if result:
            result["dimensions"] = dict(result["dimensions"]) | {"growth": None}
        return result

    baseline = {m["slug"]: m for m in sponsor_matches(db, campaign)}
    monkeypatch.setattr(matching, "analytics_for", without_growth)
    degraded = {m["slug"]: m for m in sponsor_matches(db, campaign)}

    scored = [s for s, m in baseline.items() if m["analytics_summary"]]
    assert scored, "seed should contain athletes with analytics"
    for slug in scored:
        m = degraded[slug]
        assert m["components"]["growth"] is None
        assert m["effective_weights"]["growth"] is None
        assert any("Not measured: growth" in c for c in m["caveats"])
        # zero-filling growth would have dragged the score down by 0.08 * growth;
        # excluding it instead keeps the score a mean over what was measured
        zero_filled = round(100 * sum(WEIGHTS[k] * (m["components"][k] or 0.0)
                                      for k in WEIGHTS), 1)
        assert m["score"] > zero_filled


def test_fan_ranking_ties_break_alphabetically(client, db):
    ranked = fan_ranking(db, interests=[], country=None, followed_ids=set())
    zeros = [r["display_name"] for r in ranked if r["affinity"] == 0]
    assert zeros == sorted(zeros)


def test_matching_reuses_the_snapshot_instead_of_rebuilding_from_posts(client, db, monkeypatch):
    """The point of the snapshot path, stated as a property rather than a timing.

    Scale, engagement quality, growth and consistency describe the athlete and
    not the brief, so a stored snapshot is not an approximation of them — it is
    the same number. Rebuilding them from post metrics on every matching run is
    what made ranking cost O(athletes x posts).

    `creator_kpis` is the expensive read, so making it explode proves matching
    never reaches for it when a snapshot exists. Audience fit still has to be
    live, and it is: it uses only follower weights and demographic shares.
    """
    campaign = dict(db.execute("SELECT * FROM campaigns ORDER BY id LIMIT 1").fetchone())

    from creatorlens.analytics import scoring

    rebuilt: list[int] = []
    real_kpis = scoring.creator_kpis

    def watched(conn, creator_id):
        rebuilt.append(creator_id)
        return real_kpis(conn, creator_id)

    monkeypatch.setattr(scoring, "creator_kpis", watched)
    matches = sponsor_matches(db, campaign)

    # By name, not by position: sqlite3.Row supports both, psycopg's dict_row
    # only the name, and this suite is meant to run on either backend.
    with_snapshots = {r["creator_id"] for r in db.execute(
        "SELECT DISTINCT creator_id FROM score_snapshots").fetchall()}
    assert with_snapshots, "seed should contain score snapshots"
    assert not (set(rebuilt) & with_snapshots), (
        "matching rebuilt KPIs from posts for creators that already had a snapshot: "
        f"{sorted(set(rebuilt) & with_snapshots)}")

    scored = [m for m in matches if m["analytics_summary"]]
    assert scored, "seed should contain athletes with analytics"
    for m in scored:
        assert m["components"]["audience_fit"] is not None, "fit must still be computed live"


def test_audience_fit_moves_with_the_brief_while_the_rest_hold_still(client, db):
    """The split has to preserve the thing that made matching worth having:
    audience fit is scored against THIS campaign, so two briefs must be able to
    disagree about the same athlete. The other four cannot, and must equal what
    the snapshot already stored."""
    from creatorlens.analytics.scoring import latest_score

    campaigns = [dict(r) for r in db.execute(
        "SELECT * FROM campaigns WHERE sponsor_target_id IS NOT NULL ORDER BY id").fetchall()]
    assert len(campaigns) >= 2, "need two briefs with different targets"
    a = {m["slug"]: m for m in sponsor_matches(db, campaigns[0])}
    b = {m["slug"]: m for m in sponsor_matches(db, campaigns[1])}

    shared = [s for s in a.keys() & b.keys() if a[s]["analytics_summary"]]
    assert shared
    assert any(a[s]["components"]["audience_fit"] != b[s]["components"]["audience_fit"]
               for s in shared), "audience fit should depend on the brief"

    for slug in shared:
        creator_id = db.execute(
            "SELECT creatorlens_creator_id FROM athlete_profiles WHERE slug = ?",
            (slug,)).fetchone()["creatorlens_creator_id"]
        snap = latest_score(db, creator_id)
        for dim in matching.SNAPSHOT_DIMS:
            stored = snap[dim]
            assert a[slug]["analytics_summary"]["dimensions"][dim] == stored
            assert b[slug]["analytics_summary"]["dimensions"][dim] == stored
