import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn = sqlite3.connect(":memory:", check_same_thread=False)


def _init() -> None:
    with _conn:
        _conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ts            TEXT    NOT NULL,
                question      TEXT    NOT NULL,
                sql_generated TEXT,
                success       INTEGER NOT NULL,
                row_count     INTEGER,
                latency_ms    INTEGER,
                error_message TEXT
            )
        """)


_init()


def record(
    question: str,
    sql: str | None,
    success: bool,
    row_count: int | None = None,
    latency_ms: int | None = None,
    error: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    with _lock:
        with _conn:
            _conn.execute(
                """
                INSERT INTO audit_log
                    (ts, question, sql_generated, success, row_count, latency_ms, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, question, sql, int(success), row_count, latency_ms, error),
            )
    # Stream to stdout so Railway captures it permanently
    logger.info(json.dumps({
        "event": "query",
        "ts": ts,
        "question": question,
        "success": success,
        "row_count": row_count,
        "latency_ms": latency_ms,
        "error": error,
    }))


def recent(limit: int = 100) -> list[dict]:
    with _lock:
        cur = _conn.execute(
            """
            SELECT id, ts, question, sql_generated, success, row_count, latency_ms, error_message
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    for r in rows:
        r["success"] = bool(r["success"])
    return rows
