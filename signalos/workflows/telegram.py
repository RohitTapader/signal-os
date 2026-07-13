from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import requests

from signalos.core.config import settings
from signalos.core.logging import log_json

BASE = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
TELEGRAM_TEXT_LIMIT = 4096


def _esc(text: str | None) -> str:
    return html.escape(str(text or "").strip())


def format_digest_briefing(item: dict[str, Any]) -> str:
    """Rich HTML briefing for AI PMs — sent as text before slide images."""
    rec = item.get("should_you_read") or {}
    why = item.get("why_it_matters") or {}
    lines: list[str] = [
        f"<b>{_esc(item.get('headline'))}</b>",
        (
            f"{_esc(item.get('source_display_name') or item.get('source_name'))} • "
            f"{_esc(item.get('source_category') or item.get('category_tag', 'media'))} • "
            f"{item.get('signal_score', 0)}/100 • "
            f"<b>{_esc(rec.get('recommendation', 'Read Later'))}</b>"
        ),
        "",
    ]

    corroborating = item.get("corroborating_sources") or []
    if corroborating:
        names = ", ".join(_esc(c.get("display_name", "")) for c in corroborating[:4])
        lines += [f"<b>Cross-source cluster</b> ({item.get('source_count', 1)} sources)", f"Also covered by: {names}", ""]

    if item.get("context"):
        lines += ["<b>What this is</b>", _esc(item["context"]), ""]

    if item.get("whats_new"):
        lines += ["<b>What's new</b>", _esc(item["whats_new"]), ""]

    if item.get("executive_summary"):
        lines += ["<b>Executive summary</b>", _esc(item["executive_summary"]), ""]

    bullets = item.get("what_changed") or []
    if bullets:
        lines.append("<b>Key changes</b>")
        lines.extend(f"• {_esc(b)}" for b in bullets[:4])
        lines.append("")

    if item.get("key_innovation"):
        lines += ["<b>Key innovation</b>", _esc(item["key_innovation"]), ""]

    if why.get("product"):
        lines += ["<b>Product impact</b>", _esc(why["product"]), ""]
    if why.get("business"):
        lines += ["<b>Business impact</b>", _esc(why["business"]), ""]
    if why.get("competitive"):
        lines += ["<b>Competitive impact</b>", _esc(why["competitive"]), ""]

    if item.get("pm_takeaway"):
        lines += ["<b>PM takeaway</b>", _esc(item["pm_takeaway"]), ""]

    if item.get("score_explanation"):
        lines += ["<b>Signal score</b>", _esc(item["score_explanation"]), ""]

    breakdown = item.get("signal_score_breakdown") or {}
    components = breakdown.get("components") or []
    if components:
        lines.append("<b>Score breakdown</b>")
        for comp in components[:5]:
            name = _esc(comp.get("name", "").replace("_", " ").title())
            pts = comp.get("weighted_points", 0)
            lines.append(f"• {name}: +{pts:.1f} pts")
        lines.append("")

    if item.get("recommended_action"):
        lines += ["<b>Recommended action</b>", _esc(item["recommended_action"]), ""]

    evidence = item.get("supporting_evidence") or []
    if evidence:
        lines.append("<b>Evidence</b>")
        for ev in evidence[:3]:
            claim = _esc(ev.get("claim", ""))
            snippet = _esc(ev.get("evidence", ""))
            if claim:
                lines.append(f"• <i>{claim}</i>: {snippet}")
        lines.append("")

    if item.get("limitations"):
        lines += ["<b>Limitations</b>", _esc(item["limitations"]), ""]

    if rec.get("reason"):
        lines += ["<b>Why read (or skip)</b>", _esc(rec["reason"]), ""]

    url = item.get("source_url") or ""
    if url:
        lines.append(f'<a href="{_esc(url)}">Read source</a>')

    text = "\n".join(lines)
    if len(text) <= TELEGRAM_TEXT_LIMIT:
        return text
    return text[: TELEGRAM_TEXT_LIMIT - 20] + "\n\n<i>(truncated)</i>"


def _post(method: str, payload: dict[str, Any] | None = None, files: dict[str, Any] | None = None):
    url = f"{BASE}/{method}"
    if files:
        resp = requests.post(url, data=payload or {}, files=files, timeout=30)
    else:
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


def send_media_group(chat_id: str, image_paths: list[str], caption: str | None = None):
    media = []
    files = {}
    for i, path in enumerate(image_paths):
        key = f"file{i}"
        files[key] = open(path, "rb")
        item = {"type": "photo", "media": f"attach://{key}"}
        if i == 0 and caption:
            item["caption"] = caption
        media.append(item)

    try:
        payload = {"chat_id": chat_id, "media": json.dumps(media)}
        return _post("sendMediaGroup", payload, files=files)
    finally:
        for f in files.values():
            try:
                f.close()
            except Exception:
                pass


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
