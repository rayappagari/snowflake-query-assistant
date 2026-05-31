"""
FastAPI application — the HTTP layer for the Snowflake Query Assistant.

Endpoints
---------
GET  /health        Liveness probe (no auth)
GET  /metrics       Prometheus metrics (no auth)
GET  /verify        Password check (legacy password mode)
POST /query         Run a question through the agent pipeline
GET  /audit         Retrieve the audit log
POST /auth/login    Obtain a JWT token
POST /auth/register Create a user (admin-only, JWT mode)
GET  /auth/me       Current user info (JWT mode)
GET  /auth/mode     Returns {"mode": "jwt"} or {"mode": "password"}

Auth modes
----------
JWT mode      DATABASE_URL is set.  All protected endpoints require
              Authorization: Bearer <token>.  Tokens are obtained via
              POST /auth/login.  Admin bootstrap via ADMIN_USERNAME +
              ADMIN_PASSWORD env vars on first startup.

Password mode DATABASE_URL is absent.  Protected endpoints require
              the X-App-Password header matching APP_PASSWORD env var.
              This preserves full backward compatibility.

Rate limiting: api/rate_limit.py — Redis-backed when REDIS_URL set.
PII scanning:  agents/pii.py    — results are scanned before returning.
Audit logging: db/audit.py      — PostgreSQL + SQLite + stdout JSON.
Metrics:       api/metrics.py   — Prometheus counters and histograms.
"""

from dotenv import load_dotenv

# Must run before any agent/db imports — clients and pool initialise at import time.
load_dotenv()

import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator import answer_question_full
from agents.pii import scan as pii_scan
from api import auth as auth_module
from api.auth import get_current_user, router as auth_router
from api.metrics import (
    CIRCUIT_STATE,
    RATE_LIMITED,
    get_metrics_response,
    record_query,
)
from api.rate_limit import limiter
from db import audit
from db.circuit_breaker import snowflake_breaker

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="Snowflake Query Assistant")

_APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
_QUERY_TIMEOUT = int(os.environ.get("QUERY_TIMEOUT_SECONDS", "120"))
_AUTH_MODE = "jwt" if os.environ.get("DATABASE_URL") else "password"

# ── Circuit-breaker state map for Prometheus gauge ────────────────────────────
_CB_STATE_MAP = {
    snowflake_breaker.CLOSED: 0,
    snowflake_breaker.HALF_OPEN: 1,
    snowflake_breaker.OPEN: 2,
}


# ── Startup event ─────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    """Bootstrap admin user when JWT mode is active."""
    auth_module.init_admin()


# ── Include routers ───────────────────────────────────────────────────────────

app.include_router(auth_router)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _check_password(x_app_password: str | None) -> None:
    """Legacy password gate — used in password mode only."""
    if _APP_PASSWORD and x_app_password != _APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")


def _check_rate_limit(request: Request) -> None:
    """Sliding-window rate-limit check.  Increments RATE_LIMITED on rejection."""
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.check(client_ip)
    if not allowed:
        RATE_LIMITED.inc()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )


# ── Models ───────────────────────────────────────────────────────────────────

class HistoryTurn(BaseModel):
    question: str
    sql: str
    answer: str


class QueryRequest(BaseModel):
    question: str
    history: list[HistoryTurn] = []


class QueryResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    error: str | None = None
    cache_hit: bool = False
    pii_detected: list[str] = []
    user: str | None = None  # username who made the query (JWT mode)


class AuditEntry(BaseModel):
    id: int
    ts: str
    question: str
    sql_generated: str | None
    success: bool
    row_count: int | None
    latency_ms: int | None
    cache_hit: bool
    pii_detected: list[str]
    error_message: str | None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    """Liveness probe. No authentication required."""
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    """
    Prometheus metrics endpoint.

    Scrape this with a Prometheus server or Grafana Agent.  No authentication
    required — add a firewall rule / network policy if you need to restrict access.
    """
    return get_metrics_response()


@app.get("/verify")
def verify(x_app_password: str | None = Header(default=None)) -> dict:
    """Validate the app password (legacy password mode). Returns 401 on mismatch."""
    _check_password(x_app_password)
    return {"ok": True}


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    request: Request,
    x_app_password: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> QueryResponse:
    """
    Run a question through the full agent pipeline.

    Auth
    ----
    JWT mode      Authorization: Bearer <token> header required.
    Password mode X-App-Password header checked against APP_PASSWORD.

    Flow
    ----
    1. Auth + rate-limit checks
    2. Pipeline (schema → SQL gen → validate → [cache|Snowflake] → interpret)
    3. PII scan on results
    4. Audit record (question, SQL, latency, cache_hit, pii_detected)
    5. Prometheus metric update
    """
    # ── Auth
    username: str | None = None
    if _AUTH_MODE == "jwt":
        user_claims = get_current_user(authorization)
        username = user_claims.get("sub")
    else:
        _check_password(x_app_password)

    _check_rate_limit(request)

    history = [t.model_dump() for t in req.history]

    start = time.monotonic()
    result = answer_question_full(req.question, history=history or None)
    latency_ms = int((time.monotonic() - start) * 1000)

    pii = pii_scan(result.rows) if result.rows else []

    # Determine the model that was used (available on result if orchestrator sets it)
    model_used = getattr(result, "model", "unknown")

    audit.record(
        question=req.question,
        sql=result.sql or None,
        success=result.error is None,
        row_count=result.row_count if result.error is None else None,
        latency_ms=latency_ms,
        cache_hit=result.cache_hit,
        pii_detected=pii or None,
        error=result.error,
    )

    # ── Metrics
    record_query(
        latency_ms=latency_ms,
        success=result.error is None,
        cache_hit=result.cache_hit,
        model=model_used,
        pii_types=pii,
    )

    # Update circuit breaker gauge
    cb_value = _CB_STATE_MAP.get(snowflake_breaker.state, 0)
    CIRCUIT_STATE.set(cb_value)

    return QueryResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
        cache_hit=result.cache_hit,
        pii_detected=pii,
        user=username,
    )


@app.get("/audit", response_model=list[AuditEntry])
def get_audit(
    limit: int = Query(default=100, le=500),
    x_app_password: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> list[AuditEntry]:
    """Return the most recent audit log entries (newest first). Auth-protected."""
    if _AUTH_MODE == "jwt":
        get_current_user(authorization)
    else:
        _check_password(x_app_password)
    return [AuditEntry(**e) for e in audit.recent(limit)]


# ── Static frontend ───────────────────────────────────────────────────────────
# Must come after all API routes so /query, /auth/*, etc. are not caught by the wildcard.

_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(_dist / "index.html")
