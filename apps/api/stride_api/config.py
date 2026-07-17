"""Environment-driven configuration. Every value has a safe dev default;
production overrides via env (see infra/k8s/configmap.yaml).

A `.env` file at the project root (or apps/api/) is loaded first — that's where
the Supabase project keys live (see SUPABASE.md). Values already present in the
real environment always win over .env.
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_dotenv() -> None:
    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[1] / ".env"):
        if candidate.exists():
            for line in candidate.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class Settings:
    def __init__(self) -> None:
        _load_dotenv()
        self.env = os.environ.get("STRIDE_ENV", "dev")
        self.db_path = Path(os.environ.get("STRIDE_DB", "")) if os.environ.get("STRIDE_DB") \
            else Path.cwd() / "data" / "stride.db"
        # Dev default only — outside dev/test the process refuses to boot without a real secret.
        self.secret_key = os.environ.get("STRIDE_SECRET", "dev-secret-not-for-production")
        if self.env not in ("dev", "test") and self.secret_key == "dev-secret-not-for-production":
            raise RuntimeError(
                "STRIDE_SECRET must be set to a strong random value outside dev"
                " (e.g. `openssl rand -hex 32`); refusing to start.")
        self.token_ttl_hours = int(os.environ.get("STRIDE_TOKEN_TTL_HOURS", "12"))
        self.max_body_bytes = int(os.environ.get("STRIDE_MAX_BODY_BYTES", "262144"))  # 256 KiB
        self.cookie_name = "stride_session"
        self.cookie_secure = self.env not in ("dev", "test")
        self.cors_origins = [
            o.strip() for o in os.environ.get(
                "STRIDE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",") if o.strip()
        ]
        self.chaos_enabled = os.environ.get("STRIDE_CHAOS", "1") == "1"  # off in prod

        # Supabase Auth (identity provider). When both are set, registration and
        # login verify credentials against Supabase; local PBKDF2 remains the
        # fallback for pre-existing (seeded/demo) accounts.
        self.supabase_url = os.environ.get("STRIDE_SUPABASE_URL", "").rstrip("/")
        self.supabase_anon_key = os.environ.get("STRIDE_SUPABASE_ANON_KEY", "")

        # Data backend. Set STRIDE_DATABASE_URL to a Postgres DSN (Supabase, RDS,
        # local docker) to run on Postgres; unset -> SQLite file at db_path.
        self.database_url = os.environ.get("STRIDE_DATABASE_URL", "")

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_anon_key)

    @property
    def db_backend(self) -> str:
        return "postgres" if self.database_url else "sqlite"


settings = Settings()
