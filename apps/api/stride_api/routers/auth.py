"""Registration, login, session. Roles are chosen at signup; RBAC everywhere else."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from creatorlens.actions import create_creator
from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator

from .. import supabase_auth
from ..auth import (clear_session_cookie, current_user, get_db, hash_password,
                    issue_token, set_session_cookie, verify_password)
from ..config import settings
from ..db import now_iso, row

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email_shape(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1] or len(v) < 6:
            raise ValueError("invalid email")
        return v
    display_name: str = Field(min_length=2, max_length=80)
    role: str  # athlete | sponsor | fan | club
    # role-specific onboarding fields
    sport: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    org_name: str | None = Field(default=None, max_length=120)
    industry: str | None = Field(default=None, max_length=80)
    # Contract formation. The client sends the version of the documents it
    # showed; the server records it against the account. A registration
    # without acceptance is refused rather than defaulted -- a default here
    # would be the product agreeing to its own terms on the person's behalf.
    accept_terms: bool = False
    policy_version: str = Field(default="", max_length=40)


class ForgotIn(BaseModel):
    email: str = Field(max_length=254)


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class VerifyIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class PasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class EmailIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    new_email: str = Field(max_length=254)

    @field_validator("new_email")
    @classmethod
    def _email_shape(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1] or len(v) < 6:
            raise ValueError("invalid email")
        return v


# ── one-time tokens ──────────────────────────────────────────────────────────

TOKEN_TTL = {"verify_email": timedelta(days=3), "reset_password": timedelta(hours=2)}


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_one_time_token(conn, user_id: int, purpose: str) -> str:
    """Mint a token, store only its hash, and retire any earlier token of the
    same purpose for this person -- the newest link is the only one that works,
    so a stale reset email in an old inbox is not a second way in."""
    conn.execute("UPDATE auth_tokens SET used_at = ? WHERE user_id = ? AND purpose = ?"
                 " AND used_at IS NULL", (now_iso(), user_id, purpose))
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + TOKEN_TTL[purpose]).strftime("%Y-%m-%dT%H:%M:%SZ")
    conn.execute("INSERT INTO auth_tokens (user_id, purpose, token_hash, created_at, expires_at)"
                 " VALUES (?, ?, ?, ?, ?)", (user_id, purpose, _hash(token), now_iso(), expires))
    return token


def consume_one_time_token(conn, token: str, purpose: str) -> dict:
    """Look a token up by hash and burn it. Every failure is the same 400 --
    expired, used, wrong purpose, never issued -- because distinguishing them
    tells an attacker which of their guesses was once real."""
    found = row(conn, "SELECT * FROM auth_tokens WHERE token_hash = ? AND purpose = ?",
                (_hash(token), purpose))
    if found is None or found["used_at"] is not None or found["expires_at"] <= now_iso():
        raise HTTPException(400, "invalid_or_expired_token")
    conn.execute("UPDATE auth_tokens SET used_at = ? WHERE id = ?", (now_iso(), found["id"]))
    return row(conn, "SELECT * FROM users WHERE id = ?", (found["user_id"],))


def queue_plain_email(conn, to_email: str, user_id: int | None, subject: str,
                      lines: list[str], kind: str) -> None:
    conn.execute("INSERT INTO email_outbox (to_email, to_user_id, subject, body, kind, created_at)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (to_email, user_id, subject, "\n\n".join([*lines, "-- Stride"]), kind, now_iso()))


def queue_auth_email(conn, user: dict, purpose: str, token: str) -> None:
    """Write the email into the outbox. Nothing sends -- see email_outbox --
    but the row carries the exact link the person would receive, so in this
    build an admin reads it from the outbox and the flow is testable end to end."""
    if purpose == "verify_email":
        subject = "Confirm your email for Stride"
        link = f"{settings.public_url}/verify?token={token}"
        lines = [f"Hi {user['display_name']},",
                 "Confirm this is your address and your account is complete:",
                 link,
                 "The link works once and for three days. If you did not create a Stride"
                 " account, ignore this and nothing happens."]
    else:
        subject = "Reset your Stride password"
        link = f"{settings.public_url}/reset?token={token}"
        lines = [f"Hi {user['display_name']},",
                 "Somebody -- hopefully you -- asked to reset the password on this account:",
                 link,
                 "The link works once and for two hours. If you did not ask for this, ignore"
                 " it; your password has not changed."]
    lines.append("-- Stride")
    conn.execute("INSERT INTO email_outbox (to_email, to_user_id, subject, body, kind, created_at)"
                 " VALUES (?, ?, ?, ?, ?, ?)",
                 (user["email"], user["id"], subject, "\n\n".join(lines), f"auth.{purpose}", now_iso()))


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=128)


def _slugify(name: str, conn: sqlite3.Connection) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    slug, n = base, 2
    while row(conn, "SELECT id FROM athlete_profiles WHERE slug = ?", (slug,)):
        slug = f"{base}-{n}"
        n += 1
    return slug


def _club_slug(name: str, conn: sqlite3.Connection) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    slug, n = base, 2
    while row(conn, "SELECT id FROM clubs WHERE slug = ?", (slug,)):
        slug = f"{base}-{n}"
        n += 1
    return slug


@router.post("/register", status_code=201)
def register(body: RegisterIn, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    if body.role not in ("athlete", "sponsor", "fan", "club"):
        raise HTTPException(422, "invalid_role")
    if row(conn, "SELECT id FROM users WHERE email = ?", (body.email,)):
        raise HTTPException(409, "email_exists")
    if not body.accept_terms:
        raise HTTPException(422, "terms_not_accepted")

    # Supabase is the credential authority when configured; the local row keeps
    # role + profile linkage and never stores a password in that case.
    auth_id, needs_confirmation = None, False
    if settings.supabase_enabled:
        supa = supabase_auth.signup(body.email, body.password)
        auth_id = supa["auth_id"]
        needs_confirmation = not supa["confirmed"]
        password_hash = "supabase"
    else:
        password_hash = hash_password(body.password)

    accepted_version = body.policy_version or settings.legal_policy_version
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, role, display_name, auth_id, created_at,"
        " accepted_policy_version, accepted_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (body.email, password_hash, body.role, body.display_name, auth_id, now_iso(),
         accepted_version, now_iso()))
    user_id = cur.lastrowid
    log_event(conn, "user", "user.registered", "user", user_id,
              {"email": body.email, "role": body.role, "accepted_policy_version": accepted_version})
    # The verification email is owed the moment the address is claimed. Local
    # accounts only: with Supabase configured, its own confirmation email is
    # the one that counts.
    if not settings.supabase_enabled:
        token = issue_one_time_token(conn, user_id, "verify_email")
        queue_auth_email(conn, {"id": user_id, "email": body.email,
                                "display_name": body.display_name}, "verify_email", token)

    if body.role == "athlete":
        slug = _slugify(body.display_name, conn)
        creator = create_creator(conn, handle=slug, display_name=body.display_name,
                                 primary_topic="fitness", actor="user")
        conn.execute(
            "INSERT INTO athlete_profiles (user_id, slug, display_name, sport, country, region,"
            " status, creatorlens_creator_id, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'draft', ?, ?)",
            (user_id, slug, body.display_name, body.sport or "Unspecified",
             body.country or "Unspecified", "Global", creator["id"], now_iso()))
    elif body.role == "sponsor":
        conn.execute(
            "INSERT INTO sponsor_orgs (user_id, name, industry, regions, created_at)"
            " VALUES (?, ?, ?, '[]', ?)",
            (user_id, body.org_name or f"{body.display_name} & Co",
             body.industry or "Sportswear", now_iso()))
    elif body.role == "club":
        club_name = body.org_name or f"{body.display_name} Club"
        conn.execute(
            "INSERT INTO clubs (user_id, slug, name, sport, country, region, status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, 'draft', ?)",
            (user_id, _club_slug(club_name, conn), club_name,
             body.sport or "Unspecified", body.country or "Unspecified", "Global", now_iso()))
    conn.commit()

    user = row(conn, "SELECT * FROM users WHERE id = ?", (user_id,))
    if needs_confirmation:
        # no session yet — Supabase sent a confirmation email; sign in after confirming
        return {**_me(user, conn), "needs_email_confirmation": True}
    set_session_cookie(response, issue_token(user))
    return _me(user, conn)


@router.post("/login")
def login(body: LoginIn, response: Response, conn: sqlite3.Connection = Depends(get_db)):
    user = row(conn, "SELECT * FROM users WHERE email = ?", (body.email,))
    if user is None:
        raise HTTPException(401, "invalid_credentials")
    if user["password_hash"].startswith("pbkdf2$"):
        # local account (seeded/demo, or created before Supabase was wired)
        if not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "invalid_credentials")
    elif settings.supabase_enabled:
        supabase_auth.verify_password(body.email, body.password)  # raises 401/403
    else:
        raise HTTPException(401, "invalid_credentials")
    if user["status"] != "active":
        raise HTTPException(403, "account_suspended")
    log_event(conn, "user", "user.logged_in", "user", user["id"], {"email": user["email"]})
    conn.commit()
    set_session_cookie(response, issue_token(user))
    return _me(user, conn)


@router.post("/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.post("/logout-all")
def logout_all(response: Response, user: dict = Depends(current_user),
               conn: sqlite3.Connection = Depends(get_db)):
    """Revoke every session for this account (stolen-cookie response)."""
    conn.execute("UPDATE users SET token_version = token_version + 1 WHERE id = ?", (user["id"],))
    log_event(conn, "user", "user.sessions_revoked", "user", user["id"], {})
    conn.commit()
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(current_user), conn: sqlite3.Connection = Depends(get_db)):
    return _me(user, conn)


# ── email verification ───────────────────────────────────────────────────────

@router.post("/verify-email")
def verify_email(body: VerifyIn, conn: sqlite3.Connection = Depends(get_db)):
    """No session required: the person may be opening the link on a different
    device from the one they registered on."""
    user = consume_one_time_token(conn, body.token, "verify_email")
    # The same link does both jobs, because they are the same job: prove an
    # address is yours. Which address is whichever one is waiting.
    moving_to = user.get("pending_email")
    if moving_to and not row(conn, "SELECT id FROM users WHERE email = ? AND id <> ?",
                             (moving_to, user["id"])):
        conn.execute("UPDATE users SET email = ?, pending_email = NULL, email_verified_at = ?"
                     " WHERE id = ?", (moving_to, now_iso(), user["id"]))
        log_event(conn, "user", "user.email_changed", "user", user["id"], {})
    else:
        conn.execute("UPDATE users SET email_verified_at = COALESCE(email_verified_at, ?),"
                     " pending_email = NULL WHERE id = ?", (now_iso(), user["id"]))
        log_event(conn, "user", "user.email_verified", "user", user["id"], {})
    conn.commit()
    fresh = row(conn, "SELECT email FROM users WHERE id = ?", (user["id"],))
    return {"ok": True, "email": fresh["email"]}


@router.post("/email")
def change_email(body: EmailIn, user: dict = Depends(current_user),
                 conn: sqlite3.Connection = Depends(get_db)):
    """Ask to move the account to another address.

    The live address does not change here. A typo that took effect immediately
    would lock the account out of its own recovery: a reset link would go to an
    inbox nobody reads, and password reset is the only way back. So the new
    address is held as `pending_email`, the confirmation link goes *to it*, and
    only opening that link moves the account.

    The old address is told, separately and immediately. Somebody who has taken
    a session should not be able to walk the account away in silence -- the
    notice is what makes that visible to the person who owns it.
    """
    if not user["password_hash"].startswith("pbkdf2$"):
        raise HTTPException(409, "password_managed_elsewhere")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(403, "wrong_password")
    if body.new_email == user["email"]:
        raise HTTPException(409, "same_email")
    if row(conn, "SELECT id FROM users WHERE email = ? AND id <> ?", (body.new_email, user["id"])):
        raise HTTPException(409, "email_exists")

    conn.execute("UPDATE users SET pending_email = ? WHERE id = ?", (body.new_email, user["id"]))
    token = issue_one_time_token(conn, user["id"], "verify_email")
    queue_auth_email(conn, {**user, "email": body.new_email}, "verify_email", token)
    queue_plain_email(
        conn, user["email"], user["id"], "Your Stride address was asked to change",
        [f"Hi {user['display_name']},",
         f"Somebody asked to move this account to {body.new_email}. Nothing has changed yet -- "
         "the move only happens when that address confirms it.",
         "If this was not you, change your password now: whoever asked had your current one."],
        "auth.email_change_notice")
    log_event(conn, "user", "user.email_change_requested", "user", user["id"], {})
    conn.commit()
    return {"ok": True, "pending_email": body.new_email}


@router.post("/resend-verification")
def resend_verification(user: dict = Depends(current_user),
                        conn: sqlite3.Connection = Depends(get_db)):
    if user.get("email_verified_at"):
        return {"ok": True, "already_verified": True}
    token = issue_one_time_token(conn, user["id"], "verify_email")
    queue_auth_email(conn, user, "verify_email", token)
    conn.commit()
    return {"ok": True, "already_verified": False}


# ── password reset ───────────────────────────────────────────────────────────

@router.post("/forgot")
def forgot_password(body: ForgotIn, conn: sqlite3.Connection = Depends(get_db)):
    """Always 200, always the same body. Whether an address has an account is
    not something this endpoint will tell a stranger. The work happens only
    for a real, local account; the response does not vary."""
    email = body.email.strip().lower()
    user = row(conn, "SELECT * FROM users WHERE email = ?", (email,))
    if user is not None and user["password_hash"].startswith("pbkdf2$") and user["status"] == "active":
        token = issue_one_time_token(conn, user["id"], "reset_password")
        queue_auth_email(conn, user, "reset_password", token)
        log_event(conn, "user", "user.password_reset_requested", "user", user["id"], {})
        conn.commit()
    return {"ok": True}


@router.post("/reset")
def reset_password(body: ResetIn, response: Response,
                   conn: sqlite3.Connection = Depends(get_db)):
    user = consume_one_time_token(conn, body.token, "reset_password")
    # A reset is a stolen-cookie response as much as a forgotten-password one:
    # every existing session dies with the old password, and the person is
    # signed in fresh on this device.
    conn.execute("UPDATE users SET password_hash = ?, token_version = token_version + 1,"
                 " email_verified_at = COALESCE(email_verified_at, ?) WHERE id = ?",
                 (hash_password(body.password), now_iso(), user["id"]))
    log_event(conn, "user", "user.password_reset", "user", user["id"], {})
    conn.commit()
    user = row(conn, "SELECT * FROM users WHERE id = ?", (user["id"],))
    set_session_cookie(response, issue_token(user))
    return _me(user, conn)


@router.post("/password")
def change_password(body: PasswordIn, response: Response, user: dict = Depends(current_user),
                    conn: sqlite3.Connection = Depends(get_db)):
    if not user["password_hash"].startswith("pbkdf2$"):
        raise HTTPException(409, "password_managed_elsewhere")
    if not verify_password(body.current_password, user["password_hash"]):
        raise HTTPException(403, "wrong_password")
    conn.execute("UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?",
                 (hash_password(body.new_password), user["id"]))
    log_event(conn, "user", "user.password_changed", "user", user["id"], {})
    conn.commit()
    # other sessions are gone with the version bump; this one continues
    fresh = row(conn, "SELECT * FROM users WHERE id = ?", (user["id"],))
    set_session_cookie(response, issue_token(fresh))
    return {"ok": True}


def _me(user: dict, conn: sqlite3.Connection) -> dict:
    out = {"id": user["id"], "email": user["email"], "role": user["role"],
           "display_name": user["display_name"],
           "email_verified": bool(user.get("email_verified_at")),
           "pending_email": user.get("pending_email"),
           "accepted_policy_version": user.get("accepted_policy_version")}
    if user["role"] == "athlete":
        profile = row(conn, "SELECT id, slug, status FROM athlete_profiles WHERE user_id = ?",
                      (user["id"],))
        out["athlete_profile"] = profile
    elif user["role"] == "sponsor":
        out["org"] = row(conn, "SELECT id, name, industry FROM sponsor_orgs WHERE user_id = ?",
                         (user["id"],))
    elif user["role"] == "club":
        out["club"] = row(conn, "SELECT id, slug, name, status FROM clubs WHERE user_id = ?",
                          (user["id"],))
    return out
