"""
Sliding-window rate limiter.

Limits each client (identified by IP address or username) to RATE_LIMIT_RPM
requests per 60-second window.  Excess requests receive HTTP 429 with a
Retry-After header indicating when the window resets.

Redis backend (optional)
------------------------
When Redis is configured (REDIS_URL env var), the limiter uses a Redis sorted
set per client_id with a sliding-window algorithm:

    ZREMRANGEBYSCORE  — evict timestamps outside the window
    ZCARD             — count remaining timestamps
    ZADD              — record the new request timestamp
    EXPIRE            — auto-clean the key after the window

This makes the rate limit consistent across all uvicorn workers.  When Redis
is unavailable the limiter falls back to the in-process deque implementation
(per-process — multiply RPM by worker count for effective limit).

Environment variables
---------------------
RATE_LIMIT_RPM    Requests per minute per client_id (default: 20)
"""

import collections
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

_RPM = int(os.environ.get("RATE_LIMIT_RPM", "20"))
_WINDOW = 60.0  # seconds
_REDIS_PREFIX = "ratelimit"


class RateLimiter:
    """
    Thread-safe sliding-window rate limiter keyed by client identifier.

    Uses Redis sorted sets when Redis is available for cross-worker consistency,
    falling back to an in-process deque when Redis is absent.
    """

    def __init__(self, rpm: int = _RPM) -> None:
        self._rpm = rpm
        # In-process fallback store
        self._requests: dict[str, collections.deque[float]] = {}
        self._lock = threading.Lock()

    # ── Internal helpers ──────────────────────────────────────────────────

    def _redis(self):
        """Return the Redis client or None if not available."""
        try:
            from db.redis_client import get_client  # noqa: PLC0415
            return get_client()
        except Exception:  # noqa: BLE001
            return None

    def _check_redis(self, client_id: str, now: float) -> tuple[bool, int] | None:
        """
        Perform the rate-limit check using a Redis sorted set.

        Returns (allowed, retry_after) on success, or None if Redis is
        unavailable so the caller can fall back to in-process logic.
        """
        r = self._redis()
        if r is None:
            return None

        key = f"{_REDIS_PREFIX}:{client_id}"
        window_start = now - _WINDOW

        try:
            pipe = r.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(key, "-inf", window_start)
            # Count requests in the current window
            pipe.zcard(key)
            # Add the current request timestamp (score = timestamp, member = unique)
            pipe.zadd(key, {str(now): now})
            # Auto-expire the key
            pipe.expire(key, int(_WINDOW) + 1)
            results = pipe.execute()

            count_before = results[1]  # count *before* adding current request

            if count_before >= self._rpm:
                # Find the oldest timestamp in the window for retry_after
                oldest = r.zrange(key, 0, 0, withscores=True)
                if oldest:
                    oldest_ts = oldest[0][1]
                    retry_after = int(_WINDOW - (now - oldest_ts)) + 1
                else:
                    retry_after = int(_WINDOW) + 1
                # Remove the request we just added (it was rejected)
                r.zrem(key, str(now))
                return False, retry_after

            return True, 0

        except Exception as exc:  # noqa: BLE001
            logger.debug("Redis rate-limit check failed: %s", exc)
            return None

    def _check_memory(self, client_id: str, now: float) -> tuple[bool, int]:
        """Perform the rate-limit check using the in-process deque."""
        with self._lock:
            q = self._requests.setdefault(client_id, collections.deque())
            # Drop timestamps outside the window
            while q and now - q[0] > _WINDOW:
                q.popleft()
            if len(q) >= self._rpm:
                retry_after = int(_WINDOW - (now - q[0])) + 1
                return False, retry_after
            q.append(now)
            return True, 0

    # ── Public API ────────────────────────────────────────────────────────

    def check(self, client_id: str) -> tuple[bool, int]:
        """
        Check whether *client_id* is within the rate limit.

        Returns
        -------
        (allowed, retry_after)
            allowed       True if the request may proceed.
            retry_after   Seconds until the oldest window entry expires
                          (0 when allowed=True).
        """
        now = time.monotonic()

        # Try Redis first
        result = self._check_redis(client_id, now)
        if result is not None:
            return result

        # Fall back to in-process deque
        return self._check_memory(client_id, now)


# Module-level singleton
limiter = RateLimiter()
