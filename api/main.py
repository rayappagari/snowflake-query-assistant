from dotenv import load_dotenv

# Must run before any agent/db imports — clients initialise at import time.
load_dotenv()

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agents.orchestrator import answer_question_full

app = FastAPI(title="Snowflake Query Assistant")

_APP_PASSWORD = os.environ.get("APP_PASSWORD", "")


def _check_password(x_app_password: str | None) -> None:
    if _APP_PASSWORD and x_app_password != _APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Incorrect password")


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, x_app_password: str | None = Header(default=None)) -> QueryResponse:
    _check_password(x_app_password)
    result = answer_question_full(req.question)
    return QueryResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
    )


# Serve React frontend — must come after API routes
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(_dist / "index.html")
