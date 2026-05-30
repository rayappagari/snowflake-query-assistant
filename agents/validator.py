from db.connection import explain_query


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate SQL using Snowflake's EXPLAIN without executing the query.
    Returns (True, explain_output) on success, (False, error_message) on failure.
    """
    try:
        output = explain_query(sql)
        return True, output
    except Exception as exc:
        return False, str(exc)
