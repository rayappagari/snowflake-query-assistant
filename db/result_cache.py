"""
TTL result cache for Snowflake query results.

Keyed by normalised SQL (whitespace-collapsed, lowercased, SHA-256 hashed).
Identical SQL within the TTL window hits the cache and skips Snowflake
execution entirely — saving credits and reducing latency.

Bounded by max_entries to prevent unbounded memory growth; oldest entries are
evicted when the limit is reached.

Environment variables
---------------------
RESULT_CACHE_TTL        Cache TTL in seconds (default: 300 = 5 minutes)
RESULT_CACHE_MAX        Maximum cached entries (default: 200)
"""

import hashlib
import os
import re
import threading
import time
from typing import Any

_TTL = int(os.environ.get("RESULT_CACHE_TTL", "300"))
_MAX = int(os.environ.get("RESULT_CACHE_MAX", "200"))
_WHITESPACE = re.compile(r"\s+")


def _key(sql: str) -> str:
    normalised = _WHITESPACE.sub(" ", sql.strip().lower())
    return hashlib.sha256(normalised.encode()).hexdigest()


class ResultCache:
    """Thread-safe TTL cache mapping normalised SQL → query rows."""

    def __init__(self, ttl: int = _TTL, max_entries: int = _MAX) -> None:
        self._ttl = ttl
        self._max = max_entries
        # {key: (inserted_at, rows)}
        self._store: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._lock = threading.RLock()

    def get(self, sql: str) -> list[dict[str, Any]] | None:
        """Return cached rows for `sql`, or None if absent / expired."""
        k = _key(sql)
        with self._lock:
            entry = self._store.get(k)
            if entry is None:
                return None
            ts, rows = entry
            if time.monotonic() - ts > self._ttl:
                del self._store[k]
                return None
            return rows

    def set(self, sql: str, rows: list[dict[str, Any]]) -> None:
        """Store rows for `sql`. Evicts the oldest entry if at capacity."""
        k = _key(sql)
        with self._lock:
            if len(self._store) >= self._max and k not in self._store:
                oldest = next(iter(self._store))
                del self._store[oldest]
            self._store[k] = (time.monotonic(), rows)

    def invalidate(self, sql: str | None = None) -> None:
        """Remove a specific SQL entry, or flush the entire cache if sql=None."""
        with self._lock:
            if sql is None:
                self._store.clear()
            else:
                self._store.pop(_key(sql), None)


# Module-level singleton
result_cache = ResultCache()
