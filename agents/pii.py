"""
PII (Personally Identifiable Information) detection.

Scans query result rows for common PII patterns before they are returned to
the client. Returns a list of detected PII type names so the API layer can
attach a warning to the response.

Detected types
--------------
email           Standard email addresses
ssn             US Social Security Numbers (NNN-NN-NNNN)
phone           US/international phone numbers
credit_card     16-digit card numbers (with or without separators)

Only string-typed cell values are scanned; numeric columns are skipped.
The scan short-circuits once all known PII types have been detected.
"""

import re
from typing import Any

_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(
        r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
    ),
    "ssn": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),
    "phone": re.compile(
        r"\b(\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b"
    ),
    "credit_card": re.compile(
        r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"
    ),
}


def scan(rows: list[dict[str, Any]]) -> list[str]:
    """
    Scan `rows` for PII.

    Returns a sorted list of detected PII type names, e.g. ["email", "phone"].
    Returns an empty list if no PII is found.
    """
    detected: set[str] = set()
    all_types = set(_PATTERNS)

    for row in rows:
        if detected == all_types:
            break  # found everything possible — stop early
        for val in row.values():
            if not isinstance(val, str):
                continue
            for pii_type, pattern in _PATTERNS.items():
                if pii_type not in detected and pattern.search(val):
                    detected.add(pii_type)

    return sorted(detected)
