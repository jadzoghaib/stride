"""Block and report: the two levers a person needs when a message is unwelcome.

The permission matrix in `messaging.py` decides who may *start* a thread. It
cannot decide who a person wants to hear from -- only they can -- and with
sixteen-year-olds admitted and an open working network, "nobody can block
anyone" was the gap that mattered most.

  POST   /api/blocks/{user_id}      Stop this person reaching me, in either
                                    direction, thread or no thread. The block is
                                    theirs to place and theirs to lift; the
                                    other side is told nothing.
  DELETE /api/blocks/{user_id}
  GET    /api/blocks                My list.
  POST   /api/reports               Tell a reviewer about a person or a message.
                                    Reporting does not block; the two are
                                    offered together and chosen separately.
  GET    /api/admin/reports         The queue, open first.
  POST   /api/admin/reports/{id}/resolve
"""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import current_user, get_db, require_role
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api", tags=["safety"])

REPORT_REASONS = ("harassment", "spam", "impersonation", "inappropriate", "underage_concern", "other")
RESOLUTIONS = ("dismissed", "warned", "suspended")


# ── the rule the rest of messaging consults ──────────────────────────────────

def is_blocked_between(conn, a: int, b: int) -> bool:
    """A block in either direction ends contact both ways. The person who
    placed it should not receive; the person it names should not be able to
    keep a channel open by being the one who writes."""
    return row(conn, "SELECT 1 FROM user_blocks WHERE (blocker_id = ? AND blocked_id = ?)"
                     " OR (blocker_id = ? AND blocked_id = ?)", (a, b, b, a)) is not None


# ── blocks ───────────────────────────────────────────────────────────────────

