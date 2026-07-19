from __future__ import annotations

import json
from datetime import datetime

from signalos.agents.feedback_agent import classify_feedback
from signalos.agents.rca_agent import analyze_root_cause
from signalos.agents.repair_agent import draft_repair_proposal
from signalos.core.config import settings
from signalos.core.db import (
    FeedbackEvent,
    PendingInteraction,
    RepairProposalRow,
    SessionLocal,
    SystemEvent,
    SystemSetting,
)
from signalos.core.feedback_guardrails import (
    ALLOWED_FEEDBACK_CATEGORIES,
    CATEGORY_PREFERENCE_STEP,
    FALLBACK_MESSAGE_UNSAFE,
    FEEDBACK_CATEGORY_LABELS,
    NOVELTY_TUNING_CATEGORIES,
)
from signalos.core.input_safety import sanitize_user_text
from signalos.core.llm import BudgetExceededError
from signalos.core.logging import log_json
from signalos.core.models import FeedbackClassification
from signalos.core.preferences import apply_bounded_delta, apply_category_bias, consume_daily_change_budget, set_recent_feedback_note
from signalos.workflows.pipeline import regenerate_from_cache, send_to_telegram
from signalos.workflows.telegram import (
    answer_callback_query,
    ask_feedback_category,
    ask_feedback_elaboration,
    ask_regenerate_angle,
    ask_regenerate_mode,
    notify_fix_proposal,
    send_message,
)


def _upsert_setting(db, key: str, value: str) -> None:
    row = db.get(SystemSetting, key)
    if row:
        row.value = value
    else:
        row = SystemSetting(key=key, value=value)
        db.add(row)
    db.commit()


def _set_pending(db, chat_id: str, kind: str, context: dict) -> None:
    row = db.get(PendingInteraction, chat_id)
    if row:
        row.kind = kind
        row.context_json = json.dumps(context)
        row.created_at = datetime.utcnow()
    else:
        db.add(PendingInteraction(chat_id=chat_id, kind=kind, context_json=json.dumps(context)))
    db.commit()


def _clear_pending(db, chat_id: str) -> None:
    row = db.get(PendingInteraction, chat_id)
    if row:
        db.delete(row)
        db.commit()


def _get_pending(db, chat_id: str) -> PendingInteraction | None:
    return db.get(PendingInteraction, chat_id)


def _no_new_info_message(summary: dict) -> str:
    if summary["ingested"] == 0:
        return "Couldn't reach any sources just now — nothing to regenerate. Try again shortly."
    return "There is no new information available for today. Everything from your sources has already been covered."


def _send_regenerated_digest(chat_id: str, summary: dict) -> None:
    if not summary["digest_items"]:
        send_message(chat_id, _no_new_info_message(summary))
        return
    sent = send_to_telegram(summary["digest_items"], run_id=summary["run_id"])
    if sent == 0:
        send_message(
            chat_id,
            f"Found {len(summary['digest_items'])} item(s) today, but none reached Read/Skim priority — "
            "filed away for reference rather than sent.",
        )
        return
    send_message(chat_id, f"Regenerated — {sent} item(s) sent above.")


