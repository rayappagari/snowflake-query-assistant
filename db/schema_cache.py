import time

from db.connection import execute_query

_TTL = 300  # seconds — refresh schema every 5 minutes
_cache: dict = {"text": None, "fetched_at": 0.0}


def get_schema_text() -> str:
    """
    Return a human-readable schema dump for the current schema.
    Cached for _TTL seconds so repeated questions don't hammer INFORMATION_SCHEMA.
    """
    now = time.time()
    if _cache["text"] and now - _cache["fetched_at"] < _TTL:
        return _cache["text"]

    rows = execute_query(
        """
        SELECT table_name, column_name, data_type, comment
        FROM information_schema.columns
        WHERE table_schema = CURRENT_SCHEMA()
        ORDER BY table_name, ordinal_position
        """
    )

    lines: list[str] = []
    current_table: str | None = None
    for row in rows:
        tname = row["TABLE_NAME"]
        col = row["COLUMN_NAME"]
        dtype = row["DATA_TYPE"]
        comment = row.get("COMMENT") or ""
        if tname != current_table:
            lines.append(f"\nTable: {tname}")
            current_table = tname
        suffix = f"  -- {comment}" if comment else ""
        lines.append(f"  {col} ({dtype}){suffix}")

    schema_text = "\n".join(lines).strip()
    _cache["text"] = schema_text
    _cache["fetched_at"] = now
    return schema_text


def invalidate() -> None:
    """Force a fresh fetch on the next call."""
    _cache["fetched_at"] = 0.0
