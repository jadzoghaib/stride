"""Direct messages and notifications.

**Who may open a conversation** is the whole design, because an open inbox on a
marketplace is a spam surface pointed at the people with the most followers:

    athlete    anyone
    sponsor    athletes  (they are here to make offers)
    fan        athletes they subscribe to
    club       nobody, on the rules as written

Two things sit on top of that. First, **a conversation that exists can always be
answered** -- otherwise a sponsor could open a thread an athlete cannot reply
to, and a club could be messaged with no way to respond. Reply rights come from
the thread, not from the role. Second, permission is checked on *every* send,
not just the first: a fan who unsubscribes keeps the thread they already have
but stops being able to start new ones.

Notifications are written where things happen rather than polled for here. The
rule is that anything arriving in a person's world without them asking -- an
offer, an invitation, a decision on their application, a message -- leaves a
row. Nothing here sends email; `email_outbox` in the admission router is where
that would attach.
"""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth import get_db, require_role
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api", tags=["messaging"])


# ── who may talk to whom ────────────────────────────────────────────────────

def may_open(conn, sender: dict, recipient: dict) -> bool:
    """Whether `sender` may *start* a conversation with `recipient`."""
    if sender["id"] == recipient["id"]:
        return False
    if sender["role"] == "athlete":
        return True
    recipient_athlete = row(conn, "SELECT id FROM athlete_profiles WHERE user_id = ?",
                            (recipient["id"],))
    if recipient_athlete is None:
        return False
    if sender["role"] == "sponsor":
        return True
    if sender["role"] == "fan":
        return row(conn, "SELECT id FROM subscriptions WHERE user_id = ? AND athlete_id = ?",
                   (sender["id"], recipient_athlete["id"])) is not None
    return False


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def existing_thread(conn, a: int, b: int) -> dict | None:
    low, high = _pair(a, b)
    return row(conn, "SELECT * FROM conversations WHERE user_a = ? AND user_b = ?", (low, high))


def may_message(conn, sender: dict, recipient: dict) -> bool:
    """Start a new one, or answer one that is already open."""
    if existing_thread(conn, sender["id"], recipient["id"]) is not None:
        return True
    return may_open(conn, sender, recipient)


# ── notifications, written by whoever caused them ───────────────────────────

def notify(conn, user_id: int, kind: str, title: str, body: str = "", link: str = "") -> None:
    """Record something that arrived in this person's world uninvited.

    Callers are already inside a transaction they will commit; this does not
    commit on its own, so a notification cannot survive the action that caused
    it being rolled back.
    """
    conn.execute("INSERT INTO notifications (user_id, kind, title, body, link, created_at)"
                 " VALUES (?, ?, ?, ?, ?, ?)", (user_id, kind, title, body, link, now_iso()))


# ── the inbox ───────────────────────────────────────────────────────────────

MESSAGING_ROLES = ("athlete", "club", "sponsor", "fan", "admin")


def _other(conn, conversation: dict, me: int) -> dict:
    other_id = conversation["user_b"] if conversation["user_a"] == me else conversation["user_a"]
    who = row(conn, "SELECT id, display_name, role FROM users WHERE id = ?", (other_id,))
    athlete = row(conn, "SELECT slug FROM athlete_profiles WHERE user_id = ?", (other_id,))
    club = row(conn, "SELECT slug FROM clubs WHERE user_id = ?", (other_id,))
    return {"id": other_id, "display_name": who["display_name"], "role": who["role"],
            "slug": (athlete or club or {}).get("slug")}


@router.get("/inbox")
def inbox(user: dict = Depends(require_role(*MESSAGING_ROLES)),
          conn: sqlite3.Connection = Depends(get_db)):
    threads = rows(conn, "SELECT * FROM conversations WHERE user_a = ? OR user_b = ?"
                         " ORDER BY last_message_at DESC", (user["id"], user["id"]))
    out = []
    for t in threads:
        last = row(conn, "SELECT body, sender_id, created_at FROM messages"
                         " WHERE conversation_id = ? ORDER BY id DESC LIMIT 1", (t["id"],))
        unread = row(conn, "SELECT COUNT(*) AS n FROM messages WHERE conversation_id = ?"
                           " AND sender_id != ? AND read_at IS NULL", (t["id"], user["id"]))
        out.append({"id": t["id"], "with": _other(conn, t, user["id"]),
                    "last_message": last["body"] if last else "",
                    "last_at": t["last_message_at"],
                    "unread": unread["n"] if unread else 0})
    return out


