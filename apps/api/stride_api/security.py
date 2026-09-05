"""Security hardening layer: rate limiting, request size limits, response headers.

Rate-limit state is in-memory per replica — correct for the current single-writer
deployment; move the bucket state to Redis when the API scales past one replica
(docs/architecture.html, "10k+" stage).
"""

from __future__ import annotations

import threading
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import settings
from .observability import metrics

# (burst, refill per second) — auth is strict, general API is a generous ceiling
AUTH_BURST, AUTH_REFILL = 20, 0.1   # ~6 credential attempts/min sustained per IP
API_BURST, API_REFILL = 300, 5.0


class _Buckets:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._state: dict[str, tuple[float, float]] = {}

    def allow(self, key: str, burst: float, refill: float) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._state.get(key, (burst, now))
            tokens = min(burst, tokens + (now - last) * refill)
            if tokens < 1:
                self._state[key] = (tokens, now)
                return False
            self._state[key] = (tokens - 1, now)
            return True


buckets = _Buckets()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/api"):
            ip = request.client.host if request.client else "unknown"
            if path.startswith(("/api/auth/login", "/api/auth/register",
                                "/api/auth/forgot", "/api/auth/reset", "/api/auth/password")):
                allowed = buckets.allow(f"auth:{ip}", AUTH_BURST, AUTH_REFILL)
            else:
                allowed = buckets.allow(f"api:{ip}", API_BURST, API_REFILL)
            if not allowed:
                metrics.rate_limited += 1
                return JSONResponse({"detail": "rate_limited"}, status_code=429,
                                    headers={"Retry-After": "30"})
        return await call_next(request)


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        # Uploads are the one route that is meant to be large, and they carry
        # their own ceiling. Everything else keeps the tight one.
        limit = settings.max_upload_bytes             if request.url.path.startswith("/api/media") else settings.max_body_bytes
        if content_length and content_length.isdigit() and int(content_length) > limit:
            return JSONResponse({"detail": "payload_too_large"}, status_code=413)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        h = response.headers
        h.setdefault("X-Content-Type-Options", "nosniff")
        h.setdefault("X-Frame-Options", "DENY")
        h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        h.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.path.startswith("/api"):
            # API responses are pure JSON; lock content sources completely.
            # (/docs keeps its own defaults — Swagger UI loads assets.)
            h.setdefault("Content-Security-Policy", "default-src 'none'")
        if settings.env not in ("dev", "test"):
            h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
