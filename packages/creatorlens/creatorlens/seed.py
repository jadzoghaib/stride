"""Seed dataset — five creators with deliberately varied platform coverage,
three sponsor targets. Exercises full coverage (3/3), partial (2/3, 1/3),
single-platform, and the nothing-connected empty state.
"""

from __future__ import annotations

import sqlite3

from .actions import create_creator, connect_platform, create_target
from .analytics.scoring import InsufficientData, store_scores
from .ingestion import sync_account

CREATORS = [
    ("mayachen.fit", "Maya Chen", "fitness", ["instagram", "youtube", "tiktok"]),
    ("dariofilms", "Dario Fontaine", "film", ["youtube", "instagram"]),
    ("linakovac", "Lina Kovač", "fashion", ["instagram"]),
    ("trailbyte", "TrailByte", "tech", ["youtube"]),
    ("rioalmeida", "Rio Almeida", "music", []),  # empty state: nothing connected
]

TARGETS = [
    ("US/EU 18-34 fitness & wellness", ["18-24", "25-34"], [],
     ["US", "GB", "DE", "FR", "CA"], ["fitness", "wellness", "sports"]),
    ("Global 18-44 tech & gaming", ["18-24", "25-34", "35-44"], [],
     ["US", "IN", "GB", "DE", "BR"], ["tech", "gaming"]),
    ("EU 25-44 fashion & lifestyle", ["25-34", "35-44"], ["female"],
     ["GB", "DE", "FR", "ES"], ["fashion", "lifestyle"]),
]


def seed(conn: sqlite3.Connection) -> dict:
    summary = {"creators": 0, "accounts": 0, "scored": 0, "targets": 0}

    default_target = None
    for name, ages, genders, countries, topics in TARGETS:
        target = create_target(conn, name, ages, genders, countries, topics, actor="system")
        default_target = default_target or target
        summary["targets"] += 1

    for handle, display_name, topic, platforms in CREATORS:
        creator = create_creator(conn, handle, display_name, topic, actor="system")
        summary["creators"] += 1
        for platform in platforms:
            account = connect_platform(conn, creator["id"], platform, actor="system")
            sync_account(conn, account["id"], trigger="seed")
            summary["accounts"] += 1
        try:
            store_scores(conn, creator["id"], target_id=default_target["id"], actor="system")
            summary["scored"] += 1
        except InsufficientData:
            pass  # the empty-state creator, by design
    return summary


def is_seeded(conn: sqlite3.Connection) -> bool:
    r = conn.execute("SELECT COUNT(*) AS n FROM creators").fetchone()
    return r["n"] > 0
