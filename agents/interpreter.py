"""
Results interpretation agent.

Summarises Snowflake query results as a plain-language answer using Claude.
The `model` parameter mirrors the one used in sql_gen so routing is consistent
across the full pipeline.
"""

from typing import Any

import anthropic

from agents.router import OPUS

_client = anthropic.Anthropic()

_MAX_ROWS_TO_MODEL = 50
_MAX_HISTORY = 3

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
    history: list[dict] | None = None,
    model: str = OPUS,
) -> str:
    """
    Produce a plain-language summary of `results`.

    Parameters
    ----------
    history     Last N conversation turns; helps the model reference prior answers.
    model       Claude model ID from agents.router.
    """
    if not results:
        return "The query returned no results."

    preview = results[:_MAX_ROWS_TO_MODEL]
    rows_text = "\n".join(str(row) for row in preview)
    truncation = (
        f"\n(Showing first {_MAX_ROWS_TO_MODEL} of {len(results)} total rows.)"
        if len(results) > _MAX_ROWS_TO_MODEL
        else ""
    )

    content = ""
    if history:
        prior = "\n".join(
            f"- Q: {t['question']} → {t['answer']}"
            for t in history[-_MAX_HISTORY:]
        )
        content += f"Prior conversation context:\n{prior}\n\n"

    content += (
        f"Question: {question}\n\n"
        f"SQL:\n{sql}\n\n"
        f"Results:\n{rows_text}{truncation}"
    )

    response = _client.messages.create(
        model=model,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )
    for block in response.content:
        if block.type == "text":
            return block.text.strip()
    return ""
