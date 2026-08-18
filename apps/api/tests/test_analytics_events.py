"""Locks the fan-event contract.

Deliberately isolated: these build their own throwaway database rather than
using the seeded session fixtures. A contract test should not depend on demo
data, and sharing the session connection made the suite order-dependent.

These names and dimensions are the Phase-2 analytics dataset
(business-plan/09-analytics-strategy.md). Renaming an event silently splits a
cohort in two; dropping a dimension silently makes rows ungroupable. Neither
failure is visible at the time it happens, which is exactly why it is asserted
here rather than left to review.
"""

from __future__ import annotations

import sqlite3

import pytest

from creatorlens.db import SCHEMA as CREATORLENS_SCHEMA
from stride_api.analytics import (CONTENT_UNLOCKED, FAN_EVENTS, PAYWALL_VIEWED,
                                  REQUIRED_DIMENSIONS, SUBSCRIPTION_CANCELLED,
                                  SUBSCRIPTION_STARTED, TIP_SENT, MissingDimension,
                                  log_fan_event)


@pytest.fixture()
def db():
    """A fresh in-memory database with just the audit table's schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(CREATORLENS_SCHEMA)
    conn.commit()
    yield conn
    conn.close()


def test_taxonomy_is_exactly_the_five_planned_events():
    assert set(FAN_EVENTS) == {
        "subscription.started", "subscription.cancelled",
        "content.unlocked", "tip.sent", "paywall.viewed",
    }
    # every name is namespaced, so the audit log stays greppable by domain
    assert all("." in e for e in FAN_EVENTS)


def test_every_analysis_dimension_is_required():
    assert set(REQUIRED_DIMENSIONS) == {"athlete_id", "sport", "country", "tier"}


def test_events_land_in_the_audit_log_with_their_dimensions(db):
    before = db.execute("SELECT COUNT(*) c FROM events").fetchone()["c"]
    log_fan_event(db, SUBSCRIPTION_STARTED, athlete_id=1, sport="Padel",
                  country="Spain", tier="insider", amount_eur=9.99, fan_user_id=42)
    db.commit()

    assert db.execute("SELECT COUNT(*) c FROM events").fetchone()["c"] == before + 1
    row = db.execute("SELECT * FROM events WHERE event_type = ? ORDER BY id DESC LIMIT 1",
                     (SUBSCRIPTION_STARTED,)).fetchone()
    import json
    detail = json.loads(row["detail_json"])
    for dim in REQUIRED_DIMENSIONS:
        assert dim in detail, f"{dim} must be written at event time, not joined later"
    assert detail["amount_eur"] == 9.99
    assert row["object_type"] == "athlete_profile"


@pytest.mark.parametrize("event", [SUBSCRIPTION_CANCELLED, CONTENT_UNLOCKED,
                                   TIP_SENT, PAYWALL_VIEWED])
def test_all_five_events_are_writable(db, event):
    log_fan_event(db, event, athlete_id=1, sport="Trail", country="Spain", tier="supporter")
    db.commit()
    assert db.execute("SELECT COUNT(*) c FROM events WHERE event_type = ?",
                      (event,)).fetchone()["c"] >= 1


def test_a_missing_dimension_fails_loudly(db):
    """Failing at write time is cheaper than an ungroupable cohort a year later."""
    with pytest.raises(MissingDimension):
        log_fan_event(db, TIP_SENT, athlete_id=1, sport="", country="Spain", tier="insider")


def test_unknown_event_is_rejected(db):
    with pytest.raises(ValueError):
        log_fan_event(db, "subscription.renewed", athlete_id=1, sport="Padel",
                      country="Spain", tier="insider")