def route_telegram_update(update: dict) -> None:
    db = SessionLocal()
    try:
        if "callback_query" in update:
            cb = update["callback_query"]
            data = cb.get("data", "")
            callback_id = cb["id"]
            chat_id = str(cb["message"]["chat"]["id"])

            answer_callback_query(callback_id, "Received")

            if data == "feedback_good":
                db.add(FeedbackEvent(event_type="positive", text=None, payload_json=json.dumps(update)))
                db.commit()
                try:
                    # Positive reinforcement: nudge today's categories up slightly so
                    # future digests lean into the same pattern of content, mirroring
                    # the negative nudge on "not_relevant" below but in reverse.
                    _apply_item_selection_bias(chat_id, delta=0.05)
                except Exception as exc:
                    log_json("feedback_handling_error", stage="positive_reinforcement", error=str(exc), chat_id=chat_id)
                send_message(chat_id, "Thanks — logged as positive feedback, future digests will lean into this.")
                return

            if data == "feedback_bad":
                ask_feedback_category(chat_id)
                return

            if data.startswith("fb_cat:"):
                _handle_feedback_category(db, chat_id, data.split(":", 1)[1])
                return

            if data == "regenerate_today":
                ask_regenerate_mode(chat_id)
                return

            if data == "regen_mode:general":
                _handle_regenerate_general(db, chat_id)
                return

            if data == "regen_mode:specific":
                _set_pending(db, chat_id, "awaiting_regenerate_angle", {"attempts": 0})
                ask_regenerate_angle(chat_id)
                return

            if data.startswith("approve_fix:"):
                proposal_id = int(data.split(":", 1)[1])
                proposal = db.get(RepairProposalRow, proposal_id)
                if proposal:
                    proposal.status = "approved"
                    proposal.reviewed_at = datetime.utcnow()
                    db.commit()
                    send_message(chat_id, f"Approved fix proposal #{proposal_id}. Code changes still require review/merge.")
                return

            if data.startswith("reject_fix:"):
                proposal_id = int(data.split(":", 1)[1])
                proposal = db.get(RepairProposalRow, proposal_id)
                if proposal:
                    proposal.status = "rejected"
                    proposal.reviewed_at = datetime.utcnow()
                    db.commit()
                    send_message(chat_id, f"Rejected fix proposal #{proposal_id}.")
                return

            return

        if "message" in update and update["message"].get("text"):
            text = update["message"]["text"].strip()
            chat_id = str(update["message"]["chat"]["id"])

            pending = _get_pending(db, chat_id)
            if pending:
                _handle_pending_reply(db, chat_id, pending, text)
                return

            if text.startswith("/start"):
                send_message(chat_id, "Signal is live. Use /latest, /help, or send feedback text.")
                return

            if text.startswith("/latest"):
                send_message(chat_id, "Open the dashboard to see the latest items or use /help.")
                return

            if text.startswith("/help"):
                send_message(
                    chat_id,
                    "Commands: /start, /latest, or send feedback text.\nButtons: Good digest / Did not like / Regenerate, and approve/reject fix."
                )
                return

            _handle_generic_feedback_message(db, chat_id, text)
            return

    finally:
        db.close()


def _handle_feedback_category(db, chat_id: str, category: str) -> None:
    if category not in ALLOWED_FEEDBACK_CATEGORIES:
        log_json("guardrail_violation", reason="unknown_feedback_category", category=category, chat_id=chat_id)
        send_message(chat_id, "That option isn't recognized — please use the buttons.")
        return

    label = FEEDBACK_CATEGORY_LABELS[category]
    row = FeedbackEvent(event_type=f"negative:{category}", text=None, payload_json=json.dumps({"category": category, "source": "button"}))
    db.add(row)
    db.commit()

    try:
        step = CATEGORY_PREFERENCE_STEP.get(category)
        if step:
            field, delta = step
            applied = apply_bounded_delta(chat_id, field, delta)
            if not applied:
                log_json("guardrail_blocked", reason="daily_cap_on_feedback_category", category=category, chat_id=chat_id)
        elif category in NOVELTY_TUNING_CATEGORIES:
            _apply_novelty_tuning(db, chat_id, category)
    except Exception as exc:
        log_json("feedback_handling_error", stage="preference_update", error=str(exc), chat_id=chat_id)

    _set_pending(db, chat_id, "awaiting_feedback_elaboration", {"feedback_event_id": row.id, "category": category})
    send_message(chat_id, f"Got it — logged as “{label}”.")
    ask_feedback_elaboration(chat_id, category)


def _apply_novelty_tuning(db, chat_id: str, category: str) -> None:
    if not consume_daily_change_budget(chat_id):
        send_message(chat_id, "Logged your feedback, but today's tuning budget is already used up — it'll still be reviewed.")
        return
    if category == "too_repetitive":
        current = db.get(SystemSetting, "novelty_duplicate_threshold")
        cur = float(current.value) if current else settings.novelty_duplicate_threshold
        _upsert_setting(db, "novelty_duplicate_threshold", str(max(0.82, cur - 0.02)))
    elif category == "not_enough_new_information":
        current = db.get(SystemSetting, "novelty_new_threshold")
        cur = float(current.value) if current else settings.novelty_new_threshold
        _upsert_setting(db, "novelty_new_threshold", str(max(0.70, cur - 0.02)))


