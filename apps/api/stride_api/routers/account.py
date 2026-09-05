"""The account as a legal object: what is held about a person, and how it ends.

Two rights the data page had honestly marked "specified, not built":

  GET  /api/account/export   Art. 15 access and Art. 20 portability, one document.
                             Everything that references this user, as JSON,
                             machine-readable by construction.
  POST /api/account/delete   Art. 17 erasure. Anonymise rather than DELETE:
                             the account row and its public profile lose every
                             identifying field, the relationship rows go, and
                             the records an accounting or dispute duty attaches
                             to -- deals, commitments -- keep their numbers with
                             the name removed. That is the promise the rights
                             page makes, so it is what the code does.

Neither is role-specific. Every role has the same account, so every role gets
the same two doors.
"""

from __future__ import annotations

import sqlite3

from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from ..auth import clear_session_cookie, current_user, get_db, verify_password
from ..config import settings
from ..db import now_iso, row, rows

router = APIRouter(prefix="/api/account", tags=["account"])

EXPORT_FORMAT = "stride-export-1"


def _public(r: dict | None, drop: tuple[str, ...] = ("password_hash", "auth_id", "token_version")) -> dict | None:
    return None if r is None else {k: v for k, v in r.items() if k not in drop}


@router.get("/export")
def export_account(user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    """Everything held about this person, in one JSON document.

    Other people appear only as they would to this person inside the product
    (a display name on a thread, an athlete's handle on a deal) -- never their
    email or anything they did not already show this user.
    """
    uid = user["id"]
    out: dict = {
        "format": EXPORT_FORMAT,
        "generated_at": now_iso(),
        "account": _public(user),
        "profile": None,
        "platform_accounts": [],
        "score_snapshots": [],
        "content": [],
        "deals": [],
        "campaigns": [],
        "club_commitments": [],
        "follows": [],
        "subscriptions": [],
        "poll_votes": [],
        "wall_posts": [],
        "conversations": [],
        "notifications": [],
        "emails_owed": [],
        "audit_trail": [],
    }

    if user["role"] == "athlete":
        profile = row(conn, "SELECT * FROM athlete_profiles WHERE user_id = ?", (uid,))
        out["profile"] = profile
        if profile and profile["creatorlens_creator_id"]:
            cid = profile["creatorlens_creator_id"]
            out["platform_accounts"] = rows(conn, "SELECT platform, handle, connection_status, source,"
                                                  " connected_at, last_synced_at FROM platform_accounts"
                                                  " WHERE creator_id = ?", (cid,))
            out["score_snapshots"] = rows(conn, "SELECT formula_version, computed_at, audience_scale,"
                                                " engagement_quality, audience_fit, growth, consistency,"
                                                " coverage_json FROM score_snapshots WHERE creator_id = ?"
                                                " ORDER BY computed_at", (cid,))
        if profile:
            out["content"] = rows(conn, "SELECT * FROM content_items WHERE athlete_id = ?", (profile["id"],))
            out["deals"] = rows(conn, """
                SELECT d.*, c.name AS campaign_name, o.name AS sponsor_name
                FROM deals d JOIN campaigns c ON c.id = d.campaign_id
                             JOIN sponsor_orgs o ON o.id = d.org_id
                WHERE d.athlete_id = ?""", (profile["id"],))
            out["club_memberships"] = rows(conn, """
                SELECT cl.name AS club, cl.slug, m.position, m.status, m.joined_at
                FROM club_members m JOIN clubs cl ON cl.id = m.club_id WHERE m.athlete_id = ?""",
                                           (profile["id"],))
            out["applications"] = rows(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                                       (profile["id"],))
    elif user["role"] == "sponsor":
        org = row(conn, "SELECT * FROM sponsor_orgs WHERE user_id = ?", (uid,))
        out["profile"] = org
        if org:
            out["campaigns"] = rows(conn, "SELECT * FROM campaigns WHERE org_id = ?", (org["id"],))
            out["deals"] = rows(conn, """
                SELECT d.*, a.slug AS athlete FROM deals d
                JOIN athlete_profiles a ON a.id = d.athlete_id WHERE d.org_id = ?""", (org["id"],))
            out["club_commitments"] = rows(conn, """
                SELECT pc.*, p.name AS package, cl.name AS club FROM package_commitments pc
                JOIN club_packages p ON p.id = pc.package_id JOIN clubs cl ON cl.id = p.club_id
                WHERE pc.org_id = ?""", (org["id"],))
    elif user["role"] == "club":
        club = row(conn, "SELECT * FROM clubs WHERE user_id = ?", (uid,))
        out["profile"] = club
        if club:
            out["content"] = rows(conn, "SELECT * FROM content_items WHERE club_id = ?", (club["id"],))
            out["packages"] = rows(conn, "SELECT * FROM club_packages WHERE club_id = ?", (club["id"],))
            out["roster"] = rows(conn, """
                SELECT a.slug, a.display_name, m.position, m.status, m.joined_at
                FROM club_members m JOIN athlete_profiles a ON a.id = m.athlete_id
                WHERE m.club_id = ?""", (club["id"],))
            out["applications"] = rows(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club["id"],))

    out["follows"] = rows(conn, """
        SELECT a.slug, a.display_name, f.created_at FROM follows f
        JOIN athlete_profiles a ON a.id = f.athlete_id WHERE f.user_id = ?""", (uid,))
    out["subscriptions"] = rows(conn, """
        SELECT a.slug AS athlete, cl.slug AS club, s.created_at FROM subscriptions s
        LEFT JOIN athlete_profiles a ON a.id = s.athlete_id
        LEFT JOIN clubs cl ON cl.id = s.club_id WHERE s.user_id = ?""", (uid,))
    out["poll_votes"] = rows(conn, """
        SELECT ci.title AS poll, po.label AS choice, v.created_at FROM poll_votes v
        JOIN content_items ci ON ci.id = v.content_id JOIN poll_options po ON po.id = v.option_id
        WHERE v.user_id = ?""", (uid,))
    out["wall_posts"] = rows(conn, """
        SELECT a.slug AS on_wall_of, p.body, p.created_at FROM fan_posts p
        JOIN athlete_profiles a ON a.id = p.athlete_id WHERE p.user_id = ?""", (uid,))
    for t in rows(conn, "SELECT * FROM conversations WHERE user_a = ? OR user_b = ?", (uid, uid)):
        other_id = t["user_b"] if t["user_a"] == uid else t["user_a"]
        other = row(conn, "SELECT display_name, role FROM users WHERE id = ?", (other_id,))
        out["conversations"].append({
            "with": other, "opened_at": t["created_at"],
            "messages": [{"mine": m["sender_id"] == uid, "body": m["body"], "at": m["created_at"]}
                         for m in rows(conn, "SELECT * FROM messages WHERE conversation_id = ?"
                                             " ORDER BY id", (t["id"],))],
        })
    out["notifications"] = rows(conn, "SELECT kind, title, body, link, created_at, read_at"
                                      " FROM notifications WHERE user_id = ? ORDER BY id", (uid,))
    out["emails_owed"] = rows(conn, "SELECT subject, body, kind, created_at, sent_at FROM email_outbox"
                                    " WHERE to_user_id = ? ORDER BY id", (uid,))
    out["audit_trail"] = rows(conn, "SELECT ts, actor, event_type, detail_json FROM events"
                                    " WHERE object_type = 'user' AND object_id = ? ORDER BY id", (uid,))
    log_event(conn, "user", "user.exported", "user", uid, {})
    conn.commit()
    return out


class DeleteIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    # the word the person typed to confirm; the client asks for it, the server
    # checks it, so a stray request with a stolen cookie is not enough
    confirm: str = Field(min_length=1, max_length=40)


@router.post("/delete")
def delete_account(body: DeleteIn, response: Response, user: dict = Depends(current_user),
                   conn: sqlite3.Connection = Depends(get_db)):
    """Erase the person; keep the ledger.

    Anonymisation rather than a row DELETE, for two reasons that are the same
    reason: foreign keys from deals and commitments must keep resolving, and
    those records are exactly the ones a legal duty says to retain -- with the
    name gone. Everything that only ever existed because this person was here
    is removed outright.
    """
    if user["role"] == "admin":
        raise HTTPException(409, "admin_accounts_are_removed_by_another_admin")
    if body.confirm.strip().upper() != "DELETE":
        raise HTTPException(422, "confirmation_word_mismatch")
    if not user["password_hash"].startswith("pbkdf2$"):
        raise HTTPException(409, "password_managed_elsewhere")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(403, "wrong_password")

    uid = user["id"]
    when = now_iso()

    # -- relationship rows: theirs alone, so they go
    for table, col in (("follows", "user_id"), ("subscriptions", "user_id"), ("poll_votes", "user_id"),
                       ("fan_posts", "user_id"), ("notifications", "user_id"),
                       ("notifications", "actor_user_id"), ("auth_tokens", "user_id"),
                       ("email_outbox", "to_user_id")):
        conn.execute(f"DELETE FROM {table} WHERE {col} = ?", (uid,))
    # -- their side of every conversation: the words go, the thread survives
    #    for the other party, who also wrote in it
    conn.execute("UPDATE messages SET body = '[deleted]' WHERE sender_id = ?", (uid,))

    if user["role"] == "athlete":
        profile = row(conn, "SELECT * FROM athlete_profiles WHERE user_id = ?", (uid,))
        if profile:
            conn.execute("""UPDATE athlete_profiles SET display_name = 'Deleted athlete', bio = '',
                            career_highlights = '[]', avatar_url = '', cover_url = '',
                            status = 'hidden' WHERE id = ?""", (profile["id"],))
            conn.execute("DELETE FROM content_items WHERE athlete_id = ?", (profile["id"],))
            conn.execute("DELETE FROM athlete_applications WHERE athlete_id = ?", (profile["id"],))
            if profile["creatorlens_creator_id"]:
                # consent withdrawn by definition; the accounts stop feeding anything
                conn.execute("UPDATE platform_accounts SET connection_status = 'disconnected'"
                             " WHERE creator_id = ?", (profile["creatorlens_creator_id"],))
    elif user["role"] == "sponsor":
        org = row(conn, "SELECT * FROM sponsor_orgs WHERE user_id = ?", (uid,))
        if org:
            conn.execute("UPDATE sponsor_orgs SET name = 'Deleted organisation', website = ''"
                         " WHERE id = ?", (org["id"],))
            conn.execute("UPDATE campaigns SET status = 'closed' WHERE org_id = ?", (org["id"],))
            conn.execute("UPDATE package_commitments SET status = 'cancelled', cancelled_at = ?"
                         " WHERE org_id = ? AND status = 'active'", (when, org["id"]))
    elif user["role"] == "club":
        club = row(conn, "SELECT * FROM clubs WHERE user_id = ?", (uid,))
        if club:
            conn.execute("UPDATE clubs SET name = 'Deleted club', bio = '', status = 'hidden'"
                         " WHERE id = ?", (club["id"],))
            conn.execute("DELETE FROM content_items WHERE club_id = ?", (club["id"],))
            conn.execute("UPDATE club_packages SET status = 'archived' WHERE club_id = ?", (club["id"],))
            conn.execute("UPDATE club_invite_links SET revoked_at = COALESCE(revoked_at, ?)"
                         " WHERE club_id = ?", (when, club["id"]))

    # -- the account itself: no field left that names a person
    conn.execute("""UPDATE users SET email = ?, display_name = 'Deleted account',
                    password_hash = 'deleted', status = 'suspended',
                    token_version = token_version + 1, deleted_at = ? WHERE id = ?""",
                 (f"deleted-{uid}@removed.invalid", when, uid))
    log_event(conn, "user", "user.deleted", "user", uid, {"role": user["role"]})
    conn.commit()
    clear_session_cookie(response)
    return {"ok": True, "deleted_at": when,
            "retained": "deal and commitment records, with your name removed, as the Privacy Policy states"}
