"""
Pipeline orchestrator.

Coordinates the full question → answer pipeline:

  1. identify_relevant_schema  (Haiku — cheap table filter)
  2. generate_sql              (Haiku or Opus, chosen by router)
  3. validate_sql              (read-only check + Snowflake EXPLAIN)
  4. execute_query             (Snowflake — skipped on cache hit)
  5. interpret_results         (same model as sql_gen)

On validation failure: retry with the error appended (up to MAX_RETRIES).
On execution failure:  call error_recovery, then retry.

Result caching: after a successful execution the (SQL → rows) pair is stored
in db.result_cache. On subsequent calls with the same SQL the Snowflake round-
trip is skipped entirely and the cached rows are used directly.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from agents.error_recovery import suggest_fix
from agents.interpreter import interpret_results
from agents.router import choose_model
from agents.schema import identify_relevant_schema
from agents.sql_gen import generate_sql
from agents.validator import validate_sql
from db.connection import execute_query
from db.result_cache import result_cache

MAX_RETRIES = 3


@dataclass
class QueryResult:
    answer: str
    sql: str
    rows: list[dict[str, Any]]
    row_count: int
    error: str | None = None
    cache_hit: bool = False
    pii_detected: list[str] | None = None


def _jsonify(row: dict) -> dict:
    """Convert Snowflake row values to JSON-serialisable Python types."""
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
    CLI-friendly pipeline — returns a plain-language string answer.
    Retries up to MAX_RETRIES times.
    """

    def log(msg: str) -> None:
        if verbose:
            print(f"  {msg}")

    log("[schema] discovering relevant tables...")
    schema = identify_relevant_schema(question)
    model = choose_model(question)
    log(f"[router] selected model: {model}")

    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        log(f"[sql_gen] generating SQL (attempt {attempt}/{MAX_RETRIES})...")
        sql = generate_sql(question, schema, previous_error=last_error, model=model)
        log(f"[sql_gen] → {sql}")

        log("[validator] checking SQL...")
        valid, validation_msg = validate_sql(sql)
        if not valid:
            log(f"[validator] invalid — {validation_msg}")
            last_error = validation_msg
            continue

        cached = result_cache.get(sql)
        if cached is not None:
            log(f"[cache] hit — {len(cached)} row(s)")
            return interpret_results(question, sql, cached, model=model)

        log("[execute] running query against Snowflake...")
        try:
            results = execute_query(sql)
            result_cache.set(sql, results)
        except Exception as exc:
            last_error = str(exc)
            log(f"[execute] error — {last_error}")
            log("[error_recovery] requesting corrected SQL...")
            sql = suggest_fix(sql, last_error, schema)
            last_error = f"Execution error: {last_error}"
            continue

        log(f"[interpreter] summarising {len(results)} row(s)...")
        return interpret_results(question, sql, results, model=model)

    return (
        f"I could not produce a working query after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


def answer_question_full(
    question: str,
    history: list[dict] | None = None,
) -> QueryResult:
    """
    Full pipeline returning a structured QueryResult for the API layer.

    Parameters
    ----------
    history     Conversation turns [{question, sql, answer}] for follow-up context.

    Returns
    -------
    QueryResult with answer, sql, rows, row_count, cache_hit, and pii_detected.
    """
    schema = identify_relevant_schema(question)
    model = choose_model(question)
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        sql = generate_sql(
            question, schema,
            previous_error=last_error,
            history=history,
            model=model,
        )

        valid, validation_msg = validate_sql(sql)
        if not valid:
            last_error = validation_msg
            continue

        # Check result cache before hitting Snowflake
        cached = result_cache.get(sql)
        if cached is not None:
            answer = interpret_results(question, sql, cached, history=history, model=model)
            serialised = [_jsonify(r) for r in cached]
            return QueryResult(
                answer=answer,
                sql=sql,
                rows=serialised,
                row_count=len(cached),
                cache_hit=True,
            )

        try:
            rows = execute_query(sql)
            result_cache.set(sql, rows)
        except Exception as exc:
            last_error = str(exc)
            sql = suggest_fix(sql, last_error, schema)
            last_error = f"Execution error: {last_error}"
            continue

        answer = interpret_results(question, sql, rows, history=history, model=model)
        serialised = [_jsonify(r) for r in rows]
        return QueryResult(
            answer=answer,
            sql=sql,
            rows=serialised,
            row_count=len(rows),
            cache_hit=False,
        )

    return QueryResult(
        answer=(
            f"Could not produce a working query after {MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        ),
        sql="",
        rows=[],
        row_count=0,
        error=last_error,
    )
