from typing import Any

import anthropic

_client = anthropic.Anthropic()

_MAX_ROWS_TO_MODEL = 50

_SYSTEM = (
    "You are a concise data analyst. "
    "Given a user question, the SQL that was executed, and its results, "
    "provide a clear natural-language summary of the findings. "
    "Flag anomalies such as unexpected nulls, zero values, or unusually large numbers. "
    "Keep the response short — two to four sentences unless the data warrants more detail."
)


def interpret_results(
    question: str,
    sql: str,
    results: list[dict[str, Any]],
) -> str:
    if not results:
        return "The query returned no results."

    preview = results[:_MAX_ROWS_TO_MODEL]
    rows_text = "\n".join(str(row) for row in preview)
    truncation = (
        f"\n(Showing first {_MAX_ROWS_TO_MODEL} of {len(results)} total rows.)"
        if len(results) > _MAX_ROWS_TO_MODEL
        else ""
    )

    response = _client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"SQL:\n{sql}\n\n"
                    f"Results:\n{rows_text}{truncation}"
                ),
            }
        ],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""
