"""
Skill dataclass.

A Skill bundles domain-specific context that is injected into the sql_gen
and interpreter prompts — without changing the agents themselves.
"""

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Skill:
    name: str
    description: str
    # Injected into the user message of sql_gen + interpreter
    prompt_hint: str
    # Common SQL patterns for this domain; appended to the sql_gen user message
    sql_hint: str
    # Optional row-level post-processor called before interpretation
    postprocess: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None
    # Keywords used by skills/router.py for matching
    keywords: list[str] = field(default_factory=list)
