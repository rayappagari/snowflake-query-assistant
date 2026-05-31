"""
FastAPI application — the HTTP layer for the Snowflake Query Assistant.

Endpoints
---------
GET  /health     Liveness probe (no auth)
GET  /verify     Password check (returns 401 on bad password)
POST /query      Run a question through the agent pipeline
GET  /audit      Retrieve the audit log (password-protected)

All endpoints except /health require the X-App-Password header when
APP_PASSWORD is set in the environment.

Rate limiting: api/rate_limit.py — configurable via RATE_LIMIT_RPM env var.
PII scanning:  agents/pii.py    — results are scanned before being returned.
Audit logging: db/audit.py      — every /query call is recorded.
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
from api.rate_limit import limiter
from db import audit

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="Snowflake Query Assistant")

_APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
_QUERY_TIMEOUT = int(os.environ.get("QUERY_TIMEOUT_SECONDS", "120"))


# ── Auth ─────────────────────────────────────────────────────────────────────

def _check_password(x_app_password: str | None) -> None:
    if _APP_PASSWORD and x_app_password != _APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = limiter.check(client_ip)
    if not allowed:
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


@app.get("/verify")
def verify(x_app_password: str | None = Header(default=None)) -> dict:
    """Validate the app password. Returns 401 on mismatch."""
    _check_password(x_app_password)
    return {"ok": True}


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    request: Request,
    x_app_password: str | None = Header(default=None),
) -> QueryResponse:
    """
    Run a question through the full agent pipeline.

    Flow:
      1. Auth + rate-limit checks
      2. Pipeline (schema → SQL gen → validation → [cache|Snowflake] → interpret)
      3. PII scan on results
      4. Audit record (question, SQL, latency, cache_hit, pii_detected)
    """
    _check_password(x_app_password)
    _check_rate_limit(request)

    history = [t.model_dump() for t in req.history]

    start = time.monotonic()
    result = answer_question_full(req.question, history=history or None)
    latency_ms = int((time.monotonic() - start) * 1000)

    pii = pii_scan(result.rows) if result.rows else []

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

    return QueryResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
        cache_hit=result.cache_hit,
        pii_detected=pii,
    )


@app.get("/audit", response_model=list[AuditEntry])
def get_audit(
    limit: int = Query(default=100, le=500),
    x_app_password: str | None = Header(default=None),
) -> list[AuditEntry]:
    """Return the most recent audit log entries (newest first). Password-protected."""
    _check_password(x_app_password)
    return [AuditEntry(**e) for e in audit.recent(limit)]


# ── Static frontend ───────────────────────────────────────────────────────────
# Must come after all API routes so /query etc. are not caught by the wildcard.

_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(_dist / "index.html")
