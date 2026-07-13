"""Governance policy for the Telegram feedback loop.

This module is the single source of truth for what feedback is allowed to do.
It is imported by signalos.core.preferences, signalos.core.input_safety, and
signalos.workflows.event_router — nothing in the feedback loop hardcodes a
category, bound, or step outside of this file. See docs/ADR/0005 for the
narrative version of this policy.
"""

from __future__ import annotations

# --- Allowed feedback categories -------------------------------------------------
# Selected via bounded Telegram buttons only — never inferred from free text —
# so the category itself can never be a prompt-injection vector.
FEEDBACK_CATEGORY_LABELS: dict[str, str] = {
    "too_technical": "🔬 Too technical",
    "too_verbose": "📝 Too verbose",
    "not_relevant": "🎯 Not relevant",
    "too_repetitive": "🔁 Too repetitive",
    "not_enough_new_information": "🆕 Not enough new info",
    "source_quality_issue": "📡 Source quality issue",
    "recommendation_issue": "⭐ Recommendation issue",
    "other": "❓ Other",
}
ALLOWED_FEEDBACK_CATEGORIES: frozenset[str] = frozenset(FEEDBACK_CATEGORY_LABELS)

# --- Bounded preference fields ----------------------------------------------------
# Hard min/max every write is clamped to, regardless of requested delta.
PREFERENCE_BOUNDS: dict[str, tuple[float, float]] = {
    "technical_depth": (0.0, 1.0),
    "summary_length": (0.0, 1.0),
    "recommendation_strictness": (0.0, 1.0),
    "source_trust_bias": (-0.2, 0.2),
    "category_bias_item": (-0.15, 0.15),  # bound applied per key inside category_bias
}

# Each category applies exactly one small, fixed-step delta to exactly one
# field — never an unbounded, compounding, or magnitude-scaled adjustment.
# categories not listed here (too_repetitive, not_enough_new_information)
# reuse the pre-existing bounded SystemSetting novelty-threshold tuning in
# event_router.py instead of the preference profile.
CATEGORY_PREFERENCE_STEP: dict[str, tuple[str, float] | None] = {
    "too_technical": ("technical_depth", -0.15),
    "too_verbose": ("summary_length", -0.15),
    "not_relevant": ("recommendation_strictness", 0.15),
    "recommendation_issue": ("recommendation_strictness", 0.10),
    "source_quality_issue": ("source_trust_bias", -0.05),
    "too_repetitive": None,
    "not_enough_new_information": None,
    "other": None,
}

NOVELTY_TUNING_CATEGORIES: frozenset[str] = frozenset({"too_repetitive", "not_enough_new_information"})

# Shared daily budget across ALL bounded adjustments for a chat (preference
# profile fields AND the novelty-threshold SystemSetting tuning). Each event
# is one fixed small step, so capping the count also caps total daily
# magnitude per field — this is what keeps adaptation "bounded, not arbitrary".
MAX_PREFERENCE_EVENTS_PER_DAY = 5

# --- Blocked actions ---------------------------------------------------------------
# Feedback handling can never do these, by construction — listed here for
# auditability, not as a runtime check (the code simply never implements them).
BLOCKED_ACTIONS: tuple[str, ...] = (
    "code_modification",
    "auto_deploy",
    "shell_or_system_execution",
    "database_schema_change",
    "arbitrary_config_key_write",
    "unbounded_preference_change",
    "auto_apply_repair_proposal",
)

# --- Free-text input safety ---------------------------------------------------------
MAX_FEEDBACK_TEXT_LENGTH = 800

# Basic prompt-injection / unsafe-content heuristics for free-text elaboration
# and regenerate-angle replies. Not a full jailbreak classifier — a cheap,
# zero-cost first filter; matching text is never stored or sent to an LLM.
UNSAFE_TEXT_PATTERNS: tuple[str, ...] = (
    r"ignore (all|any|previous|the) (prior )?instructions",
    r"disregard (all|any|previous|the) (prior )?instructions",
    r"system prompt",
    r"you are now",
    r"act as (a|an)",
    r"</?script",
    r"drop\s+table",
    r";\s*rm\s+-rf",
    r"\bexec\(",
    r"\beval\(",
    r"```",
)

# --- Fallback behavior --------------------------------------------------------------
# When feedback is ambiguous or unsafe: ask a clarifying question, never
# change preferences, and log a guardrail_violation SystemEvent for eval.
FALLBACK_MESSAGE_UNSAFE = (
    "That doesn't look like plain feedback text, so I skipped saving it — nothing was changed. "
    "Could you rephrase in a short plain sentence?"
)
FALLBACK_MESSAGE_AMBIGUOUS = (
    "I couldn't tell what you meant. Could you rephrase, or use one of the buttons instead?"
)
