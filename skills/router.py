"""
Skill router.

Matches a natural-language question to the best domain skill using keyword
scoring. Returns None when no skill reaches a minimum confidence threshold,
letting the generic agents handle the question unchanged.
"""

from skills import cohort_analysis, coding_standards, customer_segmentation, data_quality, financial_reporting, inventory_analysis, performance_optimization, revenue_trend, user_behavior
from skills.base import Skill

_SKILLS: list[Skill] = [
    revenue_trend.skill,
    customer_segmentation.skill,
    inventory_analysis.skill,
    cohort_analysis.skill,
    coding_standards.skill,
    performance_optimization.skill,
    data_quality.skill,
    user_behavior.skill,
    financial_reporting.skill,
]

# Minimum keyword hits required before a skill is applied
_MIN_SCORE = 1


def match_skill(question: str) -> Skill | None:
    """
    Return the highest-scoring Skill for `question`, or None.

    Scoring: one point per keyword found in the lowercased question.
    Ties are broken by skill order (first registered wins).
    """
    q = question.lower()
    best: tuple[int, Skill] | None = None
    for skill in _SKILLS:
        score = sum(1 for kw in skill.keywords if kw in q)
        if score >= _MIN_SCORE and (best is None or score > best[0]):
            best = (score, skill)
    return best[1] if best else None
