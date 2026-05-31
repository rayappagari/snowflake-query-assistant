"""
Lazy Redis client.

Provides a single shared Redis connection (backed by redis-py's built-in
connection pool) that is initialised on first use. When REDIS_URL is not set,
or when redis-py is not installed, all helpers return None / False so callers
can fall back to in-memory alternatives without crashing.

Environment variables
---------------------
REDIS_URL    Full Redis connection string, e.g. ``redis://localhost:6379``.
             On Railway this is provided automatically when you add a Redis
             service. When absent, is_available() returns False and every
             feature that uses Redis falls back to its in-process equivalent.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def get_client():
    """
    Return a connected ``redis.Redis`` instance, or ``None`` if Redis is not
    configured / available.

    The connection is lazy — the first call does the I/O; subsequent calls
    return the cached client.  Thread-safe via a double-checked lock.
    """
    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is not None:
            return _client

        url = os.environ.get("REDIS_URL", "")
        if not url:
            return None

        try:
            import redis  # noqa: PLC0415
        except ImportError:
            logger.warning("redis-py not installed — Redis disabled")
            return None

        try:
            client = redis.from_url(url, decode_responses=True)
            client.ping()   # raises on connection failure
            _client = client
            logger.info("Redis client connected to %s", url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis connection failed: %s — using in-memory fallback", exc)
            _client = None

    return _client


def is_available() -> bool:
    """Return True if a Redis connection is configured and reachable."""
    return get_client() is not None
