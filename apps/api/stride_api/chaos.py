"""Chaos layer — controlled failure injection for resilience drills.

Enabled only when STRIDE_CHAOS=1 (dev default; off in production manifests).
Modes, settable by an admin at runtime:
  latency_ms  — add N ms to every API response (slow dependency simulation)
  error_rate  — fail this fraction of API requests with 503 (flaky upstream)
  db_down     — /readyz starts failing (Kubernetes stops routing to the pod)

The drill script (scripts/failure_drill.py) exercises each mode and verifies
recovery; docs/runbook.md documents the expected operator response.
"""

from __future__ import annotations

import asyncio
import random

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .observability import metrics


class ChaosState:
    def __init__(self) -> None:
        self.latency_ms: int = 0
        self.error_rate: float = 0.0
        self.db_down: bool = False

    def as_dict(self) -> dict:
        return {"latency_ms": self.latency_ms, "error_rate": self.error_rate, "db_down": self.db_down}

    def reset(self) -> None:
        self.latency_ms = 0
        self.error_rate = 0.0
        self.db_down = False


chaos = ChaosState()


class ChaosMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # never sabotage the probes or the chaos controls themselves
        if path.startswith("/api") and not path.startswith("/api/admin/chaos"):
            if chaos.latency_ms:
                await asyncio.sleep(chaos.latency_ms / 1000)
            if chaos.error_rate and random.random() < chaos.error_rate:
                metrics.chaos_injected += 1
                return JSONResponse({"detail": "chaos_injected_failure"}, status_code=503)
        return await call_next(request)
