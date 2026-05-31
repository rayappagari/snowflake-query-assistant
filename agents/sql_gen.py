import anthropic

_client = anthropic.Anthropic()

_SYSTEM = (
    "You are an expert Snowflake SQL developer. "
    "Generate a single, valid Snowflake SQL SELECT query that answers the user's question. "
    "Use only tables and columns present in the provided schema. "
    "Return ONLY the SQL statement — no explanation, no markdown fences, no trailing semicolon."
)

_MAX_HISTORY = 5


def _format_history(history: list[dict]) -> str:
    lines = []
    for i, turn in enumerate(history[-_MAX_HISTORY:], 1):
        lines.append(f"Turn {i}:")
        lines.append(f"  Question: {turn['question']}")
        lines.append(f"  SQL: {turn['sql']}")
        lines.append(f"  Answer: {turn['answer']}")
    return "\n".join(lines)


def generate_sql(
    question: str,
    schema: str,
    previous_error: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """
    Generate a Snowflake SQL query for the given question and schema context.
    Pass previous_error to ask the model to fix a prior attempt.
    Pass history for conversation context so follow-up questions resolve correctly.
    """
    user_content = f"Schema:\n{schema}\n\n"

    if history:
        user_content += f"Conversation history (use for context on follow-up questions):\n{_format_history(history)}\n\n"

    user_content += f"Question: {question}"

    if previous_error:
        user_content += (
            f"\n\nPrevious attempt failed with this error — please fix it:\n{previous_error}"
        )

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""
