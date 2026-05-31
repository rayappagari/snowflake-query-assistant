"""
PostgreSQL connection pool for enterprise persistence.

Uses psycopg2.pool.ThreadedConnectionPool with lazy initialisation — the pool
is created on the first call to query() or is_available(), not at module import
time. This means DATABASE_URL does not need to be set for the app to start;
all features gracefully fall back to SQLite/in-memory when PostgreSQL is absent.

Railway convention: DATABASE_URL may use the ``postgres://`` prefix
(deprecated in newer PostgreSQL versions). This module rewrites it to
``postgresql://`` automatically.

Tables created on first use via _migrate():
    users       — application user accounts with hashed passwords and roles
    audit_log   — persistent, cross-worker audit trail for all queries

Environment variables
---------------------
DATABASE_URL    Full PostgreSQL connection string (optional). When absent all
                calls to query() return None and is_available() returns False.
"""

import json
import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_pool = None
_pool_lock = threading.Lock()
_migrated = False

# ── Helpers ──────────────────────────────────────────────────────────────────

def _fix_url(url: str) -> str:
    """Rewrite Railway's ``postgres://`` prefix to ``postgresql://``."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


def _get_pool():
    """
    Lazily create and return the connection pool.

    Returns None if DATABASE_URL is not set or psycopg2 is not installed.
    Thread-safe — only one pool is ever created.
    """
    global _pool, _migrated
    if _pool is not None:
        return _pool

    with _pool_lock:
        if _pool is not None:           # double-checked locking
            return _pool

        raw_url = os.environ.get("DATABASE_URL", "")
        if not raw_url:
            return None

        try:
            import psycopg2.pool  # noqa: PLC0415
        except ImportError:
            logger.warning("psycopg2 not installed — PostgreSQL disabled")
            return None

        try:
            url = _fix_url(raw_url)
            _pool = psycopg2.pool.ThreadedConnectionPool(1, 10, url)
            logger.info("PostgreSQL pool created")
            if not _migrated:
                _migrate()
                _migrated = True
        except Exception as exc:  # noqa: BLE001
            logger.error("PostgreSQL pool creation failed: %s", exc)
            _pool = None

    return _pool


# ── Migration ─────────────────────────────────────────────────────────────────

def _migrate() -> None:
    """
    Create application tables if they do not exist.

    Safe to call multiple times — uses CREATE TABLE IF NOT EXISTS throughout.
    """
    pool = _get_pool()
    if pool is None:
        return

    import psycopg2.extras  # noqa: PLC0415

    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id              SERIAL PRIMARY KEY,
                        username        VARCHAR(100) UNIQUE NOT NULL,
                        email           VARCHAR(200),
                        hashed_password TEXT NOT NULL,
                        role            VARCHAR(20) DEFAULT 'user',
                        created_at      TIMESTAMPTZ DEFAULT NOW(),
                        is_active       BOOLEAN DEFAULT TRUE
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id            SERIAL PRIMARY KEY,
                        ts            TIMESTAMPTZ DEFAULT NOW(),
                        question      TEXT NOT NULL,
                        sql_generated TEXT,
                        success       BOOLEAN NOT NULL,
                        row_count     INT,
                        latency_ms    INT,
                        cache_hit     BOOLEAN DEFAULT FALSE,
                        pii_detected  TEXT DEFAULT '',
                        error_message TEXT
                    )
                """)
        logger.info("PostgreSQL tables migrated")
    finally:
        pool.putconn(conn)


# ── Public API ────────────────────────────────────────────────────────────────

def is_available() -> bool:
    """Return True if a PostgreSQL pool is configured and healthy."""
    return _get_pool() is not None


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]] | None:
    """
    Execute *sql* with *params* and return all rows as dicts.

    Returns None when PostgreSQL is not available so callers can fall back
    gracefully to SQLite or in-memory alternatives.

    Parameters
    ----------
    sql:
        Parameterised SQL string (use ``%s`` placeholders for psycopg2).
    params:
        Positional parameters passed to execute().
    """
    pool = _get_pool()
    if pool is None:
        return None

    import psycopg2.extras  # noqa: PLC0415

    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                # INSERT/UPDATE have no result set
                try:
                    rows = cur.fetchall()
                    return [dict(r) for r in rows]
                except Exception:  # noqa: BLE001
                    return []
    except Exception as exc:  # noqa: BLE001
        logger.error("PostgreSQL query error: %s", exc)
        return None
    finally:
        pool.putconn(conn)
