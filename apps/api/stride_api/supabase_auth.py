"""Supabase Auth (GoTrue) client — identity provider integration.

Stride uses Supabase as the credential authority when configured: sign-up and
password verification happen against the Supabase project (real email
confirmation, password reset via the Supabase dashboard settings), while the
app keeps issuing its own short-lived session cookie after Supabase says yes.
Only the publishable (anon) key is used here — never the service role key.

Data migration to Supabase Postgres is a separate step (SUPABASE.md).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from fastapi import HTTPException

from .config import settings

logger = logging.getLogger("stride.supabase")
TIMEOUT_S = 10


def _call(path: str, body: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{settings.supabase_url}{path}",
        method="POST",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        data=json.dumps(body).encode(),
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except json.JSONDecodeError:
            return exc.code, {}
    # a network failure to the identity provider is a 502, not a 401 —
    # never report "wrong password" for an outage
    except (urllib.error.URLError, TimeoutError) as exc:
        logger.error("supabase unreachable: %s", exc)
        raise HTTPException(502, "identity_provider_unreachable")


def _error_text(data: dict) -> str:
    return str(data.get("error_description") or data.get("msg")
               or data.get("message") or data.get("error_code") or "").lower()


def signup(email: str, password: str) -> dict:
    """Returns {auth_id, confirmed}. Raises 409 on existing account."""
    status, data = _call("/auth/v1/signup", {"email": email, "password": password})
    if status >= 400:
        text = _error_text(data)
        if "already" in text or data.get("error_code") == "user_already_exists":
            raise HTTPException(409, "email_exists")
        logger.warning("supabase signup rejected: %s", text)
        raise HTTPException(422, f"identity_provider_rejected:{text[:80]}")
    user = data.get("user") or data  # shape differs with/without auto-confirm
    auth_id = user.get("id")
    # repeated signup for an existing confirmed user returns an obfuscated
    # user object with empty identities — treat as already registered
    if user.get("identities") == []:
        raise HTTPException(409, "email_exists")
    confirmed = bool(data.get("access_token")) or bool(user.get("email_confirmed_at"))
    return {"auth_id": auth_id, "confirmed": confirmed}


def verify_password(email: str, password: str) -> dict:
    """Password grant. Returns {auth_id}. Raises 401/403 with a stable reason."""
    status, data = _call("/auth/v1/token?grant_type=password", {"email": email, "password": password})
    if status >= 400:
        text = _error_text(data)
        if "not confirmed" in text or data.get("error_code") == "email_not_confirmed":
            raise HTTPException(403, "email_not_confirmed")
        raise HTTPException(401, "invalid_credentials")
    return {"auth_id": (data.get("user") or {}).get("id")}
