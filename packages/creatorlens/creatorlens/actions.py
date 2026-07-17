"""Governed actions — the only write paths besides ingestion and scoring.

Each action checks its preconditions, changes state, and logs an Event.
Used by both the API layer and the seed script (actor differs).
"""

from __future__ import annotations

import json
import sqlite3

from . import PLATFORMS
from .db import now_iso, row
from .events import log_event


class ActionRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def create_creator(conn: sqlite3.Connection, handle: str, display_name: str,
                   primary_topic: str, actor: str = "user") -> dict:
    if row(conn, "SELECT id FROM creators WHERE handle = ?", (handle,)):
        raise ActionRejected("handle_exists")
    cur = conn.execute(
        "INSERT INTO creators (handle, display_name, primary_topic, status, created_at)"
        " VALUES (?, ?, ?, 'active', ?)",
        (handle, display_name, primary_topic, now_iso()),
    )
    creator_id = cur.lastrowid
    log_event(conn, actor, "creator.created", "creator", creator_id,
              {"handle": handle, "display_name": display_name, "primary_topic": primary_topic})
    conn.commit()
    return row(conn, "SELECT * FROM creators WHERE id = ?", (creator_id,))


def connect_platform(conn: sqlite3.Connection, creator_id: int, platform: str,
                     handle: str | None = None, actor: str = "user") -> dict:
    creator = row(conn, "SELECT * FROM creators WHERE id = ?", (creator_id,))
    if creator is None:
        raise ActionRejected("unknown_creator")
    if creator["status"] != "active":
        raise ActionRejected("creator_not_active")
    if platform not in PLATFORMS:
        raise ActionRejected("unknown_platform")

    handle = handle or creator["handle"]
    existing = row(conn,
                   "SELECT * FROM platform_accounts WHERE creator_id = ? AND platform = ?",
                   (creator_id, platform))
    if existing and existing["connection_status"] == "connected":
        raise ActionRejected("already_connected")

    if existing:  # reconnect a disconnected/error account — history is retained
        conn.execute(
            "UPDATE platform_accounts SET connection_status = 'connected', connected_at = ? WHERE id = ?",
            (now_iso(), existing["id"]),
        )
        account_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO platform_accounts (creator_id, platform, handle, external_id,"
            " connection_status, source, connected_at)"
            " VALUES (?, ?, ?, ?, 'connected', 'mock', ?)",
            (creator_id, platform, handle, f"mock-{platform}-{handle}", now_iso()),
        )
        account_id = cur.lastrowid
    log_event(conn, actor, "account.connected", "platform_account", account_id,
              {"creator_id": creator_id, "platform": platform, "handle": handle,
               "reconnect": existing is not None})
    conn.commit()
    return row(conn, "SELECT * FROM platform_accounts WHERE id = ?", (account_id,))


def disconnect_platform(conn: sqlite3.Connection, account_id: int, actor: str = "user") -> dict:
    account = row(conn, "SELECT * FROM platform_accounts WHERE id = ?", (account_id,))
    if account is None:
        raise ActionRejected("unknown_account")
    if account["connection_status"] == "disconnected":
        raise ActionRejected("already_disconnected")
    conn.execute("UPDATE platform_accounts SET connection_status = 'disconnected' WHERE id = ?",
                 (account_id,))
    log_event(conn, actor, "account.disconnected", "platform_account", account_id,
              {"creator_id": account["creator_id"], "platform": account["platform"]})
    conn.commit()
    return row(conn, "SELECT * FROM platform_accounts WHERE id = ?", (account_id,))


def create_target(conn: sqlite3.Connection, name: str, age_buckets: list[str],
                  genders: list[str], countries: list[str], topics: list[str],
                  actor: str = "user") -> dict:
    if row(conn, "SELECT id FROM sponsor_targets WHERE name = ?", (name,)):
        raise ActionRejected("name_exists")
    cur = conn.execute(
        "INSERT INTO sponsor_targets (name, age_buckets, genders, countries, topics, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (name, json.dumps(age_buckets), json.dumps(genders), json.dumps(countries),
         json.dumps(topics), now_iso()),
    )
    target_id = cur.lastrowid
    log_event(conn, actor, "target.created", "sponsor_target", target_id, {"name": name})
    conn.commit()
    return row(conn, "SELECT * FROM sponsor_targets WHERE id = ?", (target_id,))