@router.get("/inbox/{conversation_id}")
def thread(conversation_id: int, user: dict = Depends(require_role(*MESSAGING_ROLES)),
           conn: sqlite3.Connection = Depends(get_db)):
    t = row(conn, "SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    if t is None or user["id"] not in (t["user_a"], t["user_b"]):
        # 404 rather than 403: a thread you are not in should not be confirmed
        # to exist by the shape of the refusal.
        raise HTTPException(404, "unknown_conversation")
    conn.execute("UPDATE messages SET read_at = ? WHERE conversation_id = ?"
                 " AND sender_id != ? AND read_at IS NULL",
                 (now_iso(), conversation_id, user["id"]))
    conn.commit()
    return {"id": t["id"], "with": _other(conn, t, user["id"]),
            "messages": [{"id": m["id"], "body": m["body"], "at": m["created_at"],
                          "mine": m["sender_id"] == user["id"]}
                         for m in rows(conn, "SELECT * FROM messages WHERE conversation_id = ?"
                                             " ORDER BY id", (conversation_id,))]}


class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    to_user: int | None = None
    to_athlete: str | None = None
    to_club: str | None = None


def _resolve(conn, body: MessageIn) -> dict:
    if body.to_athlete:
        found = row(conn, "SELECT user_id FROM athlete_profiles WHERE slug = ?", (body.to_athlete,))
    elif body.to_club:
        found = row(conn, "SELECT user_id FROM clubs WHERE slug = ?", (body.to_club,))
    elif body.to_user:
        found = {"user_id": body.to_user}
    else:
        raise HTTPException(422, "no_recipient")
    if found is None or found["user_id"] is None:
        raise HTTPException(404, "unknown_recipient")
    who = row(conn, "SELECT id, display_name, role FROM users WHERE id = ?", (found["user_id"],))
    if who is None:
        raise HTTPException(404, "unknown_recipient")
    return who


@router.post("/messages", status_code=201)
def send(body: MessageIn, user: dict = Depends(require_role(*MESSAGING_ROLES)),
         conn: sqlite3.Connection = Depends(get_db)):
    recipient = _resolve(conn, body)
    if not may_message(conn, user, recipient):
        raise HTTPException(403, "cannot_message_this_person")

    thread_row = existing_thread(conn, user["id"], recipient["id"])
    if thread_row is None:
        low, high = _pair(user["id"], recipient["id"])
        cur = conn.execute("INSERT INTO conversations (user_a, user_b, created_at,"
                           " last_message_at) VALUES (?, ?, ?, ?)",
                           (low, high, now_iso(), now_iso()))
        conversation_id = cur.lastrowid
    else:
        conversation_id = thread_row["id"]
        conn.execute("UPDATE conversations SET last_message_at = ? WHERE id = ?",
                     (now_iso(), conversation_id))
    conn.execute("INSERT INTO messages (conversation_id, sender_id, body, created_at)"
                 " VALUES (?, ?, ?, ?)", (conversation_id, user["id"], body.body, now_iso()))
    notify(conn, recipient["id"], "message", f"{user['display_name']} messaged you",
           body.body[:140], "/inbox")
    log_event(conn, "user", "message.sent", "conversation", conversation_id,
              {"to": recipient["id"]})
    conn.commit()
    return {"ok": True, "conversation_id": conversation_id}


@router.get("/messages/can/{kind}/{slug}")
def can_message(kind: str, slug: str, user: dict = Depends(require_role(*MESSAGING_ROLES)),
                conn: sqlite3.Connection = Depends(get_db)):
    """Whether the envelope should be offered at all.

    The server owns this so the button cannot appear where the send would be
    refused -- a control whose only behaviour is a 403 is worse than no control.
    """
    if kind not in ("athlete", "club"):
        raise HTTPException(404, "unknown_subject")
    table = "athlete_profiles" if kind == "athlete" else "clubs"
    found = row(conn, f"SELECT user_id FROM {table} WHERE slug = ?", (slug,))
    if found is None or found["user_id"] is None:
        return {"can_message": False}
    who = row(conn, "SELECT id, display_name, role FROM users WHERE id = ?", (found["user_id"],))
    return {"can_message": who is not None and may_message(conn, user, who)}


# ── notifications ───────────────────────────────────────────────────────────

@router.get("/notifications")
def list_notifications(limit: int = Query(30, ge=1, le=100),
                       user: dict = Depends(require_role(*MESSAGING_ROLES)),
                       conn: sqlite3.Connection = Depends(get_db)):
    items = rows(conn, "SELECT * FROM notifications WHERE user_id = ?"
                       " ORDER BY id DESC LIMIT ?", (user["id"], limit))
    unread = row(conn, "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ?"
                       " AND read_at IS NULL", (user["id"],))
    return {"unread": unread["n"] if unread else 0,
            "items": [{"id": n["id"], "kind": n["kind"], "title": n["title"],
                       "body": n["body"], "link": n["link"], "at": n["created_at"],
                       "read": n["read_at"] is not None} for n in items]}


@router.post("/notifications/read")
def mark_read(user: dict = Depends(require_role(*MESSAGING_ROLES)),
              conn: sqlite3.Connection = Depends(get_db)):
    conn.execute("UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL",
                 (now_iso(), user["id"]))
    conn.commit()
    return {"ok": True}
