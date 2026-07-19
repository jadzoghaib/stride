"""Registration, login, session. Roles are chosen at signup; RBAC everywhere else."""

from __future__ import annotations

import sqlite3

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

    cur = conn.execute(
        "INSERT INTO users (email, password_hash, role, display_name, auth_id, created_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (body.email, password_hash, body.role, body.display_name, auth_id, now_iso()))
    user_id = cur.lastrowid
    log_event(conn, "user", "user.registered", "user", user_id,
              {"email": body.email, "role": body.role})

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


def _me(user: dict, conn: sqlite3.Connection) -> dict:
    out = {"id": user["id"], "email": user["email"], "role": user["role"],
           "display_name": user["display_name"]}
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
