"""Observability: structured JSON logs, request IDs, Prometheus-format metrics.

The three pillars, sized for a first draft:
  logs    — one JSON line per request (and app events), machine-parseable,
            request_id correlates everything a request touched
  metrics — hand-rolled Prometheus text format at /metrics: request counts,
            latency histogram, error counts; scrape-ready (infra/k8s)
  traces  — request_id doubles as the trace correlation key; a real tracer
            (OpenTelemetry) slots into the same middleware later
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
import uuid
from collections import defaultdict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("request_id", "method", "path", "status", "duration_ms", "user_id", "role"):
            if hasattr(record, key):
                entry[key] = getattr(record, key)
        if record.exc_info:
            entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True  # replaced by our request log


# ---- metrics registry (Prometheus text format, no dependency) ---------------

_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests: dict[tuple[str, str, int], int] = defaultdict(int)   # (method, route, status)
        self.latency_buckets: dict[tuple[str, float], int] = defaultdict(int)
        self.latency_sum: dict[str, float] = defaultdict(float)
        self.latency_count: dict[str, int] = defaultdict(int)
        self.chaos_injected: int = 0
        self.rate_limited: int = 0

    def observe(self, method: str, route: str, status: int, seconds: float) -> None:
        with self._lock:
            self.requests[(method, route, status)] += 1
            self.latency_sum[route] += seconds
            self.latency_count[route] += 1
            for b in _LATENCY_BUCKETS:
                if seconds <= b:
                    self.latency_buckets[(route, b)] += 1

    def render(self) -> str:
        lines = [
            "# HELP stride_http_requests_total HTTP requests by method, route, status",
            "# TYPE stride_http_requests_total counter",
        ]
        with self._lock:
            for (method, route, status), n in sorted(self.requests.items()):
                lines.append(f'stride_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {n}')
            lines += [
                "# HELP stride_http_request_duration_seconds Request latency",
                "# TYPE stride_http_request_duration_seconds histogram",
            ]
            for route in sorted(self.latency_count):
                cumulative = 0
                for b in _LATENCY_BUCKETS:
                    cumulative += self.latency_buckets.get((route, b), 0)
                    lines.append(
                        f'stride_http_request_duration_seconds_bucket{{route="{route}",le="{b}"}} {cumulative}')
                lines.append(
                    f'stride_http_request_duration_seconds_bucket{{route="{route}",le="+Inf"}} {self.latency_count[route]}')
                lines.append(f'stride_http_request_duration_seconds_sum{{route="{route}"}} {self.latency_sum[route]:.6f}')
                lines.append(f'stride_http_request_duration_seconds_count{{route="{route}"}} {self.latency_count[route]}')
            lines += [
                "# HELP stride_chaos_injected_total Failures injected by the chaos layer",
                "# TYPE stride_chaos_injected_total counter",
                f"stride_chaos_injected_total {self.chaos_injected}",
                "# HELP stride_rate_limited_total Requests rejected by the rate limiter",
                "# TYPE stride_rate_limited_total counter",
                f"stride_rate_limited_total {self.rate_limited}",
            ]
        return "\n".join(lines) + "\n"


metrics = Metrics()
request_logger = logging.getLogger("stride.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Request ID + timing + one structured log line + metrics per request."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            metrics.observe(request.method, request.url.path, 500, duration)
            request_logger.error(
                "unhandled exception", exc_info=True,
                extra={"request_id": request_id, "method": request.method,
                       "path": request.url.path, "status": 500,
                       "duration_ms": round(duration * 1000, 1)},
            )
            raise
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        metrics.observe(request.method, route_path, response.status_code, duration)
        request_logger.info(
            "request", extra={"request_id": request_id, "method": request.method,
                              "path": request.url.path, "status": response.status_code,
                              "duration_ms": round(duration * 1000, 1)},
        )
        response.headers["x-request-id"] = request_id
        return response
