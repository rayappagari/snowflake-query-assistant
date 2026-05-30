import os
import platform
import sys
from typing import Any

# snowflake-connector-python calls platform.libc_ver() during authentication to
# collect telemetry. On Windows Store Python, sys.executable is a virtual app
# alias that cannot be opened as a file, raising [Errno 22]. Patch before import.
if sys.platform == "win32":
    platform.libc_ver = lambda *args, **kwargs: ("", "")

import snowflake.connector
from snowflake.connector import DictCursor


def _connect() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
    )


def execute_query(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    """Execute a SQL query and return rows as a list of dicts."""
    conn = _connect()
    try:
        cur = conn.cursor(DictCursor)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


def explain_query(sql: str) -> str:
    """
    Run EXPLAIN to validate syntax and semantics without consuming query credits.
    Raises snowflake.connector.errors.ProgrammingError on invalid SQL.
    """
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(f"EXPLAIN {sql}")
        rows = cur.fetchall()
        return "\n".join(str(r) for r in rows)
    finally:
        conn.close()
