import anthropic

from db.schema_cache import get_schema_text

_client = anthropic.Anthropic()

_SYSTEM = (
    "You are a database schema analyst. "
    "Given a user question and a full Snowflake schema, return only the table and column "
    "definitions that are relevant to answering the question. "
    "Preserve the exact input format (Table: / column lines). "
    "Do not add commentary or explanation — output schema lines only."
)


def identify_relevant_schema(question: str) -> str:
    """
    Use Haiku to filter the full schema down to tables relevant to the question.
    Returns a schema string suitable for the SQL generation prompt.
    """
    full_schema = get_schema_text()

    response = _client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2048,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": f"Question: {question}\n\nFull schema:\n{full_schema}",
            }
        ],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return full_schema  # fall back to full schema if model returns nothing
