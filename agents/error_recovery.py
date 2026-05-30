import anthropic

_client = anthropic.Anthropic()

_SYSTEM = (
    "You are a Snowflake SQL expert. "
    "Given a failing SQL query, its exact error message, and the database schema, "
    "return a corrected SQL query. "
    "Return ONLY the SQL statement — no explanation, no markdown fences, no trailing semicolon."
)


def suggest_fix(sql: str, error: str, schema: str) -> str:
    """Return a corrected SQL query based on the execution error."""
    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Schema:\n{schema}\n\n"
                    f"Failing SQL:\n{sql}\n\n"
                    f"Error:\n{error}"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return sql  # return original if model produces nothing
