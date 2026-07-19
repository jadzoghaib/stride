"""Unit + property tests for the matching engines (no HTTP)."""

from __future__ import annotations

from stride_api.matching import WEIGHTS, _budget_alignment, fan_ranking, sponsor_matches


def test_weights_are_a_complete_partition():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    assert all(w > 0 for w in WEIGHTS.values())


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
        assert set(m["components"]) == set(WEIGHTS)
        # the reported score is exactly the weighted component sum (no hidden terms)
        recomputed = round(100 * sum(WEIGHTS[k] * m["components"][k] for k in WEIGHTS), 1)
        assert abs(m["score"] - recomputed) <= 0.11  # component rounding tolerance
    assert all(matches[i]["score"] >= matches[i + 1]["score"] for i in range(len(matches) - 1))


def test_fan_ranking_ties_break_alphabetically(client, db):
    ranked = fan_ranking(db, interests=[], country=None, followed_ids=set())
    zeros = [r["display_name"] for r in ranked if r["affinity"] == 0]
    assert zeros == sorted(zeros)
