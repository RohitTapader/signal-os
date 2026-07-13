"""Bounded preference-state read/write layer.

All mutation goes through apply_bounded_delta / apply_category_bias, both of
which spend from consume_daily_change_budget's shared per-chat daily budget
before touching a value, and both of which clamp to
signalos.core.feedback_guardrails.PREFERENCE_BOUNDS. There is no code path
here that writes an unbounded or unlogged change.
"""

from __future__ import annotations

import json
from datetime import date, datetime

from signalos.core.db import SessionLocal, UserPreferenceState
from signalos.core.feedback_guardrails import MAX_PREFERENCE_EVENTS_PER_DAY, PREFERENCE_BOUNDS
from signalos.core.logging import log_json
from signalos.core.models import PreferenceProfile


def _get_or_create_row(db, chat_id: str) -> UserPreferenceState:
    row = db.get(UserPreferenceState, chat_id)
    if row:
        return row
    row = UserPreferenceState(chat_id=chat_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_preference_profile(chat_id: str) -> PreferenceProfile:
    db = SessionLocal()
    try:
        row = db.get(UserPreferenceState, chat_id)
        if not row:
            return PreferenceProfile()
        return PreferenceProfile(
            technical_depth=row.technical_depth,
            summary_length=row.summary_length,
            recommendation_strictness=row.recommendation_strictness,
            source_trust_bias=row.source_trust_bias,
            category_bias=json.loads(row.category_bias_json or "{}"),
        )
    finally:
        db.close()


def consume_daily_change_budget(chat_id: str) -> bool:
    """Shared bounded budget across every preference/threshold adjustment for
    a chat, reset daily. Returns False when today's budget is already spent —
    callers must treat that as a no-op, not an error."""
    today = date.today().isoformat()
    db = SessionLocal()
    try:
        row = _get_or_create_row(db, chat_id)
        if row.daily_change_date != today:
            row.daily_change_date = today
            row.daily_change_count = 0
        if row.daily_change_count >= MAX_PREFERENCE_EVENTS_PER_DAY:
            db.commit()
            log_json("guardrail_blocked", reason="daily_change_cap", chat_id=chat_id)
            return False
        row.daily_change_count += 1
        db.commit()
        return True
    finally:
        db.close()


def apply_bounded_delta(chat_id: str, field: str, delta: float) -> bool:
    """Apply one pre-approved, fixed-step delta to a single bounded field.
    Returns False (no-op, logged) if the field is unknown or the daily
    change budget is already spent."""
    if field not in PREFERENCE_BOUNDS:
        log_json("guardrail_violation", reason="unknown_preference_field", field=field, chat_id=chat_id)
        return False
    if not consume_daily_change_budget(chat_id):
        return False

    lo, hi = PREFERENCE_BOUNDS[field]
    db = SessionLocal()
    try:
        row = _get_or_create_row(db, chat_id)
        new_value = max(lo, min(hi, getattr(row, field) + delta))
        setattr(row, field, new_value)
        row.updated_at = datetime.utcnow()
        db.commit()
        log_json("preference_updated", chat_id=chat_id, field=field, delta=delta, new_value=new_value)
        return True
    finally:
        db.close()


def apply_category_bias(chat_id: str, category_tags: list[str], delta: float, max_keys: int = 6) -> bool:
    """Nudge item-selection bias for a small, bounded set of category tags
    (e.g. 'official', 'research'). Bounded state size and per-key magnitude."""
    if not category_tags:
        return False
    if not consume_daily_change_budget(chat_id):
        return False

    lo, hi = PREFERENCE_BOUNDS["category_bias_item"]
    db = SessionLocal()
    try:
        row = _get_or_create_row(db, chat_id)
        bias = json.loads(row.category_bias_json or "{}")
        for tag in category_tags[:max_keys]:
            current = bias.get(tag, 0.0)
            bias[tag] = max(lo, min(hi, current + delta))
        if len(bias) > max_keys:
            bias = dict(list(bias.items())[-max_keys:])
        row.category_bias_json = json.dumps(bias)
        row.updated_at = datetime.utcnow()
        db.commit()
        log_json("preference_updated", chat_id=chat_id, field="category_bias", tags=category_tags[:max_keys], delta=delta)
        return True
    finally:
        db.close()
