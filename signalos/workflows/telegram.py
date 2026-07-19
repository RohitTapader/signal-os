from __future__ import annotations

import html
from typing import Any

import requests

from signalos.core.config import settings
from signalos.core.logging import log_json

BASE = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
TELEGRAM_TEXT_LIMIT = 4096


def _esc(text: str | None) -> str:
    return html.escape(str(text or "").strip())


# Grounded PM action labels. Only Read and Skim are ever delivered to
# Telegram (signalos.workflows.pipeline.TELEGRAM_SHOWN_RECOMMENDATIONS) —
# File Away and Ignore never reach format_digest_briefing in practice, but
# the maps stay complete for dashboard/debug rendering. See
# signalos.source_intelligence.scoring.recommendation_for_score for how the
# label is chosen (deterministically, from score band + whether a concrete
# decision is actually grounded in the source).
PRIORITY_EMOJI = {
    "Read": "🔥",
    "Skim": "👀",
    "File Away": "🗂",
    "Ignore": "💤",
}

# Ties the sign-off to the actual recommendation rather than being random —
# gives each message a distinct close without turning into a gimmick.
PRIORITY_SIGNOFF = {
    "Read": "⏱ Act on this today.",
    "Skim": "👀 A 2-minute scan is enough.",
    "File Away": "🗂 Low urgency now — kept for reference.",
    "Ignore": "💤 Skip unless it's directly in your lane.",
}


def format_digest_briefing(item: dict[str, Any], *, index: int = 1, total: int = 1) -> str:
    """A decision briefing, not a news summary — what changed, why it matters
    to an AI PM, who should care, in that order.

    Designed to be read in a scroll: a scannable eyebrow line carrying the
    grounded action label (never a vague "read later"), a punchy headline +
    plain-English reason up top, a single "What's New/Changed" section that
    folds in cross-source cluster context and comparison bullets, a pulled-
    quote takeaway that breaks the visual pattern, and a recommendation-
    specific sign-off so a multi-item daily digest doesn't read as the same
    template five times over.
    """
    rec = item.get("should_you_read") or {}
    recommendation = rec.get("recommendation", "Skim")
    emoji = PRIORITY_EMOJI.get(recommendation, "👁")
    category = _esc(item.get("source_category") or item.get("category_tag", "media"))
    source = _esc(item.get("source_display_name") or item.get("source_name"))

    counter = f" · Signal {index}/{total} today" if total > 1 else ""
    lines: list[str] = [
        f"{emoji} <b>{_esc(recommendation).upper()}</b> · {category} · {source}{counter}",
        f"<b>{_esc(item.get('headline'))}</b>",
    ]
    if rec.get("reason"):
        lines.append(f"<i>{_esc(rec['reason'])}</i>")
    if item.get("who_should_care"):
        lines.append(f"👤 For: {_esc(item['who_should_care'])}")
    lines.append("")

    if item.get("executive_summary"):
        lines += [_esc(item["executive_summary"]), ""]

    # One section for both the cross-source cluster ("who else is covering
    # this") and the concrete deltas, so a reader gets a single coherent
    # picture of what's new/changed instead of three disconnected fragments.
    corroborating = item.get("corroborating_sources") or []
    bullets = item.get("what_changed") or []
    if corroborating or bullets:
        lines.append("<b>What's New/Changed</b>")
        if corroborating:
            names = ", ".join(_esc(c.get("display_name", "")) for c in corroborating[:4])
            lines.append(f"🔗 Confirmed by {item.get('source_count', 1)} sources — also covered by {names}")
        lines.extend(f"▸ {_esc(b)}" for b in bullets[:5])
        lines.append("")

    if item.get("business_impact"):
        lines += [f"💰 <b>Business Impact</b> — {_esc(item['business_impact'])}", ""]

    if item.get("competitive_insight"):
        lines += [f"🏆 <b>Competitive Insight</b> — {_esc(item['competitive_insight'])}", ""]

    if item.get("pm_takeaway"):
        lines += [f"<blockquote>💡 {_esc(item['pm_takeaway'])}</blockquote>", ""]

    if item.get("recommended_action"):
        lines += [f"✅ <b>Do this:</b> {_esc(item['recommended_action'])}", ""]

    links: list[str] = []
    if item.get("source_url"):
        links.append(str(item["source_url"]))
    for ev in item.get("supporting_evidence") or []:
        url = ev.get("source_url") or ev.get("source", "")
        if url:
            links.append(str(url))
    for c in corroborating:
        if c.get("url"):
            links.append(str(c["url"]))
    links = list(dict.fromkeys(links))  # dedupe, keep order
    if links:
        lines.append("<b>Sources</b>")
        for url in links[:5]:
            lines.append(f'▸ <a href="{_esc(url)}">{_esc(url)}</a>')
        lines.append("")

    lines.append(PRIORITY_SIGNOFF.get(recommendation, ""))

    text = "\n".join(lines).strip()
    if len(text) <= TELEGRAM_TEXT_LIMIT:
        return text
    return text[: TELEGRAM_TEXT_LIMIT - 20] + "\n\n<i>(truncated)</i>"


