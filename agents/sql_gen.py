"""
SQL generation agent.

Converts a natural-language question + schema context into a valid Snowflake
SELECT query using Claude.

The `model` parameter is set by agents/router.py — simple questions use Haiku,
complex analytical questions use Opus 4.8.

The system prompt carries cache_control so it is reused across calls within
the 5-minute Anthropic prompt-cache TTL window.
"""

import anthropic

from agents.router import OPUS

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
    model: str = OPUS,
) -> str:
    """
    Generate a Snowflake SQL query for `question` given `schema`.

    Parameters
    ----------
    previous_error  Error from the last attempt; appended so the model can fix it.
    history         Last N conversation turns for follow-up question resolution.
    model           Claude model ID from agents.router (Haiku or Opus).
    """
    user_content = f"Schema:\n{schema}\n\n"

    if history:
        user_content += (
            f"Conversation history (use for context on follow-up questions):\n"
            f"{_format_history(history)}\n\n"
        )

    user_content += f"Question: {question}"

    if previous_error:
        user_content += (
            f"\n\nPrevious attempt failed — please fix:\n{previous_error}"
        )

    kwargs = {"thinking": {"type": "adaptive"}, "output_config": {"effort": "high"}} if model == OPUS else {}
    response = _client.messages.create(
        model=model,
        max_tokens=2048,
        **kwargs,
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
