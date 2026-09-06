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


def test_it_covers_an_added_parent_with_an_added_child(client, db):
    """The case a previous ordering broke, so it is pinned.

    A test that adds a conversation and a message inside it is entirely
    ordinary. Deleting the parent before the child trips
    `messages.conversation_id`, so additions come off child-first.
    """
    before_msgs = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM messages")}
    before_convs = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM conversations")}
    pair = _a_pair_with_no_thread(db)

    with preserved(db, ("messages", "conversations")):
        db.execute("INSERT INTO conversations (user_a, user_b, created_at, last_message_at)"
                   " VALUES (?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')", pair)
        db.commit()
        conv = row(db, "SELECT id FROM conversations WHERE user_a = ? AND user_b = ?", pair)["id"]
        db.execute("INSERT INTO messages (conversation_id, sender_id, body, created_at)"
                   " VALUES (?, ?, 'inside', '2026-01-01T00:00:00Z')", (conv, pair[0]))
        db.commit()

    assert {r["id"]: dict(r) for r in rows(db, "SELECT * FROM messages")} == before_msgs
    assert {r["id"]: dict(r) for r in rows(db, "SELECT * FROM conversations")} == before_convs


def test_the_documented_gap_explains_itself(client, db):
    """A changed pre-existing row pointing at an added row is the one shape the
    phase order cannot serve, because the three requirements are circular.

    Nothing in this suite does it. What matters is that if anything ever does,
    the failure names the helper rather than surfacing as a bare IntegrityError
    from inside a fixture, which would send the reader into the wrong file.
    """
    message = row(db, "SELECT * FROM messages ORDER BY id LIMIT 1")
    assert message is not None, "the seed should carry messages"
    pair = _a_pair_with_no_thread(db)

    try:
        with preserved(db, ("messages", "conversations")):
            db.execute("INSERT INTO conversations (user_a, user_b, created_at, last_message_at)"
                       " VALUES (?, ?, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')", pair)
            db.commit()
            conv = row(db, "SELECT id FROM conversations WHERE user_a = ? AND user_b = ?",
                       pair)["id"]
            # a row that existed before this scope, pointed at one that did not
            db.execute("UPDATE messages SET conversation_id = ? WHERE id = ?",
                       (conv, message["id"]))
            db.commit()
    except RuntimeError as exc:
        assert "limitation of the helper" in str(exc)
    else:
        raise AssertionError("the gap closed — update the docstring and delete this test")

    # The rollback means the scope's own writes are still there, so this test
    # cleans up after itself -- and the connection is usable enough to do it,
    # which is the property that matters most here.
    _repair_after_the_gap(db, message, pair)


def _a_pair_with_no_thread(db) -> tuple[int, int]:
    """Two demo users with no conversation between them, lowest id first.

    `conversations` requires `user_a < user_b` and is unique on the pair, so
    ids guessed from seed insertion order could collide with a seeded thread.
    """
    pair = tuple(sorted(row(db, "SELECT id FROM users WHERE email = ?", (email,))["id"]
                        for email in ("fan2@demo.stride", "fan3@demo.stride")))
    assert row(db, "SELECT id FROM conversations WHERE user_a = ? AND user_b = ?",
               pair) is None, "these two should not already have a thread"
    return pair


def _repair_after_the_gap(db, message, pair) -> None:
    """Undo by hand what the aborted restore could not.

    Order matters here for the same reason it matters in the helper: the
    message has to stop pointing at the added conversation before that
    conversation can go.
    """
    db.execute("UPDATE messages SET conversation_id = ? WHERE id = ?",
               (message["conversation_id"], message["id"]))
    db.execute("DELETE FROM conversations WHERE user_a = ? AND user_b = ?", pair)
    db.commit()


def test_it_survives_a_deleted_row_being_replaced_on_the_same_unique_key(client, db):
    """Unsubscribe, then re-subscribe — an ordinary thing for a test to do.

    `subscriptions` is unique on `(user_id, athlete_id)`, so putting the
    original row back while its replacement still holds the key is refused by
    the index. This left the table half-restored for the rest of the session,
    with the seeded subscription gone and a test-made one in its place.
    """
    athlete = row(db, "SELECT id FROM athlete_profiles WHERE slug = 'kaia-mercer'")["id"]
    fan = row(db, "SELECT id FROM users WHERE email = 'fan4@demo.stride'")["id"]
    # A second, later row so the one under test is not the highest id. SQLite
    # reuses a rowid when the deleted row held the maximum, which would make the
    # replacement land on the *same* id and turn this into an in-place change --
    # a different restore path from the one this test exists for. Postgres never
    # reuses an IDENTITY value, so without this the two backends would exercise
    # different code from the same test.
    tail = row(db, "SELECT id FROM users WHERE email = 'fan5@demo.stride'")["id"]

    with preserved(db, ("subscriptions",)):          # outer: cleans up the setup
        for who in (fan, tail):
            db.execute("INSERT INTO subscriptions (user_id, athlete_id, created_at)"
                       " VALUES (?, ?, '2026-01-01T00:00:00Z')", (who, athlete))
        db.commit()
        original = row(db, "SELECT * FROM subscriptions WHERE user_id = ? AND athlete_id = ?",
                       (fan, athlete))
        before = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM subscriptions")}

        with preserved(db, ("subscriptions",)):      # inner: the thing under test
            db.execute("DELETE FROM subscriptions WHERE id = ?", (original["id"],))
            db.execute("INSERT INTO subscriptions (user_id, athlete_id, created_at)"
                       " VALUES (?, ?, '2026-02-02T00:00:00Z')", (fan, athlete))
            db.commit()

            live = {r["id"]: dict(r) for r in rows(db, "SELECT * FROM subscriptions")}
            assert original["id"] not in live, "the original row is gone"
            assert len(live) == len(before), "a different row now holds its unique key"

        assert {r["id"]: dict(r) for r in rows(db, "SELECT * FROM subscriptions")} == before


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