def _post(method: str, payload: dict[str, Any] | None = None):
    url = f"{BASE}/{method}"
    resp = requests.post(url, json=payload or {}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def send_message(chat_id: str, text: str, reply_markup: dict[str, Any] | None = None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _post("sendMessage", payload)


def answer_callback_query(callback_query_id: str, text: str = ""):
    payload = {"callback_query_id": callback_query_id, "text": text}
    return _post("answerCallbackQuery", payload)


def set_webhook(webhook_url: str):
    return _post("setWebhook", {"url": webhook_url})


def notify_digest_button(chat_id: str):
    return send_message(
        chat_id,
        "Digest ready.",
        reply_markup={
            "inline_keyboard": [[
                {"text": "👍 Good digest", "callback_data": "feedback_good"},
                {"text": "👎 Did not like", "callback_data": "feedback_bad"},
                {"text": "🔁 Regenerate", "callback_data": "regenerate_today"},
            ]]
        },
    )


def ask_feedback_category(chat_id: str):
    from signalos.core.feedback_guardrails import FEEDBACK_CATEGORY_LABELS
    keys = list(FEEDBACK_CATEGORY_LABELS)
    rows = [
        [{"text": FEEDBACK_CATEGORY_LABELS[k], "callback_data": f"fb_cat:{k}"} for k in keys[i:i + 2]]
        for i in range(0, len(keys), 2)
    ]
    return send_message(chat_id, "Sorry to hear that — what didn't work?", reply_markup={"inline_keyboard": rows})


def ask_feedback_elaboration(chat_id: str):
    return send_message(chat_id, "Want to add details? Reply with specifics, or send ‘skip’.")


def ask_regenerate_mode(chat_id: str):
    return send_message(
        chat_id,
        "Do you want something specific or a general retry?",
        reply_markup={
            "inline_keyboard": [[
                {"text": "🔁 General retry", "callback_data": "regen_mode:general"},
                {"text": "🎯 Something specific", "callback_data": "regen_mode:specific"},
            ]]
        },
    )


def ask_regenerate_angle(chat_id: str):
    return send_message(chat_id, "What new information or angle would you like me to focus on?")


def notify_fix_proposal(chat_id: str, proposal_id: int, title: str, proposal_text: str, risk_level: str):
    return send_message(
        chat_id,
        f"<b>Repair proposal ready</b>\n\n"
        f"<b>{title}</b>\n"
        f"Risk: {risk_level}\n\n"
        f"{proposal_text}",
        reply_markup={
            "inline_keyboard": [[
                {"text": "Approve", "callback_data": f"approve_fix:{proposal_id}"},
                {"text": "Reject", "callback_data": f"reject_fix:{proposal_id}"},
            ]]
        },
    )
