"""
Prometheus metrics for the Snowflake Query Assistant.

Metrics are exposed at GET /metrics in the Prometheus text format.
Connect Grafana (or any Prometheus-compatible scraper) to that endpoint.

Defined metrics
---------------
query_requests_total        Counter   labelled by status, cache_hit, model
query_latency_seconds       Histogram custom buckets matching pipeline latency
cache_hits_total            Counter   total cache hits
rate_limit_exceeded_total   Counter   requests rejected by the rate limiter
pii_detections_total        Counter   labelled by pii_type
circuit_breaker_state       Gauge     0=closed, 1=half_open, 2=open
active_users_total          Gauge     count of rows in the users table

Usage
-----
Call ``record_query()`` after each /query request to update the counters.
Import and increment ``RATE_LIMITED`` when a request is rate-limited.
Call ``CIRCUIT_STATE.set(...)`` from the /query handler after each pipeline run.
"""

import logging

from fastapi.responses import Response

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _PROM_AVAILABLE = True
except ImportError:
    logger.warning("prometheus_client not installed — metrics endpoint disabled")
    _PROM_AVAILABLE = False

# ── Metric definitions ────────────────────────────────────────────────────────

if _PROM_AVAILABLE:
    QUERY_TOTAL = Counter(
        "query_requests_total",
        "Total queries handled by the pipeline",
        ["status", "cache_hit", "model"],
    )

    QUERY_LATENCY = Histogram(
        "query_latency_seconds",
        "End-to-end query latency including all agent stages",
        buckets=[1, 3, 5, 10, 20, 30, 60, 120],
    )

    CACHE_HITS = Counter(
        "cache_hits_total",
        "Number of requests served from the result cache",
    )

    RATE_LIMITED = Counter(
        "rate_limit_exceeded_total",
        "Number of requests rejected by the rate limiter",
    )

    PII_DETECTED = Counter(
        "pii_detections_total",
        "Number of PII items detected in query results",
        ["pii_type"],
    )

    CIRCUIT_STATE = Gauge(
        "circuit_breaker_state",
        "Snowflake circuit breaker state (0=closed, 1=half_open, 2=open)",
    )

    ACTIVE_USERS = Gauge(
        "active_users_total",
        "Number of active user accounts in the database",
    )
else:
    # Stub objects so imports never crash even without prometheus_client
    class _Stub:
        def labels(self, **kwargs):
            return self

        def inc(self, *a, **kw):
            pass

        def observe(self, *a, **kw):
            pass

        def set(self, *a, **kw):
            pass

    QUERY_TOTAL = _Stub()          # type: ignore[assignment]
    QUERY_LATENCY = _Stub()        # type: ignore[assignment]
    CACHE_HITS = _Stub()           # type: ignore[assignment]
    RATE_LIMITED = _Stub()         # type: ignore[assignment]
    PII_DETECTED = _Stub()         # type: ignore[assignment]
    CIRCUIT_STATE = _Stub()        # type: ignore[assignment]
    ACTIVE_USERS = _Stub()         # type: ignore[assignment]


# ── Public helpers ────────────────────────────────────────────────────────────

_CB_STATE_MAP = {"closed": 0, "half_open": 1, "open": 2}


def record_query(
    latency_ms: int,
    success: bool,
    cache_hit: bool,
    model: str,
    pii_types: list[str],
) -> None:
    """
    Update all query-related counters after a pipeline run.

    Parameters
    ----------
    latency_ms:  Wall-clock time for the full pipeline in milliseconds.
    success:     True if the query returned results; False on error.
    cache_hit:   True if results came from the in-process or Redis cache.
    model:       Model ID used for SQL generation / interpretation.
    pii_types:   List of PII type names detected (e.g. ["email", "ssn"]).
    """
    status = "success" if success else "error"
    cache_str = "true" if cache_hit else "false"

    QUERY_TOTAL.labels(status=status, cache_hit=cache_str, model=model).inc()
    QUERY_LATENCY.observe(latency_ms / 1000.0)

    if cache_hit:
        CACHE_HITS.inc()

    for pii_type in (pii_types or []):
        PII_DETECTED.labels(pii_type=pii_type).inc()


def get_metrics_response() -> Response:
    """
    Generate and return the Prometheus text-format metrics response.

    Returns a plain-text 200 response when prometheus_client is available,
    or a 501 Not Implemented response when it is not installed.
    """
    if not _PROM_AVAILABLE:
        return Response(
            content="prometheus_client not installed",
            status_code=501,
            media_type="text/plain",
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
