"""Offline metrics for the Telegram feedback loop.

Pure functions over already-collected data (FeedbackEvent rows, SystemEvent
logs) — mirrors the pattern in evaluation/metrics.py and evaluation/offline.py.
Not wired into the live pipeline; run standalone against exported data.
"""

from __future__ import annotations


def feedback_category_accuracy(labeled: list[tuple[str, str]]) -> float:
    """labeled: list of (true_category, selected_or_predicted_category).
    For button-driven feedback, true == selected by construction; this is
    mainly useful for the free-text classify_feedback() path."""
    if not labeled:
        return 0.0
    correct = sum(1 for true, predicted in labeled if true == predicted)
    return round(correct / len(labeled), 4)


def preference_adaptation_quality(before: dict[str, float], after: dict[str, float], expected_direction: dict[str, int]) -> float:
    """expected_direction: field -> +1 (should increase), -1 (should decrease), 0 (should not change).
    Returns the fraction of fields that moved in the expected direction (or
    correctly stayed put)."""
    if not expected_direction:
        return 0.0
    correct = 0
    for field, direction in expected_direction.items():
        delta = after.get(field, 0.0) - before.get(field, 0.0)
        if direction == 0:
            correct += 1 if abs(delta) < 1e-9 else 0
        elif direction > 0:
            correct += 1 if delta > 0 else 0
        else:
            correct += 1 if delta < 0 else 0
    return round(correct / len(expected_direction), 4)


def regenerate_success_rate(outcomes: list[bool]) -> float:
    """outcomes: True where a regenerate request completed without raising
    (independent of whether it found new content — "no new information" is
    a successful, correct outcome, not a failure)."""
    if not outcomes:
        return 0.0
    return round(sum(outcomes) / len(outcomes), 4)


def digest_satisfaction_improvement(positive_rate_before: float, positive_rate_after: float) -> float:
    """Change in the share of 'good digest' vs 'did not like' feedback
    between two periods. Positive means satisfaction improved."""
    return round(positive_rate_after - positive_rate_before, 4)


def guardrail_violation_rate(total_events: int, violations: int) -> float:
    if total_events == 0:
        return 0.0
    return round(violations / total_events, 4)
