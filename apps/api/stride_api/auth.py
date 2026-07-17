"""Auth: PBKDF2 password hashing, JWT sessions in an httpOnly cookie, RBAC deps.

Designed to be swapped for Supabase Auth later: the users table mirrors the
auth.users + profile-role pattern, and every route guards with require_role(),
which maps 1:1 onto Supabase RLS policies (infra/supabase/migrations).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, Response

from .config import settings
from .db import connect, row

PBKDF2_ITERATIONS = 300_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS)
    return f"pbkdf2${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iters))
        return hmac.compare_digest(digest.hex(), expected)
    except (ValueError, TypeError):
        return False


def issue_token(user: dict) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user["id"]), "role": user["role"], "name": user["display_name"],
         "ver": user.get("token_version", 1),  # bump users.token_version -> all sessions die
         "iat": now, "exp": now + timedelta(hours=settings.token_ttl_hours)},
        settings.secret_key, algorithm="HS256",
    )


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.cookie_name, token,
        httponly=True, samesite="lax", secure=settings.cookie_secure,
        max_age=settings.token_ttl_hours * 3600, path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.cookie_name, path="/")


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def current_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(401, "not_authenticated")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid_session")
    user = row(conn, "SELECT * FROM users WHERE id = ?", (int(payload["sub"]),))
    if user is None or user["status"] != "active":
        raise HTTPException(401, "account_unavailable")
    if payload.get("ver") != user["token_version"]:
        raise HTTPException(401, "session_revoked")
    return user


def optional_user(request: Request, conn: sqlite3.Connection = Depends(get_db)) -> dict | None:
    try:
        return current_user(request, conn)
    except HTTPException:
        return None


def require_role(*roles: str):
    def guard(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(403, f"requires_role:{'|'.join(roles)}")
        return user
    return guard
