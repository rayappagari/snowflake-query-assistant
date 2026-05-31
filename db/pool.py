"""
Snowflake connection pool.

Opens SNOWFLAKE_POOL_SIZE persistent connections at first use (lazy init so
load_dotenv() runs first). Each acquire() health-checks the connection before
handing it to the caller and returns it to the pool in the finally block.

Environment variables
---------------------
SNOWFLAKE_POOL_SIZE          Number of pooled connections (default: 5)
SNOWFLAKE_ACQUIRE_TIMEOUT    Seconds to wait for a free connection (default: 30)
QUERY_TIMEOUT_SECONDS        Snowflake network / query timeout (default: 120)
"""

import os
import queue
import threading
from contextlib import contextmanager
from typing import Generator

import snowflake.connector

_POOL_SIZE = int(os.environ.get("SNOWFLAKE_POOL_SIZE", "5"))
_ACQUIRE_TIMEOUT = float(os.environ.get("SNOWFLAKE_ACQUIRE_TIMEOUT", "30"))
_QUERY_TIMEOUT = int(os.environ.get("QUERY_TIMEOUT_SECONDS", "120"))


def _new_connection() -> snowflake.connector.SnowflakeConnection:
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        schema=os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
        login_timeout=30,
        network_timeout=_QUERY_TIMEOUT,
        session_parameters={"QUERY_TAG": "snowflake-query-assistant"},
    )


class _Pool:
    """Thread-safe Snowflake connection pool backed by a queue."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._q: queue.Queue[snowflake.connector.SnowflakeConnection] = queue.Queue()
        self._lock = threading.Lock()
        self._initialised = False

    def _ensure_init(self) -> None:
        """Lazily fill the pool on first use (after env vars are loaded)."""
        with self._lock:
            if not self._initialised:
                for _ in range(self._size):
                    self._q.put(_new_connection())
                self._initialised = True

    def _is_alive(self, conn: snowflake.connector.SnowflakeConnection) -> bool:
        try:
            conn.cursor().execute("SELECT 1")
            return True
        except Exception:
            return False

    @contextmanager
    def acquire(self) -> Generator[snowflake.connector.SnowflakeConnection, None, None]:
        self._ensure_init()
        try:
            conn = self._q.get(timeout=_ACQUIRE_TIMEOUT)
        except queue.Empty:
            raise RuntimeError(
                f"Snowflake pool exhausted — no connection available after {_ACQUIRE_TIMEOUT}s. "
                f"Try increasing SNOWFLAKE_POOL_SIZE (current: {self._size})."
            )

        if not self._is_alive(conn):
            try:
                conn.close()
            except Exception:
                pass
            conn = _new_connection()

        try:
            yield conn
        finally:
            self._q.put(conn)


# Module-level singleton — imported by db/connection.py
pool = _Pool(_POOL_SIZE)
