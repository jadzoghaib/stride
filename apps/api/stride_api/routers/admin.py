"""Admin surface: audit log access + chaos controls (resilience drills)."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, require_role
from ..chaos import chaos
from ..config import settings
from ..db import loads_events, rows

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/events")
def audit_events(event_type: str | None = None, limit: int = Query(200, le=1000),
                 user: dict = Depends(require_role("admin")),
                 conn: sqlite3.Connection = Depends(get_db)):
    if event_type:
        events = rows(conn, "SELECT * FROM events WHERE event_type = ?"
                      " ORDER BY ts DESC, id DESC LIMIT ?", (event_type, limit))
    else:
        events = rows(conn, "SELECT * FROM events ORDER BY ts DESC, id DESC LIMIT ?", (limit,))
    return loads_events(events)


class ChaosIn(BaseModel):
    latency_ms: int = Field(ge=0, le=10000, default=0)
    error_rate: float = Field(ge=0, le=1, default=0.0)
    db_down: bool = False


def _chaos_state() -> dict:
    """One shape for all three endpoints.

    The GET returned `enabled` and both POSTs did not, and the client replaces
    its whole state object with whatever comes back — so a successful injection
    set `enabled` to undefined, which reads as false. The panel then announced
    "disabled in this environment" and greyed out the buttons that had just
    worked.
    """
    return {"enabled": settings.chaos_enabled, **chaos.as_dict()}


@router.get("/chaos")
def chaos_state(user: dict = Depends(require_role("admin"))):
    return _chaos_state()


@router.post("/chaos")
def set_chaos(body: ChaosIn, user: dict = Depends(require_role("admin"))):
    if not settings.chaos_enabled:
        raise HTTPException(403, "chaos_disabled_in_this_environment")
    chaos.latency_ms = body.latency_ms
    chaos.error_rate = body.error_rate
    chaos.db_down = body.db_down
    return _chaos_state()


@router.post("/chaos/reset")
def reset_chaos(user: dict = Depends(require_role("admin"))):
    chaos.reset()
    return _chaos_state()
