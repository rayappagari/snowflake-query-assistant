"""
Circuit breaker for Snowflake calls.

Protects the app from cascading failures when Snowflake is degraded.

States
------
CLOSED    Normal operation — requests pass through.
OPEN      Service failing — requests are rejected immediately with an error.
HALF_OPEN Recovery probe — one request is allowed through to test the service.

Transitions
-----------
CLOSED    → OPEN      after `failure_threshold` consecutive failures
OPEN      → HALF_OPEN after `recovery_timeout` seconds have elapsed
HALF_OPEN → CLOSED    on a successful probe
HALF_OPEN → OPEN      on a failed probe (resets the timer)

Environment variables
---------------------
CB_FAILURE_THRESHOLD    Consecutive failures before opening (default: 5)
CB_RECOVERY_TIMEOUT     Seconds before attempting recovery (default: 60)
"""

import os
import threading
import time

_FAILURE_THRESHOLD = int(os.environ.get("CB_FAILURE_THRESHOLD", "5"))
_RECOVERY_TIMEOUT = float(os.environ.get("CB_RECOVERY_TIMEOUT", "60"))


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = _FAILURE_THRESHOLD,
        recovery_timeout: float = _RECOVERY_TIMEOUT,
    ) -> None:
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._state = self.CLOSED
        self._failures = 0
        self._opened_at: float | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and self._opened_at is not None:
                if time.monotonic() - self._opened_at >= self._timeout:
                    self._state = self.HALF_OPEN
            return self._state

    def call(self, func, *args, **kwargs):
        """
        Invoke `func(*args, **kwargs)` through the circuit breaker.
        Raises RuntimeError immediately if the breaker is OPEN.
        """
        current = self.state
        if current == self.OPEN:
            raise RuntimeError(
                "Snowflake circuit breaker is OPEN — service unavailable. "
                f"Will attempt recovery in ~{self._timeout:.0f}s."
            )

        try:
            result = func(*args, **kwargs)
            with self._lock:
                self._failures = 0
                self._state = self.CLOSED
            return result
        except Exception:
            with self._lock:
                self._failures += 1
                if self._failures >= self._threshold or current == self.HALF_OPEN:
                    self._state = self.OPEN
                    self._opened_at = time.monotonic()
            raise


# Module-level singleton shared across threads within a process
snowflake_breaker = CircuitBreaker()
