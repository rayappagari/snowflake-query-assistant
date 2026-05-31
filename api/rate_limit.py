"""
Sliding-window rate limiter.

Limits each client (identified by IP address) to RATE_LIMIT_RPM requests
per 60-second window. Excess requests receive HTTP 429 with a Retry-After
header indicating when the window resets.

Note: This is an in-process limiter. With multiple uvicorn workers each
process maintains its own counter, so effective limit = RPM × workers.
For strict per-user enforcement across workers, replace with Redis-backed
counters (e.g. redis-py + INCR + EXPIRE).

Environment variables
---------------------
RATE_LIMIT_RPM    Requests per minute per IP (default: 20)
"""

import collections
import os
import threading
import time

_RPM = int(os.environ.get("RATE_LIMIT_RPM", "20"))
_WINDOW = 60.0  # seconds


class RateLimiter:
    """Thread-safe sliding-window rate limiter keyed by client IP."""

    def __init__(self, rpm: int = _RPM) -> None:
        self._rpm = rpm
        self._requests: dict[str, collections.deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, client_id: str) -> tuple[bool, int]:
        """
        Check whether `client_id` is within the rate limit.

        Returns
        -------
        (allowed, retry_after)
            allowed       True if the request may proceed.
            retry_after   Seconds until the window resets (0 when allowed=True).
        """
        now = time.monotonic()
        with self._lock:
            q = self._requests.setdefault(client_id, collections.deque())
            # Drop timestamps older than the window
            while q and now - q[0] > _WINDOW:
                q.popleft()
            if len(q) >= self._rpm:
                retry_after = int(_WINDOW - (now - q[0])) + 1
                return False, retry_after
            q.append(now)
            return True, 0


# Module-level singleton
limiter = RateLimiter()
