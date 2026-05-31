from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from agents.error_recovery import suggest_fix
from agents.interpreter import interpret_results
from agents.schema import identify_relevant_schema
from agents.sql_gen import generate_sql
from agents.validator import validate_sql
from db.connection import execute_query

MAX_RETRIES = 3


@dataclass
class QueryResult:
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    error: str | None = None


def _jsonify(row: dict) -> dict:
    """Convert Snowflake row values to JSON-serialisable types."""
    out = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def answer_question(question: str, verbose: bool = True) -> str:
    """
    Full pipeline: schema → SQL generation → validation → execution → interpretation.
    Retries up to MAX_RETRIES times, using error_recovery on execution failures.
    """

    def log(msg: str) -> None:
        if verbose:
            print(f"  {msg}")

    log("[schema] discovering relevant tables...")
    schema = identify_relevant_schema(question)

    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        log(f"[sql_gen] generating SQL (attempt {attempt}/{MAX_RETRIES})...")
        sql = generate_sql(question, schema, previous_error=last_error)
        log(f"[sql_gen] → {sql}")

        log("[validator] checking SQL with EXPLAIN...")
        valid, validation_msg = validate_sql(sql)
        if not valid:
            log(f"[validator] invalid — {validation_msg}")
            last_error = validation_msg
            continue  # retry: sql_gen will receive the error on the next pass

        log("[execute] running query against Snowflake...")
        try:
            results = execute_query(sql)
        except Exception as exc:
            last_error = str(exc)
            log(f"[execute] error — {last_error}")
            log("[error_recovery] requesting corrected SQL...")
            sql = suggest_fix(sql, last_error, schema)
            last_error = f"Execution error: {last_error}"
            continue  # retry with the recovered SQL as a starting point

        log(f"[interpreter] summarising {len(results)} row(s)...")
        return interpret_results(question, sql, results)

    return (
        f"I could not produce a working query after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def answer_question_full(
    question: str,
    history: list[dict] | None = None,
) -> QueryResult:
    """
    Same pipeline as answer_question but returns structured QueryResult
    (answer + SQL + serialised rows) for the API layer.
    Pass history (list of {question, sql, answer} dicts) for conversation memory.
    """
    schema = identify_relevant_schema(question)
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        sql = generate_sql(question, schema, previous_error=last_error, history=history)

        valid, validation_msg = validate_sql(sql)
        if not valid:
            last_error = validation_msg
            continue

        try:
            rows = execute_query(sql)
        except Exception as exc:
            last_error = str(exc)
            sql = suggest_fix(sql, last_error, schema)
            last_error = f"Execution error: {last_error}"
            continue

        answer = interpret_results(question, sql, rows, history=history)
        serialised = [_jsonify(r) for r in rows]
        return QueryResult(answer=answer, sql=sql, rows=serialised, row_count=len(rows))

    return QueryResult(
        answer=f"Could not produce a working query after {MAX_RETRIES} attempts. Last error: {last_error}",
        sql="",
        rows=[],
        row_count=0,
        error=last_error,
    )
