"""
Model complexity router.

Classifies a natural-language question as 'simple' or 'complex' and returns
the appropriate Claude model ID — without making an additional API call.

Simple queries (fast lookups, schema introspection) → Haiku (cheap, fast)
Complex queries (multi-table joins, aggregations, trends) → Opus 4.8 (capable)

The classifier uses regex heuristics. When in doubt it defaults to Opus.
"""

import re

HAIKU = "claude-haiku-4-5"
OPUS = "claude-opus-4-8"

# Strong signals that a query is analytically complex
_COMPLEX_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(trend|forecast|predict|growth|decline|seasonality)\b",
        r"\b(year.?over.?year|month.?over.?month|yoy|mom|qoq)\b",
        r"\b(percentile|quartile|standard.?deviation|variance|correlation)\b",
        r"\b(compare|vs\.?|versus|against|benchmark)\b",
        r"\b(running total|cumulative|rolling average|moving average)\b",
        r"\b(rank|dense_rank|ntile|window function)\b",
        r"\b(revenue|profit|margin|churn|retention|conversion rate)\b",
        r"\b(cohort|funnel|attribution|segmentation)\b",
        r"\b(multiple|across|join|between .+ and .+)\b",
    ]
]

# Strong signals that a query is a simple lookup
_SIMPLE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"^(list|show me|give me|what are|how many|count)\b",
        r"\b(all tables|schema|columns in|describe|list tables)\b",
        r"^show\s+(tables|columns|schemas|databases)\b",
    ]
]


def choose_model(question: str) -> str:
    """
    Return the Claude model ID most appropriate for `question`.

    Uses lightweight regex heuristics — no API call.
    Defaults to Opus when complexity is ambiguous.
    """
    is_simple = any(p.match(question) for p in _SIMPLE_PATTERNS)
    complex_signals = sum(1 for p in _COMPLEX_PATTERNS if p.search(question))

    if is_simple and complex_signals == 0:
        return HAIKU
    return OPUS
