"""
Pipeline orchestrator.

Coordinates the full question → answer pipeline:

  1. Question cache check   (skip everything if same question was asked recently)
  2. identify_relevant_schema  (Haiku — cheap table filter)
  3. choose_model              (router — Haiku vs Opus)
  4. generate_sql              (chosen model)
  5. validate_sql              (read-only check + Snowflake EXPLAIN)
     - Read-only violations return immediately — no retries, no timeout
  6. execute_query             (Snowflake — skipped on SQL cache hit)
  7. interpret_results         (same model as sql_gen)
  8. Question cache store      (cache full result keyed by question)

Two cache layers
----------------
Question cache  (orchestrator module level, in-process + Redis)
  Key = SHA256(normalised_question + history_fingerprint)
  Hits before any API or Snowflake call — fastest possible response.
  Fixes the case where the same question generates slightly different SQL
  on each call, causing SQL-level cache misses.

SQL cache  (db/result_cache, in-process + Redis)
  Key = SHA256(normalised_sql)
  Hits after SQL generation but before Snowflake execution.
  Shared across questions that happen to produce the same SQL.

Retry policy
------------
On validation failure (syntax/semantic):  retry with error appended (up to MAX_RETRIES).
On read-only violation ("Blocked:"):       return immediately — retrying will never succeed.
On execution failure:                      call error_recovery, then retry (up to MAX_RETRIES).
"""

import hashlib
import json
import os
import time as _time
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
from db.redis_client import get_client as _redis
from db.result_cache import result_cache

MAX_RETRIES = 3
_Q_CACHE_TTL = int(os.environ.get("RESULT_CACHE_TTL", "300"))

# In-process question cache: {key: (inserted_at, serialised_result)}
_q_cache: dict[str, tuple[float, dict]] = {}


# ── Question cache helpers ────────────────────────────────────────────────────

def _q_key(question: str, history: list[dict] | None) -> str:
    norm = question.strip().lower()
    h_sig = "|".join(t["question"] for t in (history or [])[-3:])
    return hashlib.sha256(f"{norm}||{h_sig}".encode()).hexdigest()


def _q_get(question: str, history: list[dict] | None) -> dict | None:
    key = _q_key(question, history)
    # 1. Try Redis
    r = _redis()
    if r:
        try:
            val = r.get(f"snowflake_qcache:{key}")
            if val:
                return json.loads(val)
        except Exception:
            pass
    # 2. Try in-process
    entry = _q_cache.get(key)
    if entry:
        ts, data = entry
        if _time.monotonic() - ts <= _Q_CACHE_TTL:
            return data
        del _q_cache[key]
    return None


def _q_set(question: str, history: list[dict] | None, result: "QueryResult") -> None:
    key = _q_key(question, history)
    data = {
        "answer": result.answer,
        "sql": result.sql,
        "rows": result.rows,
        "row_count": result.row_count,
        "error": result.error,
        "cache_hit": True,          # always True when served from question cache
        "pii_detected": result.pii_detected,
    }
    # 1. Write to Redis
    r = _redis()
    if r:
        try:
            r.setex(f"snowflake_qcache:{key}", _Q_CACHE_TTL, json.dumps(data, default=str))
        except Exception:
            pass
    # 2. Write to in-process
    _q_cache[key] = (_time.monotonic(), data)


# ── Data model ────────────────────────────────────────────────────────────────

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


# ── CLI pipeline ──────────────────────────────────────────────────────────────

def answer_question(question: str, verbose: bool = True) -> str:
    """CLI-friendly pipeline — returns a plain-language string answer."""

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
            log(f"[validator] {validation_msg}")
            if validation_msg.startswith("Blocked:"):
                return f"That type of query is not permitted. {validation_msg}"
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
            sql = suggest_fix(sql, last_error, schema)
            last_error = f"Execution error: {last_error}"
            continue

        log(f"[interpreter] summarising {len(results)} row(s)...")
        return interpret_results(question, sql, results, model=model)

    return (
        f"I could not produce a working query after {MAX_RETRIES} attempts. "
        f"Last error: {last_error}"
    )


# ── API pipeline ──────────────────────────────────────────────────────────────

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
    # ── Layer 1: question cache ───────────────────────────────────────────────
    cached_q = _q_get(question, history)
    if cached_q:
        return QueryResult(**{k: cached_q[k] for k in (
            "answer", "sql", "rows", "row_count", "error", "cache_hit", "pii_detected"
        )})

    # ── Pipeline ──────────────────────────────────────────────────────────────
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
            # Read-only violations are permanent — retrying will never succeed.
            if validation_msg.startswith("Blocked:"):
                return QueryResult(
                    answer=(
                        "This type of query is not permitted. "
                        "Only read-only SELECT queries are allowed."
                    ),
                    sql=sql,
                    rows=[],
                    row_count=0,
                    error=validation_msg,
                )
            last_error = validation_msg
            continue

        # ── Layer 2: SQL cache ────────────────────────────────────────────────
        cached_sql = result_cache.get(sql)
        if cached_sql is not None:
            answer = interpret_results(question, sql, cached_sql, history=history, model=model)
            serialised = [_jsonify(r) for r in cached_sql]
            result = QueryResult(
                answer=answer,
                sql=sql,
                rows=serialised,
                row_count=len(cached_sql),
                cache_hit=True,
            )
            _q_set(question, history, result)
            return result

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
        result = QueryResult(
            answer=answer,
            sql=sql,
            rows=serialised,
            row_count=len(rows),
            cache_hit=False,
        )
        _q_set(question, history, result)
        return result

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