@router.get("/blocks")
def my_blocks(user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    return rows(conn, """
        SELECT b.blocked_id AS user_id, u.display_name, u.role, b.created_at
        FROM user_blocks b JOIN users u ON u.id = b.blocked_id
        WHERE b.blocker_id = ? ORDER BY b.id DESC""", (user["id"],))


@router.post("/blocks/{user_id}", status_code=201)
def block(user_id: int, user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    if user_id == user["id"]:
        raise HTTPException(409, "cannot_block_yourself")
    if row(conn, "SELECT id FROM users WHERE id = ?", (user_id,)) is None:
        raise HTTPException(404, "unknown_user")
    if row(conn, "SELECT 1 FROM user_blocks WHERE blocker_id = ? AND blocked_id = ?",
           (user["id"], user_id)):
        return {"ok": True, "already": True}
    conn.execute("INSERT INTO user_blocks (blocker_id, blocked_id, created_at) VALUES (?, ?, ?)",
                 (user["id"], user_id, now_iso()))
    # the other party's unread notifications from this person are noise now
    conn.execute("DELETE FROM notifications WHERE user_id = ? AND actor_user_id = ? AND read_at IS NULL",
                 (user["id"], user_id))
    log_event(conn, "user", "user.blocked", "user", user["id"], {"blocked": user_id})
    conn.commit()
    return {"ok": True, "already": False}


@router.delete("/blocks/{user_id}")
def unblock(user_id: int, user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("DELETE FROM user_blocks WHERE blocker_id = ? AND blocked_id = ?", (user["id"], user_id))
    log_event(conn, "user", "user.unblocked", "user", user["id"], {"unblocked": user_id})
    conn.commit()
    return {"ok": True}


# ── reports ──────────────────────────────────────────────────────────────────

class ReportIn(BaseModel):
    user_id: int
    reason: str = Field(max_length=40)
    detail: str = Field(default="", max_length=2000)
    # optional pointer at the specific thing, for the reviewer
    message_id: int | None = None
    content_id: int | None = None


@router.post("/reports", status_code=201)
def report(body: ReportIn, user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    if body.reason not in REPORT_REASONS:
        raise HTTPException(422, "unknown_report_reason")
    if body.user_id == user["id"]:
        raise HTTPException(409, "cannot_report_yourself")
    if row(conn, "SELECT id FROM users WHERE id = ?", (body.user_id,)) is None:
        raise HTTPException(404, "unknown_user")
    if body.message_id is not None:
        # the message has to exist, be by the reported person, and be in a
        # thread the reporter is actually in -- a report is not a way to read
        m = row(conn, """SELECT m.id FROM messages m JOIN conversations c ON c.id = m.conversation_id
                         WHERE m.id = ? AND m.sender_id = ? AND (c.user_a = ? OR c.user_b = ?)""",
                (body.message_id, body.user_id, user["id"], user["id"]))
        if m is None:
            raise HTTPException(404, "unknown_message")
    cur = conn.execute("""INSERT INTO reports (reporter_id, reported_user_id, reason, detail,
                          message_id, content_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                       (user["id"], body.user_id, body.reason, body.detail.strip(),
                        body.message_id, body.content_id, now_iso()))
    log_event(conn, "user", "report.filed", "report", cur.lastrowid,
              {"reported": body.user_id, "reason": body.reason})
    conn.commit()
    return {"ok": True, "id": cur.lastrowid}


# ── the reviewer's queue ─────────────────────────────────────────────────────

@router.get("/admin/reports")
def report_queue(status: str = Query("open", pattern="^(open|resolved|all)$"),
                 limit: int = Query(100, ge=1, le=500),
                 _: dict = Depends(require_role("admin")),
                 conn: sqlite3.Connection = Depends(get_db)):
    where = {"open": "WHERE r.resolved_at IS NULL", "resolved": "WHERE r.resolved_at IS NOT NULL", "all": ""}[status]
    out = rows(conn, f"""
        SELECT r.*, rep.display_name AS reporter_name, rep.role AS reporter_role,
               tgt.display_name AS reported_name, tgt.role AS reported_role, tgt.status AS reported_status,
               m.body AS message_body
        FROM reports r
        JOIN users rep ON rep.id = r.reporter_id
        JOIN users tgt ON tgt.id = r.reported_user_id
        LEFT JOIN messages m ON m.id = r.message_id
        {where} ORDER BY r.resolved_at IS NOT NULL, r.id DESC LIMIT ?""", (limit,))
    for r in out:
        r["prior_reports"] = row(conn, "SELECT COUNT(*) AS n FROM reports WHERE reported_user_id = ?"
                                       " AND id <> ?", (r["reported_user_id"], r["id"]))["n"]
    return out


class ResolveIn(BaseModel):
    resolution: str = Field(max_length=20)
    note: str = Field(default="", max_length=2000)


@router.post("/admin/reports/{report_id}/resolve")
def resolve_report(report_id: int, body: ResolveIn, admin: dict = Depends(require_role("admin")),
                   conn: sqlite3.Connection = Depends(get_db)):
    if body.resolution not in RESOLUTIONS:
        raise HTTPException(422, "unknown_resolution")
    r = row(conn, "SELECT * FROM reports WHERE id = ?", (report_id,))
    if r is None:
        raise HTTPException(404, "unknown_report")
    if r["resolved_at"] is not None:
        raise HTTPException(409, "already_resolved")
    conn.execute("UPDATE reports SET resolved_at = ?, resolved_by = ?, resolution = ?, resolution_note = ?"
                 " WHERE id = ?", (now_iso(), admin["id"], body.resolution, body.note.strip(), report_id))
    if body.resolution == "suspended":
        # every session dies with the status change; the login refuses from here on
        conn.execute("UPDATE users SET status = 'suspended', token_version = token_version + 1 WHERE id = ?",
                     (r["reported_user_id"],))
    log_event(conn, "user", "report.resolved", "report", report_id,
              {"resolution": body.resolution, "reported": r["reported_user_id"], "by": admin["id"]})
    conn.commit()
    return {"ok": True}
