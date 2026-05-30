from dotenv import load_dotenv

# Must run before any agent/db imports — clients initialise at import time.
load_dotenv()

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator import answer_question_full

app = FastAPI(title="Snowflake Query Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


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
def query(req: QueryRequest) -> QueryResponse:
    result = answer_question_full(req.question)
    return QueryResponse(
        answer=result.answer,
        sql=result.sql,
        rows=result.rows,
        row_count=result.row_count,
        error=result.error,
    )
