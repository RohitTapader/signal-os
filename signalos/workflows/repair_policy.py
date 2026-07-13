from __future__ import annotations

from signalos.core.models import FeedbackClassification


def decide_repair_path(classification: FeedbackClassification) -> str:
    if classification.category in ("content_accuracy", "wrong_novelty_call"):
        return "config_or_data"
    if classification.category in ("source_broken", "slide_rendering_bug"):
        return "proposal_only"
    return "review_only"
