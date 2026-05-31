from snowflake.connector.errors import ProgrammingError

from db.connection import explain_query

# Snowflake SQLSTATE 42501 = insufficient privileges.
# If EXPLAIN itself lacks permission, the SQL may still be valid — skip validation.
_PRIVILEGE_SQLSTATE = "42501"


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL using Snowflake's EXPLAIN without executing the query.
    Returns (True, explain_output) on success, (False, error_message) on failure.
    """
    try:
        output = explain_query(sql)
        return True, output
    except ProgrammingError as exc:
        if exc.sqlstate == _PRIVILEGE_SQLSTATE:
            return True, "validation skipped (insufficient EXPLAIN privilege)"
        return False, str(exc)
    except Exception as exc:
        return False, str(exc)
