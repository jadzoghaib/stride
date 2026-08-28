"""Fan monetisation event taxonomy — the Phase-2 analytics dataset.

business-plan/09-analytics-strategy.md argues that instrumentation is the only
urgent analytics work: a late analyst is merely late, but an event that was
never written cannot be recovered. These five events are the whole dataset the
first analytics hire will need, and defining them now costs an afternoon.

    subscription.started    a fan begins paying an athlete
    subscription.cancelled  a fan stops (the churn numerator)
    content.unlocked        a one-off purchase (PPV)
    tip.sent                a voluntary payment
    paywall.viewed          a fan hit a paywall — the conversion denominator

**Three of these have no live trigger yet.** Subscriptions, paid content and
paywalls are P1/P2 in business-plan/05-product-gaps.md; nothing in the product
can charge a fan today. What exists here is the *contract*: the names, the
required dimensions, and a test that fails if either drifts. When P1 ships, the
emitter is already there and the analytics schema is already fixed — which is
the entire point, because the alternative is discovering in year three that
six months of cohorts are unreadable.

Every event carries the four dimensions every Phase-2 question needs to slice
by: athlete, sport, country, tier. Getting those attached at write time is what
makes cohort analysis possible later; joining them back afterwards is not always
possible, because an athlete's sport or tier can change.
"""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event

# The taxonomy. Adding to this is cheap; renaming is not, because it silently
# splits a cohort in two — hence the contract test.
SUBSCRIPTION_STARTED = "subscription.started"
SUBSCRIPTION_CANCELLED = "subscription.cancelled"
CONTENT_UNLOCKED = "content.unlocked"
TIP_SENT = "tip.sent"
PAYWALL_VIEWED = "paywall.viewed"

# The two that only mean anything as a matched pair: a start with no fan
# identity cannot be joined to the cancellation that ends it, and cohort churn
# is the entire question these events exist to answer.
SUBSCRIPTION_EVENTS = (SUBSCRIPTION_STARTED, SUBSCRIPTION_CANCELLED)

FAN_EVENTS = (
    SUBSCRIPTION_STARTED,
    SUBSCRIPTION_CANCELLED,
    CONTENT_UNLOCKED,
    TIP_SENT,
    PAYWALL_VIEWED,
)

# Dimensions required on every fan event. A missing one is not a warning: it is
# a row that cannot be grouped, which is the same as a row that was not written.
REQUIRED_DIMENSIONS = ("athlete_id", "sport", "country", "tier")


class MissingDimension(ValueError):
    """Raised when an event would be written without a dimension needed to
    analyse it. Failing loudly at write time is far cheaper than discovering an
    ungroupable cohort a year later."""


def log_fan_event(conn: sqlite3.Connection, event_type: str, *,
                  athlete_id: int, sport: str, country: str, tier: str,
                  amount_eur: float | None = None,
                  fan_user_id: int | None = None,
                  detail: dict | None = None) -> None:
    """Write one fan-monetisation event to the shared audit log.

    Reuses the `events` table rather than adding an analytics store: it already
    takes an arbitrary object type, it is already backed up, and at this volume
    a separate warehouse would be infrastructure without a question to answer.
    Phase 3 can move it (09-analytics-strategy.md).
    """
    if event_type not in FAN_EVENTS:
        raise ValueError(f"unknown fan event: {event_type}")

    dims = {"athlete_id": athlete_id, "sport": sport, "country": country, "tier": tier}
    missing = [k for k, v in dims.items() if v is None or v == ""]
    if missing:
        raise MissingDimension(f"{event_type} needs {', '.join(missing)}")

    # Write time is the only moment a fan identity can still be supplied: the
    # cancellation arrives months later with nothing to join it back to.
    if event_type in SUBSCRIPTION_EVENTS and fan_user_id is None:
        raise MissingDimension(f"{event_type} needs fan_user_id to close a churn cohort")

    payload = dict(dims)
    if amount_eur is not None:
        payload["amount_eur"] = round(float(amount_eur), 2)
    if fan_user_id is not None:
        payload["fan_user_id"] = fan_user_id
    if detail:
        # `payload |= detail` let a caller replace a dimension that had just been
        # validated two lines above, so an event could pass the check and still
        # land ungroupable — the exact failure this module exists to prevent.
        # Extra context is welcome; overwriting a dimension is a call-site bug.
        clashes = sorted(set(detail) & set(payload))
        if clashes:
            raise MissingDimension(
                f"{event_type} detail may not overwrite {', '.join(clashes)}")
        payload |= detail

    # actor is "user", not "fan": the events table constrains it to
    # ('user','system'), and a fan is a user of the platform. The fan's own
    # identity travels in the payload as fan_user_id, which is where a
    # dimension belongs anyway.
    log_event(conn, "user", event_type, "athlete_profile", athlete_id, payload)
