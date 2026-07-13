from __future__ import annotations

import json

from signalos.core.llm import call_model
from signalos.core.models import FeedbackClassification


def classify_feedback(text: str) -> FeedbackClassification:
    raw, usage = call_model(
        "feedback_agent",
        text,
        skill_name="feedback-classifier",
        json_mode=True,
    )
    data = json.loads(raw)
    return FeedbackClassification(**data)