def _handle_regenerate_general(db, chat_id: str) -> None:
    try:
        summary = regenerate_from_cache(chat_id=chat_id)
        _send_regenerated_digest(chat_id, summary)
    except BudgetExceededError:
        log_json("pipeline_budget_stop", stage="regenerate")
        send_message(chat_id, "Today's AI budget cap is reached, so I can't regenerate right now. It'll be available again tomorrow.")
    except Exception as exc:
        log_json("feedback_handling_error", stage="regenerate_general", error=str(exc), chat_id=chat_id)
        send_message(chat_id, "Something went wrong regenerating the digest. Logged for review — nothing else was affected.")


def _handle_pending_reply(db, chat_id: str, pending: PendingInteraction, text: str) -> None:
    try:
        if pending.kind == "awaiting_feedback_elaboration":
            _resolve_feedback_elaboration(db, chat_id, pending, text)
        elif pending.kind == "awaiting_regenerate_angle":
            _resolve_regenerate_angle(db, chat_id, pending, text)
        else:
            _clear_pending(db, chat_id)
    except Exception as exc:
        log_json("feedback_handling_error", stage="pending_reply", kind=pending.kind, error=str(exc), chat_id=chat_id)
        _clear_pending(db, chat_id)
        send_message(chat_id, "Logged what I could, but hit a hiccup processing that reply. Nothing else was affected.")


def _resolve_feedback_elaboration(db, chat_id: str, pending: PendingInteraction, text: str) -> None:
    context = json.loads(pending.context_json or "{}")
    _clear_pending(db, chat_id)

    if text.strip().lower() in ("skip", "no", "none", "-"):
        send_message(chat_id, "Thanks!")
        return

    clean_text, is_safe = sanitize_user_text(text)
    if not is_safe:
        db.add(SystemEvent(run_id=None, event_type="guardrail_violation", payload_json=json.dumps({"stage": "feedback_elaboration", "chat_id": chat_id})))
        db.commit()
        send_message(chat_id, FALLBACK_MESSAGE_UNSAFE + " Your category choice is already recorded.")
        return

    feedback_event_id = context.get("feedback_event_id")
    if feedback_event_id:
        row = db.get(FeedbackEvent, feedback_event_id)
        if row:
            row.text = clean_text
            db.commit()

    category = context.get("category", "other")
    if category == "not_relevant":
        _apply_item_selection_bias(chat_id, delta=-0.05)

    # One-shot: shapes the next digest's tone/focus for this specific
    # complaint, then is consumed and cleared (see pop_recent_feedback_note).
    set_recent_feedback_note(category, clean_text)

    if category in ("source_quality_issue", "other"):
        try:
            rca = analyze_root_cause(
                error_text=clean_text,
                context_text=f"Telegram feedback category: {category}. User elaboration follows.",
            )
            db.add(SystemEvent(run_id=None, event_type="rca", payload_json=rca.model_dump_json()))
            db.commit()
        except BudgetExceededError:
            log_json("pipeline_budget_stop", stage="rca_feedback_elaboration")

    send_message(chat_id, "Thanks — noted, and future digests will factor this in.")


def _apply_item_selection_bias(chat_id: str, *, delta: float) -> None:
    """Nudge item-selection bias for today's digest categories. Positive delta
    reinforces the same pattern of content (Good digest); negative delta backs
    away from it (Did not like -> Not relevant)."""
    db = SessionLocal()
    try:
        latest = db.query(SystemEvent).filter(SystemEvent.event_type == "daily_digest_generated").order_by(SystemEvent.id.desc()).first()
        if not latest:
            return
        payload = json.loads(latest.payload_json)
        categories = list({item.get("category_tag") for item in payload.get("digest_items", []) if item.get("category_tag")})
        if categories:
            apply_category_bias(chat_id, categories, delta)
    finally:
        db.close()


