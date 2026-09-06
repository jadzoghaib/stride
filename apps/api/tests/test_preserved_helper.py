"""The isolation helper, tested — because its first version was not.

`preserved()` claimed to put tables back "exactly as they were found" and only
ever deleted rows that were added. Rows a test *changed* in place, and rows a
test *deleted*, both survived into the rest of the session. The claim was in a
docstring, nothing checked it, and the messaging tests it protects are precisely
the ones whose assertions depend on the state being what they think it is.

So the helper gets its own tests. There are three ways to leave a mark on a
table and each one is asserted here separately, against a real table with real
foreign keys rather than a fixture invented for the purpose.
"""
from __future__ import annotations

from conftest import preserved
from stride_api.db import row, rows

# Every test here takes `client` as well as `db`: the `db` fixture only opens a
# connection, while the schema and the seed are created by the app's lifespan,
# which `client` is what starts. `db` alone finds an empty database.


def _notifications(db) -> dict:
    return {r["id"]: dict(r) for r in rows(db, "SELECT * FROM notifications")}


def test_it_removes_rows_that_were_added(client, db):
    before = _notifications(db)
    with preserved(db, ("notifications",)):
        db.execute("INSERT INTO notifications (user_id, kind, title, body, link, created_at)"
                   " VALUES (1, 'test', 'Added', '', '', '2026-01-01T00:00:00Z')")
        db.commit()
        assert len(_notifications(db)) == len(before) + 1
    assert _notifications(db) == before


def test_it_reverts_rows_that_were_changed_in_place(client, db):
    """The case that used to survive: an UPDATE to a row that already existed.

    `test_the_newest_message_sorts_the_inbox` collapses every conversation's
    `last_message_at` to force an ordering tie. Before this, that collapse
    outlived the test and every later inbox assertion ran against it.
    """
    target = row(db, "SELECT * FROM notifications ORDER BY id LIMIT 1")
    assert target is not None, "the seed should carry notifications"
    original_title = target["title"]

    with preserved(db, ("notifications",)):
        db.execute("UPDATE notifications SET title = ? WHERE id = ?",
                   ("Changed by a test", target["id"]))
        db.commit()
        assert row(db, "SELECT title FROM notifications WHERE id = ?",
                   (target["id"],))["title"] == "Changed by a test"

    assert row(db, "SELECT title FROM notifications WHERE id = ?",
               (target["id"],))["title"] == original_title


def test_it_puts_back_rows_that_were_deleted(client, db):
    """The other case that used to survive, and the one with teeth.

    A test that unsubscribes the seeded fan left it unsubscribed for the rest of
    the run — so a later test asserting that a subscriber may message an athlete
    was asserting it about somebody who no longer subscribed.
    """
    before = _notifications(db)
    victim = next(iter(before))

    with preserved(db, ("notifications",)):
        db.execute("DELETE FROM notifications WHERE id = ?", (victim,))
        db.commit()
        assert victim not in _notifications(db)

    after = _notifications(db)
    assert victim in after, "the deleted row came back"
    # and it came back as itself, id included -- which on Postgres needs an
    # explicit override, because `id` is GENERATED ALWAYS AS IDENTITY
    assert after[victim] == before[victim]


def test_it_restores_all_three_kinds_of_change_together(client, db):
    """The realistic case: one test that adds, edits and deletes.

    The three rows are named up front and are deliberately distinct. The first
    version of this test deleted with `ORDER BY id DESC LIMIT 1`, which selects
    the row the INSERT had just created -- so the add and the delete cancelled
    out and the assertion passed on the UPDATE path alone, exercising neither of
    the paths it claimed to cover.
    """
    with preserved(db, ("notifications",)):          # outer: cleans up the setup
        for tag in ("to edit", "to delete"):
            db.execute("INSERT INTO notifications (user_id, kind, title, body, link,"
                       " created_at) VALUES (1, 'test', ?, '', '', '2026-01-01T00:00:00Z')",
                       (tag,))
        db.commit()
        _run_the_combined_case(db)


def _run_the_combined_case(db):
    before = _notifications(db)
    seeded = list(before)
    assert len(seeded) >= 2, "the setup above guarantees these"
    edited, deleted = seeded[-2], seeded[-1]

    with preserved(db, ("notifications",)):          # inner: the thing under test
        db.execute("INSERT INTO notifications (user_id, kind, title, body, link, created_at)"
                   " VALUES (1, 'test', 'Added', '', '', '2026-01-01T00:00:00Z')")
        db.execute("UPDATE notifications SET title = 'Edited' WHERE id = ?", (edited,))
        db.execute("DELETE FROM notifications WHERE id = ?", (deleted,))
        db.commit()

        # all three states really are in play at once
        mid = _notifications(db)
        assert len(mid) == len(before)                       # one added, one gone
        assert deleted not in mid
        assert mid[edited]["title"] == "Edited"
        assert any(i not in before for i in mid)

    assert _notifications(db) == before


def test_it_survives_a_changed_row_pointing_at_an_added_one(client, db):
    """The ordering case, and the reason the phases run add-last.

    A test may point a *pre-existing* row at a row it just created. Deleting
    additions before reverting changes then tries to remove a parent the
    still-modified child references, and the foreign key stops it — so the
    restore raises instead of restoring, leaving the database worse than it
    found it. Foreign keys are enforced on both backends (`PRAGMA
    foreign_keys = ON` in db.py, and Postgres needs no asking).
    """
    message = row(db, "SELECT * FROM messages ORDER BY id LIMIT 1")
    assert message is not None, "the seed should carry messages"
    before_msgs = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM messages")}
    before_convs = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM conversations")}

    with preserved(db, ("messages", "conversations")):
        db.execute("INSERT INTO conversations (user_a, user_b, created_at, last_message_at)"
                   " VALUES (1, 2, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')")
        db.commit()
        new_conv = row(db, "SELECT id FROM conversations ORDER BY id DESC LIMIT 1")["id"]
        assert new_conv not in before_convs

        # the pre-existing message now hangs off the conversation this test made
        db.execute("UPDATE messages SET conversation_id = ? WHERE id = ?",
                   (new_conv, message["id"]))
        db.commit()

    assert {r["id"]: dict(r) for r in rows(db, "SELECT * FROM messages")} == before_msgs
    assert {r["id"]: dict(r) for r in rows(db, "SELECT * FROM conversations")} == before_convs


def test_it_restores_even_when_the_test_fails(client, db):
    """A failing assertion must not also corrupt the database for everything
    that runs after it. The restore is in a `finally` for this reason."""
    before = _notifications(db)
    try:
        with preserved(db, ("notifications",)):
            db.execute("INSERT INTO notifications (user_id, kind, title, body, link, created_at)"
                       " VALUES (1, 'test', 'Doomed', '', '', '2026-01-01T00:00:00Z')")
            db.commit()
            raise AssertionError("pretend the test failed here")
    except AssertionError as exc:
        assert "pretend" in str(exc), "the original failure must propagate, not be swallowed"

    assert _notifications(db) == before
