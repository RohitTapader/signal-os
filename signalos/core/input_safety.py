"""Validates free-text Telegram input before it touches storage or a prompt.

Category selection happens via bounded buttons (never free text), so this
module only guards the optional elaboration / regenerate-angle text.
"""

from __future__ import annotations

import re

from signalos.core.feedback_guardrails import MAX_FEEDBACK_TEXT_LENGTH, UNSAFE_TEXT_PATTERNS

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in UNSAFE_TEXT_PATTERNS]


def sanitize_user_text(text: str | None) -> tuple[str | None, bool]:
    """Returns (clean_text, is_safe). clean_text is None whenever is_safe is False
    or the input was empty after cleaning — callers must never use the raw text."""
    if not text:
        return None, False

    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t").strip()
    if not cleaned:
        return None, False

    cleaned = cleaned[:MAX_FEEDBACK_TEXT_LENGTH]

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(cleaned):
            return None, False

    return cleaned, True
