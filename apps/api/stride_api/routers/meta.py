"""What the client needs to know before anyone is signed in.

One public, unauthenticated endpoint. It exists because the front end otherwise
has to guess: a deployment with registration closed would still draw a "Create
account" tab, and the only way to discover the policy would be to fill the form
in and be refused. An error a client could have avoided is a design fault, not
an error message.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..config import settings

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta")
def meta() -> dict:
    """Public deployment facts. No auth, no personal data, safe to cache briefly."""
    return {
        "signup_open": settings.allow_signup,
        # Whether this deployment ships the seeded demo accounts, which is a
        # different question from whether registration is open -- and became a
        # visibly different one when signup opened while the sign-in page went
        # on listing them. Tied to the signup flag it would now report `false`
        # about credentials the page is still showing.
        "demo_accounts": settings.demo_accounts,
        "policy_version": settings.legal_policy_version,
    }
