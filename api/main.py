from dotenv import load_dotenv

# Must run before any agent/db imports — clients initialise at import time.
load_dotenv()

import logging
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator import answer_question_full
from db import audit

logging.basicConfig(level=logging.INFO, format="%(message)s")

app = FastAPI(title="Snowflake Query Assistant")

_APP_PASSWORD = os.environ.get("APP_PASSWORD", "")


def _check_password(x_app_password: str | None) -> None:
    if _APP_PASSWORD and x_app_password != _APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")


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


class AuditEntry(BaseModel):
    id: int
    ts: str
    question: str
    sql_generated: str | None
    success: bool
    row_count: int | None
    latency_ms: int | None
    error_message: str | None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/verify")
def verify(x_app_password: str | None = Header(default=None)) -> dict:
    _check_password(x_app_password)
    return {"ok": True}


@app.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    x_app_password: str | None = Header(default=None),
) -> QueryResponse:
    _check_password(x_app_password)
    history = [t.model_dump() for t in req.history]

    start = time.monotonic()
    result = answer_question_full(req.question, history=history or None)
    latency_ms = int((time.monotonic() - start) * 1000)

    audit.record(
        question=req.question,
        sql=result.sql or None,
        success=result.error is None,
        row_count=result.row_count if result.error is None else None,
        latency_ms=latency_ms,
        error=result.error,
    )

    return QueryResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
    )


@app.get("/audit", response_model=list[AuditEntry])
def get_audit(
    limit: int = Query(default=100, le=500),
    x_app_password: str | None = Header(default=None),
) -> list[AuditEntry]:
    _check_password(x_app_password)
    return [AuditEntry(**e) for e in audit.recent(limit)]


# Serve React frontend — must come after API routes
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(_dist / "index.html")
