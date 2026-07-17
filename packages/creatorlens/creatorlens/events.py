"""First-class audit log. Every governed action and system transition lands here."""

from __future__ import annotations

import json
import sqlite3

from .db import now_iso


def log_event(
    conn: sqlite3.Connection,
    actor: str,
    event_type: str,
    object_type: str | None = None,
    object_id: int | None = None,
    detail: dict | None = None,
) -> None:
    conn.execute(
        "INSERT INTO events (ts, actor, event_type, object_type, object_id, detail_json)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (now_iso(), actor, event_type, object_type, object_id, json.dumps(detail or {})),
    )
