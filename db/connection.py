"""
Snowflake query execution.

Uses db.pool for connection reuse and db.circuit_breaker to stop hammering
Snowflake when it is degraded.

Row values come back as dict[str, Any] with UPPERCASE column-name keys
(Snowflake's DictCursor default).
"""

import platform
import sys
from typing import Any

# snowflake-connector-python calls platform.libc_ver() during authentication
# telemetry collection. On Windows Store Python, sys.executable is a virtual
# app alias that raises [Errno 22]. Patch before import.
if sys.platform == "win32":
    platform.libc_ver = lambda *args, **kwargs: ("", "")

from snowflake.connector import DictCursor

from db.circuit_breaker import snowflake_breaker
from db.pool import pool


def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """
    Execute a SQL SELECT and return rows as a list of dicts.

    Routed through the circuit breaker — raises RuntimeError if Snowflake is
    currently marked unavailable. Connection is drawn from the shared pool.
    """
    def _run() -> list[dict[str, Any]]:
        with pool.acquire() as conn:
            cur = conn.cursor(DictCursor)
            cur.execute(sql, params)
            return cur.fetchall()

    return snowflake_breaker.call(_run)


def explain_query(sql: str) -> str:
    """
    Run EXPLAIN to validate SQL syntax/semantics without consuming credits.

    Raises snowflake.connector.errors.ProgrammingError on invalid SQL.
    Routed through the circuit breaker.
    """
    def _run() -> str:
        with pool.acquire() as conn:
            cur = conn.cursor()
            cur.execute(f"EXPLAIN {sql}")
            rows = cur.fetchall()
            return "\n".join(str(r) for r in rows)

    return snowflake_breaker.call(_run)
