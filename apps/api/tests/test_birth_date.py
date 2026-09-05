"""A full date of birth: exact where known, a lower bound where only the year is.

The gate had been reading `year - birth_year - 1` because a year alone cannot
say whether the birthday has passed. With a date it can, so a sixteen-year-old
born in January is no longer refused until the following calendar year.
"""

from __future__ import annotations

from datetime import date

from stride_api.admission import MIN_AGE, age_of, age_on, age_from
from stride_api.db import row

TODAY = date(2026, 9, 5)


def test_exact_age_turns_on_the_birthday():
    assert age_on("2010-09-05", TODAY) == 16, "birthday today: sixteen"
    assert age_on("2010-09-06", TODAY) == 15, "birthday tomorrow: still fifteen"
    assert age_on("2010-01-01", TODAY) == 16
    assert age_on("2010-12-31", TODAY) == 15
    assert age_on(None, TODAY) is None
    assert age_on("not-a-date", TODAY) is None


def test_the_gate_prefers_the_date_and_falls_back_to_the_year_bound():
    # date present: exact, even though the year alone would have said 15
    assert age_of({"birth_date": "2010-01-01", "birth_year": 2010}, TODAY) == 16
    assert age_from(2010, TODAY.year) == 15
    # year only: the conservative bound the old form produced
    assert age_of({"birth_year": 2010}, TODAY) == 15
    assert age_of({}, TODAY) is None


def _throwaway_athlete(db):
    """A registered athlete of our own. Submitting an application re-runs
    admission and can change a profile's listing, so the demo athletes are not
    a safe place to do it -- the first version of these tests unlisted Kaia for
    every test that ran after them."""
    from fastapi.testclient import TestClient  # noqa: PLC0415
    from stride_api.main import app  # noqa: PLC0415
    c = TestClient(app)
    me = c.post("/api/auth/register", json={
        "email": "dob@test.local", "password": "longenough1", "display_name": "Dob Tester",
        "role": "athlete", "sport": "Rowing", "country": "Ireland", "accept_terms": True}).json()
    return c, me["id"], me["athlete_profile"]["id"]


def _remove_throwaway(db, uid: int, pid: int) -> None:
    creator = row(db, "SELECT creatorlens_creator_id AS c FROM athlete_profiles WHERE id = ?", (pid,))
    db.execute("DELETE FROM athlete_applications WHERE athlete_id = ?", (pid,))
    db.execute("DELETE FROM athlete_profiles WHERE id = ?", (pid,))
    if creator and creator["c"]:
        db.execute("DELETE FROM creators WHERE id = ?", (creator["c"],))
    for t, col in (("auth_tokens", "user_id"), ("notifications", "user_id"), ("email_outbox", "to_user_id")):
        db.execute(f"DELETE FROM {t} WHERE {col} = ?", (uid,))
    db.execute("DELETE FROM events WHERE object_type = 'user' AND object_id = ?", (uid,))
    db.execute("DELETE FROM users WHERE id = ?", (uid,))
    db.commit()


def test_the_form_takes_a_date_derives_the_year_and_refuses_nonsense(db):
    c, uid, pid = _throwaway_athlete(db)
    try:
        for bad in ("2010-13-40", "yesterday", "2099-01-01", "1899-05-05"):
            r = c.post("/api/athlete/application", json={
                "competition_level": "national", "years_competing": 3, "birth_date": bad,
                "proof_kind": "none", "proof_url": ""})
            assert r.status_code == 422, f"{bad!r} accepted"

        ok = c.post("/api/athlete/application", json={
            "competition_level": "national", "years_competing": 3, "birth_date": "2004-07-19",
            "proof_kind": "none", "proof_url": ""})
        assert ok.status_code == 201, ok.text
        stored = row(db, "SELECT birth_date, birth_year FROM athlete_applications WHERE athlete_id = ?", (pid,))
        assert stored["birth_date"] == "2004-07-19"
        assert stored["birth_year"] == 2004, "the year follows the date, so every older reader still works"
    finally:
        _remove_throwaway(db, uid, pid)


def test_a_january_sixteen_year_old_is_no_longer_refused_for_the_whole_year(db):
    """The case the year-only bound got wrong in the safe direction."""
    c, uid, pid = _throwaway_athlete(db)
    born = date(TODAY.year - MIN_AGE, 1, 1).isoformat()   # sixteen since January
    try:
        r = c.post("/api/athlete/application", json={
            "competition_level": "national", "years_competing": 3, "birth_date": born,
            "proof_kind": "none", "proof_url": ""})
        assert r.status_code == 201
        assert r.json()["rule"] != "under_minimum_age", r.json()

        # the same person described only by year is still held back
        r2 = c.post("/api/athlete/application", json={
            "competition_level": "national", "years_competing": 3, "birth_year": TODAY.year - MIN_AGE,
            "proof_kind": "none", "proof_url": ""})
        assert r2.json()["rule"] == "under_minimum_age"
    finally:
        _remove_throwaway(db, uid, pid)


def test_the_seeded_applications_carry_dates():
    """On a database nothing else has touched: the session-scoped one has had
    Sofia's application replaced by earlier tests."""
    import sqlite3  # noqa: PLC0415
    from stride_api.db import init_db  # noqa: PLC0415
    from stride_api.seed import seed  # noqa: PLC0415
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    seed(conn)
    for slug in ("sofia-brandt", "elif-kaya"):
        a = row(conn, "SELECT birth_date, birth_year FROM athlete_applications WHERE athlete_id ="
                      " (SELECT id FROM athlete_profiles WHERE slug = ?)", (slug,))
        assert a["birth_date"] and a["birth_date"][:4] == str(a["birth_year"])
