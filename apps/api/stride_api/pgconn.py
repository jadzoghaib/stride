"""Postgres compatibility shim.

The app's data layer was written in SQLite dialect (``?`` placeholders,
``cur.lastrowid``, ``INSERT OR IGNORE``, ``executescript``). Rather than rewrite
every query, this shim presents the same tiny surface the code already uses —
``conn.execute(sql, params)`` returning a cursor with ``fetchone``/``fetchall``/
``lastrowid``, plus ``executescript``/``commit``/``close`` — backed by psycopg3.

Translations applied per statement:
  * ``?``            -> ``%s``            (psycopg paramstyle)
  * ``INSERT OR IGNORE`` -> ``INSERT ... ON CONFLICT DO NOTHING``
  * every ``INSERT`` gets ``RETURNING id`` appended so ``lastrowid`` works
    (no-op for conflict-skipped rows, which return no id — matching SQLite).

Rows come back as dicts (``dict_row``), so ``row()``/``rows()`` are unchanged.
The SQL the code already contains is standard enough that nothing else differs;
``ON CONFLICT ... DO UPDATE ... excluded.x`` is identical in both engines.
"""

from __future__ import annotations

import re

import psycopg
from psycopg.rows import dict_row

_INSERT = re.compile(r"^\s*insert\s+into", re.IGNORECASE)
_INSERT_OR_IGNORE = re.compile(r"^(\s*insert)\s+or\s+ignore(\s+into)", re.IGNORECASE)


def _translate(sql: str) -> tuple[str, bool]:
    """Return (postgres_sql, is_insert_or_ignore). Our SQL never contains a
    literal '%' in the statement text — LIKE wildcards live in bound params —
    but we escape defensively before swapping placeholders."""
    ignore = bool(_INSERT_OR_IGNORE.match(sql))
    if ignore:
        sql = _INSERT_OR_IGNORE.sub(r"\1\2", sql)
    sql = sql.replace("%", "%%").replace("?", "%s")
    if ignore:
        sql += " ON CONFLICT DO NOTHING"
    return sql, ignore


def _split_statements(script: str):
    """Split DDL into single statements. Safe here because the schema file has
    no semicolons inside string literals or identifiers. Fragments that are
    only comments/whitespace (e.g. trailing section headers) are skipped."""
    for stmt in script.split(";"):
        meaningful = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        if meaningful:
            yield stmt


class _Cursor:
    __slots__ = ("_cur", "lastrowid")

    def __init__(self, cur, lastrowid):
        self._cur = cur
        self.lastrowid = lastrowid

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()


class PgConnection:
    """Duck-types the subset of sqlite3.Connection the app relies on."""

    def __init__(self, dsn: str):
        # prepare_threshold=None: disable server-side prepared statements.
        # Supabase's transaction pooler (port 6543) — and PgBouncer generally —
        # breaks them with "prepared statement ... does not exist". Costs little
        # on a session pooler, prevents a confusing production error.
        self._conn = psycopg.connect(dsn, row_factory=dict_row, autocommit=False,
                                     prepare_threshold=None, connect_timeout=10)

    def execute(self, sql: str, params: tuple = ()) -> _Cursor:
        pg_sql, _ = _translate(sql)
        want_id = bool(_INSERT.match(pg_sql)) and " returning " not in pg_sql.lower()
        if want_id:
            pg_sql += " RETURNING id"
        cur = self._conn.cursor()
        cur.execute(pg_sql, tuple(params))
        lastrowid = None
        if want_id:
            try:
                fetched = cur.fetchone()
                lastrowid = fetched["id"] if fetched else None
            except psycopg.ProgrammingError:
                lastrowid = None  # nothing to return
        return _Cursor(cur, lastrowid)

    def executescript(self, script: str) -> None:
        with self._conn.cursor() as cur:
            for stmt in _split_statements(script):
                cur.execute(stmt)
        self._conn.commit()

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()
