from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from signalos.core.config import settings
from signalos.core.db import CostLedger, SessionLocal
from signalos.core.logging import log_json
from signalos.core.skill_registry import load_skill

client = OpenAI(api_key=settings.openai_api_key)
MODEL_MAP = settings.model_routing


class BudgetExceededError(Exception):
    """Raised when today's spend or token usage has hit the configured cap.

    Callers should catch this and degrade gracefully (skip the item, fall back
    to NEEDS_HUMAN_REVIEW, notify the user) rather than let the run crash.
    """


def _today_start_utc() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime(now.year, now.month, now.day, tzinfo=timezone.utc)


def get_today_usage() -> tuple[float, int]:
    """Returns (spend_usd, total_tokens) recorded in CostLedger since UTC midnight."""
    db = SessionLocal()
    try:
        cutoff = _today_start_utc()
        rows = db.query(CostLedger).filter(CostLedger.created_at >= cutoff).all()
        spend = sum(r.estimated_cost_usd for r in rows)
        tokens = sum(r.prompt_tokens + r.completion_tokens for r in rows)
        return spend, tokens
    finally:
        db.close()


def _record_cost(run_id: str | None, task_type: str, model: str, prompt_tokens: int, completion_tokens: int, cost: float) -> None:
    db = SessionLocal()
    try:
        db.add(CostLedger(
            run_id=run_id,
            task_type=task_type,
            model_name=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=cost,
        ))
        db.commit()
    finally:
        db.close()

# Estimated prices in USD per 1M tokens.
# Keep these in config if you want to tune later.
PRICE_PER_1M = {
    "text-embedding-3-small": (0.02, 0.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    in_cost, out_cost = PRICE_PER_1M.get(model_name, (0.0, 0.0))
    return (prompt_tokens / 1_000_000.0) * in_cost + (completion_tokens / 1_000_000.0) * out_cost


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=8))
def call_model(
    task_type: str,
    prompt: str,
    *,
    skill_name: str | None = None,
    system: str | None = None,
    json_mode: bool = True,
    temperature: float | None = None,
    run_id: str | None = None,
) -> tuple[str, dict[str, Any]]:
    # Budget check happens before spending anything further today.
    # This only gates paid chat-completion calls (this function), not embeddings —
    # embeddings cost ~$0.02/1M tokens and are load-bearing for dedup, so they stay
    # exempt from the hard stop; their (small) cost is still logged to the ledger.
    spend_so_far, tokens_so_far = get_today_usage()
    if spend_so_far >= settings.daily_spend_cap_usd:
        log_json("budget_exceeded", spent=spend_so_far, cap=settings.daily_spend_cap_usd, task_type=task_type, gate="spend")
        raise BudgetExceededError(
            f"Daily spend cap ${settings.daily_spend_cap_usd:.2f} reached (spent ${spend_so_far:.2f}); skipping {task_type} call."
        )
    if tokens_so_far >= settings.daily_token_cap:
        log_json("budget_exceeded", tokens=tokens_so_far, cap=settings.daily_token_cap, task_type=task_type, gate="tokens")
        raise BudgetExceededError(
            f"Daily token cap {settings.daily_token_cap} reached ({tokens_so_far} used); skipping {task_type} call."
        )

    model = MODEL_MAP[task_type]
    temp = temperature if temperature is not None else (settings.model_json_temperature if json_mode else settings.model_text_temperature)

    system_parts = [
        "You are Signal, a governed AI intelligence system.",
        "Follow the active skill instructions exactly when provided.",
        "Return valid JSON when requested.",
        "Never speculate beyond the source text.",
    ]

    if system:
        system_parts.append(system)

    if skill_name:
        skill = load_skill(skill_name)
        system_parts.append(f"[SKILL:{skill_name}]\n{skill['body']}")

    messages = [{"role": "system", "content": "\n\n".join(system_parts)}]
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temp,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""

    usage = getattr(resp, "usage", None)
    usage_payload = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
        "total_tokens": getattr(usage, "total_tokens", 0) if usage else 0,
        "model": model,
        "task_type": task_type,
        "skill_name": skill_name,
        "estimated_cost_usd": estimate_cost(
            model,
            getattr(usage, "prompt_tokens", 0) if usage else 0,
            getattr(usage, "completion_tokens", 0) if usage else 0,
        ),
    }
    log_json("llm_usage", **usage_payload)
    _record_cost(
        run_id=run_id,
        task_type=task_type,
        model=model,
        prompt_tokens=usage_payload["prompt_tokens"],
        completion_tokens=usage_payload["completion_tokens"],
        cost=usage_payload["estimated_cost_usd"],
    )
    return content, usage_payload


def embed_texts(texts: list[str], run_id: str | None = None) -> list[list[float]]:
    resp = client.embeddings.create(
        model=MODEL_MAP["embedding"],
        input=texts,
    )
    usage = getattr(resp, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
    cost = estimate_cost(MODEL_MAP["embedding"], prompt_tokens, 0)
    # Embeddings are exempt from the hard budget gate above (see call_model) but
    # still logged, so get_today_usage() and the dashboard reflect true total spend.
    _record_cost(run_id=run_id, task_type="embedding", model=MODEL_MAP["embedding"], prompt_tokens=prompt_tokens, completion_tokens=0, cost=cost)
    return [item.embedding for item in resp.data]
