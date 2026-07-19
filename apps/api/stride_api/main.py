"""Stride API application: middleware stack, routers, probes, metrics."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from . import __version__
from .chaos import ChaosMiddleware, chaos
from .config import settings
from .db import connect, init_db
from .observability import RequestContextMiddleware, configure_logging, metrics
from .routers import admin, athletes, auth, clubs, discover, sponsors
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
# routes <- request log/metrics <- chaos <- body limit <- rate limit <- headers <- CORS
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

app.include_router(auth.router)
app.include_router(athletes.router)
app.include_router(sponsors.router)
app.include_router(clubs.router)
app.include_router(discover.router)
app.include_router(admin.router)


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
