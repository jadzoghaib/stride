"""Stride API application: middleware stack, routers, probes, metrics."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from . import __version__
from .chaos import ChaosMiddleware, chaos
from .config import settings
from .db import connect, init_db
from .observability import RequestContextMiddleware, configure_logging, metrics
from .routers import (account, admin, safety, admission, athletes, auth, clubs, content, discover, media, meta,
                      messaging, sponsors)
from .security import BodySizeLimitMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from .seed import is_seeded, seed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    conn = connect()
    init_db(conn)
    if not is_seeded(conn):
        seed(conn)
    conn.close()
    yield


app = FastAPI(title="Stride API", version=__version__, lifespan=lifespan)

# Middleware stack, innermost first (Starlette wraps in reverse order):
# routes <- request log/metrics <- chaos <- body limit <- rate limit <- headers <- CORS <- proxy headers
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ChaosMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Outermost, so the rate limiter and the request log see the real client
# address rather than the ingress. Trusts nothing unless configured -- see
# `forwarded_allow_ips` in config.py for why that default matters.
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=settings.forwarded_allow_ips)

app.include_router(meta.router)
app.include_router(auth.router)
app.include_router(account.router)
app.include_router(safety.router)
app.include_router(athletes.router)
app.include_router(sponsors.router)
app.include_router(clubs.router)
app.include_router(discover.router)
app.include_router(admin.router)
app.include_router(admission.router)
app.include_router(content.router)
app.include_router(messaging.router)
app.include_router(media.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Unhandled errors return a stable JSON shape with the request id for
    support correlation — never a stack trace or framework default page.
    (The request-context middleware has already logged the exception.)"""
    return JSONResponse(
        {"detail": "internal_error",
         "request_id": getattr(request.state, "request_id", None)},
        status_code=500,
    )


@app.get("/healthz", tags=["ops"])
def healthz():
    """Liveness: the process is up. Kubernetes restarts the pod if this fails."""
    return {"status": "ok", "version": __version__}


@app.get("/readyz", tags=["ops"])
def readyz():
    """Readiness: dependencies reachable. Kubernetes stops routing if this fails.
    The chaos db_down mode fails this probe on purpose (see docs/runbook.md)."""
    if chaos.db_down:
        return PlainTextResponse('{"status":"degraded","reason":"database_unreachable"}',
                                 status_code=503, media_type="application/json")
    try:
        conn = connect()
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        return PlainTextResponse('{"status":"degraded","reason":"database_error"}',
                                 status_code=503, media_type="application/json")
    return {"status": "ready"}


@app.get("/metrics", tags=["ops"])
def prometheus_metrics():
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")


# ── the single-container demo ───────────────────────────────────────────────
#
# When `STRIDE_WEB_DIST` points at a Vite build, this process serves the client
# as well as the API. Nothing changes for local development, where the front end
# runs under Vite and this variable is unset.
#
# The point is deployment cost. Two containers means two instances and a private
# network between them, which on a managed platform is two paid services and an
# upstream address wired by hand. One container is one free instance and no
# cross-service configuration to get wrong.
#
# Registered last, on purpose: every router above is matched first, so the
# catch-all can only ever see paths nothing else claimed.
_web_dist = os.environ.get("STRIDE_WEB_DIST", "").strip()
if _web_dist and Path(_web_dist).is_dir():
    _dist = Path(_web_dist)
    _index = _dist / "index.html"

    # Hashed filenames, so they can be cached hard. index.html cannot be.
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{spa_path:path}", include_in_schema=False)
    def spa(spa_path: str):
        """Client routes resolve to index.html; everything else stays honest.

        A blanket catch-all would answer `/api/does-not-exist` with the HTML
        shell and a 200, turning every client-side typo into a parse error
        somewhere far from the cause. API paths that reach here are genuinely
        missing and say so.
        """
        # The bare word too, not just the prefix: `GET /api` does not start
        # with "api/", so it fell through and answered the HTML shell with a
        # 200 -- the exact confusion this guard exists to prevent.
        reserved = ("api", "healthz", "readyz", "metrics")
        if spa_path in reserved or spa_path.startswith(tuple(f"{r}/" for r in reserved)):
            raise HTTPException(404, "not_found")
        # A real file (favicon, manifest, an image) is served as itself; anything
        # else is a route the client router owns.
        candidate = (_dist / spa_path).resolve()
        if spa_path and candidate.is_file() and _dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_index)
