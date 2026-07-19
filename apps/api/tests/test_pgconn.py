"""Unit tests for the SQLite->Postgres SQL translation shim."""

from __future__ import annotations

import re

from stride_api.pgconn import _INSERT, _split_statements, _translate


def full(sql: str) -> str:
    pg, _ = _translate(sql)
    if _INSERT.match(pg) and " returning " not in pg.lower():
        pg += " RETURNING id"
    return pg


CASES = [
    ("SELECT * FROM users WHERE id = ?", "SELECT * FROM users WHERE id = %s"),
    ("SELECT * FROM a WHERE name LIKE ? OR sport LIKE ?",
     "SELECT * FROM a WHERE name LIKE %s OR sport LIKE %s"),
    ("INSERT INTO users (email, role) VALUES (?, ?)",
     "INSERT INTO users (email, role) VALUES (%s, %s) RETURNING id"),
    ("INSERT OR IGNORE INTO follows (user_id, athlete_id, created_at) VALUES (?, ?, ?)",
     "INSERT INTO follows (user_id, athlete_id, created_at) VALUES (%s, %s, %s)"
     " ON CONFLICT DO NOTHING RETURNING id"),
    ("INSERT INTO account_snapshots (a, b) VALUES (?, ?)"
     " ON CONFLICT(account_id, snapshot_date) DO UPDATE SET followers = excluded.followers",
     "INSERT INTO account_snapshots (a, b) VALUES (%s, %s)"
     " ON CONFLICT(account_id, snapshot_date) DO UPDATE SET followers = excluded.followers"
     " RETURNING id"),
    ("UPDATE users SET token_version = token_version + 1 WHERE id = ?",
     "UPDATE users SET token_version = token_version + 1 WHERE id = %s"),
    ("SELECT COUNT(*) AS n FROM users", "SELECT COUNT(*) AS n FROM users"),
]


def test_translation_cases():
    for sql, expected in CASES:
        assert full(sql) == expected, sql


def test_placeholder_count_is_preserved():
    # property: every ? becomes exactly one %s, for any statement in the app
    for sql, _ in CASES:
        assert full(sql).count("%s") == sql.count("?")


def test_split_skips_comment_only_fragments():
    script = "-- header\nCREATE TABLE a (id int);\n-- section\nCREATE TABLE b (id int);\n-- trailer\n"
    stmts = list(_split_statements(script))
    assert len(stmts) == 2
    assert all(re.search(r"CREATE TABLE", s) for s in stmts)
