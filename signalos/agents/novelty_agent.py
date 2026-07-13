from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import select

from signalos.core.config import settings
from signalos.core.db import ContentItem, SessionLocal, SystemSetting
from signalos.core.llm import call_model
from signalos.core.logging import log_json
from signalos.core.models import NoveltyResult, SourceItem


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _get_threshold(db: SessionLocal, key: str, default: float) -> float:
    row = db.get(SystemSetting, key)
    if not row:
        return default
    try:
        return float(row.value)
    except ValueError:
        return default


def detect_novelty(item: SourceItem) -> NoveltyResult:
    db = SessionLocal()
    try:
        if not item.embedding:
            raise ValueError("Item must have embedding before novelty detection")

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = db.execute(
            select(ContentItem).where(ContentItem.created_at >= cutoff).order_by(ContentItem.id.desc()).limit(250)
        ).scalars().all()

        similarities: list[tuple[int, float, str]] = []
        for rec in recent:
            if not rec.embedding_json:
                continue
            try:
                rec_emb = json.loads(rec.embedding_json)
                sim = cosine_similarity(item.embedding, rec_emb)
                similarities.append((rec.id, sim, rec.cleaned_text))
            except Exception:
                continue

        similarities.sort(key=lambda x: x[1], reverse=True)
        top3 = similarities[:3]
        max_sim = top3[0][1] if top3 else 0.0

        new_th = _get_threshold(db, "novelty_new_threshold", settings.novelty_new_threshold)
        dup_th = _get_threshold(db, "novelty_duplicate_threshold", settings.novelty_duplicate_threshold)
        low_conf = _get_threshold(db, "novelty_low_confidence", settings.novelty_ambiguous_low_confidence)

        if max_sim < new_th:
            return NoveltyResult(
                verdict="NEW",
                confidence=0.95,
                reasoning=f"Similarity {max_sim:.2f} is below auto-new threshold {new_th:.2f}.",
                similar_item_ids=[x[0] for x in top3],
            )

        if max_sim > dup_th:
            return NoveltyResult(
                verdict="DUPLICATE",
                confidence=0.95,
                reasoning=f"Similarity {max_sim:.2f} is above auto-duplicate threshold {dup_th:.2f}.",
                similar_item_ids=[x[0] for x in top3],
            )

        prompt = f"""
You are a novelty detection agent.

Decide whether the new item is NEW, DUPLICATE, or UPDATE relative to the top similar past items.

Return JSON only:
{{
  "verdict": "NEW|DUPLICATE|UPDATE",
  "confidence": 0-1,
  "reasoning": "string"
}}

NEW ITEM:
{item.cleaned_text}

TOP SIMILAR ITEMS:
{json.dumps([{"id": i, "similarity": round(s, 4), "text": t[:1500]} for i, s, t in top3], ensure_ascii=False)}
"""
        raw, usage = call_model(
            "novelty_agent",
            prompt,
            skill_name="signal-detection",
            json_mode=True,
        )
        data = json.loads(raw)
        result = NoveltyResult(
            verdict=data["verdict"],
            confidence=float(data["confidence"]),
            reasoning=data["reasoning"],
            similar_item_ids=[x[0] for x in top3],
        )

        if result.confidence < low_conf:
            result.verdict = "NEEDS_HUMAN_REVIEW"

        log_json("novelty_result", verdict=result.verdict, confidence=result.confidence, similar_count=len(top3))
        return result
    finally:
        db.close()
