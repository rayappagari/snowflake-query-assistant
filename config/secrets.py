"""
Secrets loader with a priority chain: AWS Secrets Manager → HashiCorp Vault → env vars.

For most deployments, environment variables are sufficient and no external
secret store is needed.  The external sources are opt-in: configure them only
when you need centralised rotation, auditing, or access-control policies.

Priority chain
--------------
1. AWS Secrets Manager  (when AWS_SECRET_ARN is set and boto3 is installed)
2. HashiCorp Vault      (when VAULT_ADDR + VAULT_TOKEN are set and httpx is installed)
3. Environment variable (always the final fallback)

Caching
-------
Secrets fetched from external stores are cached in memory for 5 minutes to
avoid repeated outbound calls on every request.  Call ``invalidate_cache()``
to force a refresh (e.g. after a manual rotation).

Environment variables
---------------------
AWS_SECRET_ARN      ARN of the Secrets Manager secret (JSON key-value store).
VAULT_ADDR          Base URL of the Vault server, e.g. https://vault.example.com.
VAULT_TOKEN         Vault authentication token.
VAULT_PATH          Path inside the KV-v2 mount (default: secret/data/snowflake-agent).
"""

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL = 300  # seconds

_cache: dict[str, tuple[float, str]] = {}  # key → (fetched_at, value)
_cache_lock = threading.Lock()

# Pre-loaded AWS / Vault bulk payloads so we don't call the API once per key
_aws_payload: dict[str, Any] | None = None
_aws_payload_ts: float = 0.0
_vault_payload: dict[str, Any] | None = None
_vault_payload_ts: float = 0.0
_payload_lock = threading.Lock()


# ── AWS Secrets Manager ───────────────────────────────────────────────────────

def _load_aws() -> dict[str, Any] | None:
    """
    Fetch all key-value pairs from the AWS Secrets Manager secret.

    The secret must be stored as a JSON object.  Returns None when boto3 is
    not installed, AWS_SECRET_ARN is not set, or the API call fails.
    """
    global _aws_payload, _aws_payload_ts

    arn = os.environ.get("AWS_SECRET_ARN", "")
    if not arn:
        return None

    now = time.monotonic()
    with _payload_lock:
        if _aws_payload is not None and now - _aws_payload_ts < _CACHE_TTL:
            return _aws_payload

        try:
            import boto3  # noqa: PLC0415
            import json   # noqa: PLC0415
        except ImportError:
            logger.debug("boto3 not installed — AWS Secrets Manager disabled")
            return None

        try:
            client = boto3.client("secretsmanager")
            resp = client.get_secret_value(SecretId=arn)
            secret_str = resp.get("SecretString", "{}")
            _aws_payload = json.loads(secret_str)
            _aws_payload_ts = now
            logger.debug("AWS Secrets Manager payload loaded (%d keys)", len(_aws_payload))
            return _aws_payload
        except Exception as exc:  # noqa: BLE001
            logger.warning("AWS Secrets Manager fetch failed: %s", exc)
            return None


# ── HashiCorp Vault ───────────────────────────────────────────────────────────

def _load_vault() -> dict[str, Any] | None:
    """
    Fetch all key-value pairs from HashiCorp Vault (KV-v2 mount).

    Returns None when VAULT_ADDR / VAULT_TOKEN are not set, httpx is not
    installed, or the API call fails.
    """
    global _vault_payload, _vault_payload_ts

    addr = os.environ.get("VAULT_ADDR", "")
    token = os.environ.get("VAULT_TOKEN", "")
    if not addr or not token:
        return None

    now = time.monotonic()
    with _payload_lock:
        if _vault_payload is not None and now - _vault_payload_ts < _CACHE_TTL:
            return _vault_payload

        try:
            import httpx  # noqa: PLC0415
        except ImportError:
            logger.debug("httpx not installed — Vault disabled")
            return None

        path = os.environ.get("VAULT_PATH", "secret/data/snowflake-agent")
        url = f"{addr.rstrip('/')}/v1/{path}"
        try:
            resp = httpx.get(url, headers={"X-Vault-Token": token}, timeout=5)
            resp.raise_for_status()
            data = resp.json().get("data", {}).get("data", {})
            _vault_payload = data
            _vault_payload_ts = now
            logger.debug("Vault payload loaded from %s (%d keys)", path, len(data))
            return _vault_payload
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vault fetch failed (%s): %s", url, exc)
            return None


# ── Public API ────────────────────────────────────────────────────────────────

def get(key: str) -> str | None:
    """
    Return the value for *key* using the priority chain.

    Checks (in order):
    1. In-memory cache
    2. AWS Secrets Manager  (if AWS_SECRET_ARN set)
    3. HashiCorp Vault       (if VAULT_ADDR + VAULT_TOKEN set)
    4. Environment variable

    Parameters
    ----------
    key:
        The secret / environment variable name.

    Returns
    -------
    The value as a string, or None if not found in any source.
    """
    now = time.monotonic()

    # 1. In-memory cache
    with _cache_lock:
        entry = _cache.get(key)
        if entry is not None:
            ts, value = entry
            if now - ts < _CACHE_TTL:
                return value

    # 2. AWS Secrets Manager
    aws = _load_aws()
    if aws and key in aws:
        value = str(aws[key])
        with _cache_lock:
            _cache[key] = (now, value)
        return value

    # 3. HashiCorp Vault
    vault = _load_vault()
    if vault and key in vault:
        value = str(vault[key])
        with _cache_lock:
            _cache[key] = (now, value)
        return value

    # 4. Environment variable (always the fallback)
    env_value = os.environ.get(key)
    if env_value is not None:
        with _cache_lock:
            _cache[key] = (now, env_value)
    return env_value


def invalidate_cache() -> None:
    """Clear the in-memory secret cache, forcing fresh lookups on next call."""
    global _aws_payload, _vault_payload
    with _cache_lock:
        _cache.clear()
    with _payload_lock:
        _aws_payload = None
        _vault_payload = None
    logger.info("Secret cache invalidated")