def _resolve_regenerate_angle(db, chat_id: str, pending: PendingInteraction, text: str) -> None:
    context = json.loads(pending.context_json or "{}")
    clean_text, is_safe = sanitize_user_text(text)

    if not is_safe:
        attempts = context.get("attempts", 0) + 1
        db.add(SystemEvent(run_id=None, event_type="guardrail_violation", payload_json=json.dumps({"stage": "regenerate_angle", "chat_id": chat_id})))
        db.commit()
        if attempts >= 2:
            _clear_pending(db, chat_id)
            send_message(chat_id, "I couldn't use that as a focus. Running a general regenerate instead.")
            _handle_regenerate_general(db, chat_id)
        else:
            _set_pending(db, chat_id, "awaiting_regenerate_angle", {"attempts": attempts})
            send_message(chat_id, FALLBACK_MESSAGE_UNSAFE)
        return

    _clear_pending(db, chat_id)
    try:
        summary = regenerate_from_cache(chat_id=chat_id, angle=clean_text)
        _send_regenerated_digest(chat_id, summary)
    except BudgetExceededError:
        log_json("pipeline_budget_stop", stage="regenerate_specific")
        send_message(chat_id, "Today's AI budget cap is reached, so I can't regenerate right now. It'll be available again tomorrow.")
    except Exception as exc:
        log_json("feedback_handling_error", stage="regenerate_specific", error=str(exc), chat_id=chat_id)
        send_message(chat_id, "Something went wrong regenerating with that angle. Logged for review — nothing else was affected.")


def _handle_generic_feedback_message(db, chat_id: str, text: str) -> None:
    try:
        classification = classify_feedback(text)
    except BudgetExceededError:
        log_json("pipeline_budget_stop", stage="feedback_classification")
        db.add(FeedbackEvent(event_type="unclassified_budget_capped", text=text, payload_json=None))
        db.commit()
        send_message(chat_id, "Thanks — logged your feedback as-is. Today's AI budget cap is reached, so I couldn't auto-analyze it, but nothing is lost; a human can review it in the meantime.")
        return

    db.add(FeedbackEvent(event_type=classification.category, text=text, payload_json=classification.model_dump_json()))
    db.commit()

    if classification.category in ("content_accuracy", "wrong_novelty_call"):
        try:
            rca = analyze_root_cause(
                error_text=text,
                context_text="Telegram-reported content/novelty issue. Check recent source items and novelty outputs."
            )
        except BudgetExceededError:
            log_json("pipeline_budget_stop", stage="rca")
            send_message(chat_id, "Logged your feedback, but today's AI budget cap is reached so I couldn't run root-cause analysis. It'll be reviewed manually.")
            return
        db.add(SystemEvent(run_id=None, event_type="rca", payload_json=rca.model_dump_json()))
        db.commit()
        lower_text = text.lower()
        if "duplicate" in lower_text or "repeated" in lower_text:
            _apply_novelty_tuning(db, chat_id, "too_repetitive")
            send_message(chat_id, "I found a likely novelty-tuning issue and adjusted the duplicate threshold slightly. No code was changed.")
        elif "missed" in lower_text or "new" in lower_text:
            _apply_novelty_tuning(db, chat_id, "not_enough_new_information")
            send_message(chat_id, "I found a likely novelty-tuning issue and adjusted the new-item threshold slightly. No code was changed.")
        else:
            send_message(chat_id, "I logged your feedback and captured an RCA for config review.")
        return

    if classification.category in ("source_broken", "slide_rendering_bug"):
        try:
            rca = analyze_root_cause(
                error_text=text,
                context_text="Telegram-reported issue. Check latest logs and recent system events."
            )
            repair = draft_repair_proposal(text, rca.model_dump_json())
        except BudgetExceededError:
            log_json("pipeline_budget_stop", stage="rca_or_repair")
            send_message(chat_id, "Logged your feedback, but today's AI budget cap is reached so I couldn't draft a repair proposal yet. It'll be picked up on the next run.")
            return
        row = RepairProposalRow(
            title=repair.title,
            proposal_text=repair.proposal_text,
            risk_level=repair.risk_level,
            status="pending_review",
        )
        db.add(row)
        db.commit()
        notify_fix_proposal(chat_id, row.id, repair.title, repair.proposal_text, repair.risk_level)
    else:
        send_message(chat_id, f"Logged feedback as {classification.category}.")
