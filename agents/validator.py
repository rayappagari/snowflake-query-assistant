import re

from snowflake.connector.errors import ProgrammingError

from db.connection import explain_query

# Snowflake SQLSTATE 42501 = insufficient privileges.
# If EXPLAIN itself lacks permission, the SQL may still be valid — skip validation.
_PRIVILEGE_SQLSTATE = "42501"

# Only SELECT and WITH (CTEs) are permitted.
_READONLY_START = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)

# Catch dangerous keywords even if they appear inside a WITH chain.
_BLOCKED_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|MERGE|REPLACE|CALL|EXEC|EXECUTE)\b",
    re.IGNORECASE,
)


def _enforce_readonly(sql: str) -> tuple[bool, str]:
    if not _READONLY_START.match(sql):
        first_word = (sql.strip().split() or ["EMPTY"])[0].upper()
        return False, f"Blocked: only SELECT queries are permitted (got {first_word})"
    match = _BLOCKED_KEYWORDS.search(sql)
    if match:
        return False, f"Blocked: disallowed keyword '{match.group(0).upper()}' in query"
    return True, ""


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    1. Enforce read-only: reject anything that isn't SELECT/WITH.
    2. Validate with Snowflake's EXPLAIN (no credits consumed).
    Returns (True, message) on pass, (False, error) on failure.
    """
    ok, msg = _enforce_readonly(sql)
    if not ok:
        return False, msg

    try:
        output = explain_query(sql)
        return True, output
    except ProgrammingError as exc:
        if exc.sqlstate == _PRIVILEGE_SQLSTATE:
            return True, "validation skipped (insufficient EXPLAIN privilege)"
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)
