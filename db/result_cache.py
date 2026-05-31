"""
TTL result cache for Snowflake query results.

Keyed by normalised SQL (whitespace-collapsed, lowercased, SHA-256 hashed).
Identical SQL within the TTL window hits the cache and skips Snowflake
execution entirely — saving credits and reducing latency.

Bounded by max_entries to prevent unbounded memory growth; oldest entries are
evicted when the limit is reached.

Redis backend (optional)
------------------------
When Redis is configured (REDIS_URL env var), results are stored in Redis in
addition to the in-process dict.  Redis enables cache sharing across multiple
uvicorn workers and across restarts.  The in-process dict is always checked
first for lowest latency; Redis is the secondary source and the primary writer.

Environment variables
---------------------
RESULT_CACHE_TTL        Cache TTL in seconds (default: 300 = 5 minutes)
RESULT_CACHE_MAX        Maximum cached entries in the in-process dict (default: 200)
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_TTL = int(os.environ.get("RESULT_CACHE_TTL", "300"))
_MAX = int(os.environ.get("RESULT_CACHE_MAX", "200"))
_WHITESPACE = re.compile(r"\s+")
_REDIS_PREFIX = "snowflake_cache"


def _key(sql: str) -> str:
    normalised = _WHITESPACE.sub(" ", sql.strip().lower())
    return hashlib.sha256(normalised.encode()).hexdigest()


class ResultCache:
    """
    Thread-safe TTL cache mapping normalised SQL → query rows.

    Uses a two-tier storage strategy:
    - In-process dict (always available, lowest latency)
    - Redis (optional; shared across workers; backed by REDIS_URL)
    """

    def __init__(self, ttl: int = _TTL, max_entries: int = _MAX) -> None:
        self._ttl = ttl
        self._max = max_entries
        # {key: (inserted_at, rows)}
        self._store: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = threading.RLock()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _redis(self):
        """Return the Redis client or None if not available."""
        try:
            from db.redis_client import get_client  # noqa: PLC0415
            return get_client()
        except Exception:  # noqa: BLE001
            return None

    def _redis_get(self, k: str) -> list[dict[str, Any]] | None:
        """Fetch an entry from Redis.  Returns None on miss or error."""
        r = self._redis()
        if r is None:
            return None
        try:
            raw = r.hget(f"{_REDIS_PREFIX}:{k}", "rows")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis get failed: %s", exc)
            return None

    def _redis_set(self, k: str, rows: list[dict[str, Any]]) -> None:
        """Store an entry in Redis with TTL.  Silently ignores errors."""
        r = self._redis()
        if r is None:
            return
        try:
            r.hset(f"{_REDIS_PREFIX}:{k}", "rows", json.dumps(rows))
            r.expire(f"{_REDIS_PREFIX}:{k}", self._ttl)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis set failed: %s", exc)

    def _redis_del(self, k: str) -> None:
        """Delete an entry from Redis.  Silently ignores errors."""
        r = self._redis()
        if r is None:
            return
        try:
            r.delete(f"{_REDIS_PREFIX}:{k}")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis del failed: %s", exc)

    # ── Public API ────────────────────────────────────────────────────────

    def get(self, sql: str) -> list[dict[str, Any]] | None:
        """
        Return cached rows for *sql*, or None if absent / expired.

        Checks in-process dict first, then Redis.  On a Redis hit the rows
        are promoted to the in-process dict for subsequent requests.
        """
        k = _key(sql)

        # 1. In-process dict
        with self._lock:
            entry = self._store.get(k)
            if entry is not None:
                ts, rows = entry
                if time.monotonic() - ts <= self._ttl:
                    return rows
                del self._store[k]

        # 2. Redis fallback
        rows = self._redis_get(k)
        if rows is not None:
            # Promote to in-process dict
            with self._lock:
                if len(self._store) >= self._max and k not in self._store:
                    oldest = next(iter(self._store))
                    del self._store[oldest]
                self._store[k] = (time.monotonic(), rows)
            return rows

        return None

    def set(self, sql: str, rows: list[dict[str, Any]]) -> None:
        """
        Store *rows* for *sql*.

        Writes to both Redis (if available) and the in-process dict.
        Evicts the oldest in-process entry when at capacity.
        """
        k = _key(sql)

        # 1. Write to Redis
        self._redis_set(k, rows)

        # 2. Write to in-process dict
        with self._lock:
            if len(self._store) >= self._max and k not in self._store:
                oldest = next(iter(self._store))
                del self._store[oldest]
            self._store[k] = (time.monotonic(), rows)

    def invalidate(self, sql: str | None = None) -> None:
        """
        Remove a specific SQL entry, or flush the entire cache if sql=None.

        Deletes from Redis (if available) and clears the in-process dict.
        """
        with self._lock:
            if sql is None:
                # Flush in-process dict; Redis entries expire on their own TTL
                self._store.clear()
            else:
                k = _key(sql)
                self._store.pop(k, None)
                self._redis_del(k)


# Module-level singleton
result_cache = ResultCache()
