"""Splitting SQL into statements — the lexer, on its own.

The Postgres backend was unusable from the day it was written because this split
the schema on every `;`, and `schema_pg.sql` has one inside a `--` comment on
line 7. The server was handed a fragment starting mid-sentence and every run
died on `syntax error at or near "the"`.

The replacement walks the script, which makes it a small lexer, and a small
lexer with no tests is how the next version of this bug arrives. Each case below
is a place a semicolon means nothing, or a place something only looks like a
quote.
"""

from __future__ import annotations

import pathlib

from stride_api.pgconn import _split_statements


def parts(script: str) -> list[str]:
    return [s.strip() for s in _split_statements(script)]


# ── the bug that made the backend unusable ──────────────────────────────────

def test_a_semicolon_inside_a_line_comment_does_not_end_a_statement():
    """Verbatim shape of the line that broke it: a comment with a semicolon in
    the middle, immediately above real DDL."""
    script = """
    -- RLS policies live elsewhere
    -- (only meaningful per-user; the service connection bypasses them).
    CREATE TABLE users (id INT);
    """
    assert parts(script) == ["-- RLS policies live elsewhere\n"
                             "    -- (only meaningful per-user; the service connection "
                             "bypasses them).\n"
                             "    CREATE TABLE users (id INT)"]


def test_the_real_schema_splits_into_statements_that_all_look_like_sql():
    """The end-to-end version: nothing in the shipped schema may produce a
    fragment that does not begin with a SQL keyword."""
    schema = (pathlib.Path(__file__).parents[1] / "stride_api" / "schema_pg.sql")
    starts = set()
    for stmt in _split_statements(schema.read_text(encoding="utf-8")):
        for line in stmt.splitlines():
            bare = line.strip()
            if bare and not bare.startswith("--"):
                starts.add(bare.split()[0].upper())
                break
    assert starts <= {"CREATE", "ALTER", "DROP", "INSERT", "DO", "COMMENT", "GRANT"}, starts


# ── the other three places a semicolon means nothing ────────────────────────

def test_a_semicolon_inside_a_string_literal_is_not_a_split():
    stmts = parts("INSERT INTO t VALUES ('a;b'); SELECT 1")
    assert stmts == ["INSERT INTO t VALUES ('a;b')", "SELECT 1"]


def test_a_semicolon_inside_a_quoted_identifier_is_not_a_split():
    stmts = parts('CREATE TABLE "od;d" (id INT); SELECT 1')
    assert stmts == ['CREATE TABLE "od;d" (id INT)', "SELECT 1"]


def test_a_semicolon_inside_a_block_comment_is_not_a_split():
    stmts = parts("/* one; two */ SELECT 1; SELECT 2")
    assert stmts == ["/* one; two */ SELECT 1", "SELECT 2"]


def test_a_dollar_quoted_body_is_one_statement():
    """Not hypothetical: the Supabase migration is a single `do $$ ... $$` block
    whose semicolons are all interior. Splitting it would shred it."""
    script = "do $$ begin perform 1; perform 2; end $$; SELECT 1"
    assert parts(script) == ["do $$ begin perform 1; perform 2; end $$", "SELECT 1"]


def test_a_named_dollar_tag_is_matched_by_its_own_name():
    script = "do $body$ select 'a $$ b'; $body$; SELECT 1"
    assert parts(script) == ["do $body$ select 'a $$ b'; $body$", "SELECT 1"]


# ── things that only look like quoting ──────────────────────────────────────

def test_a_doubled_quote_is_an_escape_not_a_terminator():
    stmts = parts("SELECT 'it''s; fine'; SELECT 2")
    assert stmts == ["SELECT 'it''s; fine'", "SELECT 2"]


def test_a_backslash_escapes_only_inside_an_E_string():
    r"""`E'...'` honours `\'`; a standard literal does not, where the backslash
    is just a character and the quote still closes the string."""
    assert parts(r"SELECT E'a\'; b'; SELECT 2") == [r"SELECT E'a\'; b'", "SELECT 2"]
    # standard string: the quote after the backslash really does close it
    assert len(parts(r"SELECT 'a\'; SELECT 2")) == 2


def test_a_dollar_in_an_identifier_does_not_open_a_quoted_body():
    """`a$b$c` is one identifier and `$1` is a parameter. Reading either as a
    dollar quote swallows every statement up to the next matching run."""
    assert parts("SELECT a$b$c FROM t; SELECT 2") == ["SELECT a$b$c FROM t", "SELECT 2"]
    assert parts("SELECT $1 FROM t; SELECT 2") == ["SELECT $1 FROM t", "SELECT 2"]


# ── what is not a statement ─────────────────────────────────────────────────

def test_comment_only_fragments_are_dropped():
    """A trailing section header is not something to send to the server."""
    assert parts("SELECT 1;\n-- a closing note\n") == ["SELECT 1"]
    assert parts("-- nothing but a comment\n") == []
    assert parts("   \n\n  ") == []
