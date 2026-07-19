
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select

from signalos.agents.impact_agent import analyze_impact
from signalos.agents.novelty_agent import detect_novelty
from signalos.core.config import settings
from signalos.core.db import ContentItem, SessionLocal, SystemEvent, init_db
from signalos.core.llm import BudgetExceededError
from signalos.core.logging import log_json
from signalos.core.models import DigestItem, NoveltyResult, PreferenceProfile, SourceItem
from signalos.core.preferences import get_preference_profile
from signalos.ingestion.collector import collect_all_sources
from signalos.source_intelligence.briefing import merged_source_context
from signalos.source_intelligence.clustering import cluster_items, pick_primary_item, supporting_items
from signalos.source_intelligence.scoring import compute_signal_score, recommendation_for_score
from signalos.workflows.embeddings import embed_item, embedding_to_json
from signalos.workflows.normalize import normalize_item
from signalos.workflows.validation import validate_item


def _store_item(db: SessionLocal, item: SourceItem, novelty_result: NoveltyResult) -> ContentItem:
    row = ContentItem(
        source_id=item.source_id or item.source_name,
        source_name=item.source_name,
        source_display_name=item.display_name or item.source_name,
        source_type=item.source_type,
        source_category=item.source_category,
        source_tier=item.tier,
        authority_score=item.authority_score,
        title=item.title,
        url=str(item.url),
        published_at=item.published_at,
        author=item.author,
        raw_text=item.raw_text,
        cleaned_text=item.cleaned_text,
        embedding_json=embedding_to_json(item),
        novelty_verdict=novelty_result.verdict,
        novelty_confidence=novelty_result.confidence,
        novelty_reasoning=novelty_result.reasoning,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _row_to_source_item(row: ContentItem) -> SourceItem:
    return SourceItem(
        source_id=row.source_id or row.source_name,
        display_name=row.source_display_name or row.source_name,
        source_name=row.source_name,
        source_type=row.source_type,
        title=row.title,
        url=row.url,
        published_at=row.published_at,
        author=row.author,
        raw_text=row.raw_text,
        cleaned_text=row.cleaned_text,
        source_category=row.source_category,
        tier=row.source_tier or "primary",
        authority_score=row.authority_score or 70,
        embedding=json.loads(row.embedding_json) if row.embedding_json else None,
    )


def _build_digest_item(row: ContentItem, impact: dict, corroborating: list[dict]) -> DigestItem | None:
    if not impact:
        return None
    return DigestItem(
        item_id=row.id,
        title=row.title,
        source_id=row.source_id or row.source_name,
        source_name=row.source_name,
        source_display_name=row.source_display_name or row.source_name,
        source_category=row.source_category,
        source_tier=row.source_tier or "primary",
        authority_score=row.authority_score or 70,
        source_url=row.url,
        category_tag=row.source_category,
        headline=impact["headline"],
        context=impact.get("context", ""),
        executive_summary=impact.get("executive_summary", ""),
        key_innovation=impact.get("key_innovation", ""),
        pm_takeaway=impact.get("pm_takeaway", ""),
        business_impact=impact.get("business_impact", ""),
        competitive_insight=impact.get("competitive_insight", ""),
        who_should_care=impact.get("who_should_care", ""),
        decision_supported=impact.get("decision_supported", ""),
        signal_type=impact.get("signal_type", row.source_category),
        signal_score=int(impact.get("signal_score", 0)),
        signal_score_breakdown=impact.get("signal_score_breakdown"),
        score_explanation=impact.get("score_explanation", ""),
        corroborating_sources=corroborating,
        source_count=1 + len(corroborating),
        what_changed=(impact.get("what_changed") or [])[:5],
        recommended_action=impact.get("recommended_action", ""),
        companies_impacted=(impact.get("companies_impacted") or [])[:5],
        confidence=float(impact.get("confidence", 0.0)),
        should_you_read={
            "recommendation": impact.get("should_you_read", {}).get("recommendation", "Skim"),
            "reason": impact.get("should_you_read", {}).get("reason", ""),
        },
        supporting_evidence=(impact.get("supporting_evidence") or [])[:5],
        limitations=impact.get("limitations", ""),
        published_at=row.published_at,
    )


def fetch_all_sources() -> list[SourceItem]:
    """Backward-compatible alias — delegates to ingestion collector."""
    return collect_all_sources()


def _today_start_utc_naive() -> datetime:
    """Midnight in settings.timezone, converted to naive UTC — matches how
    ContentItem.created_at is stored (datetime.utcnow(), no tzinfo)."""
    tz = ZoneInfo(settings.timezone)
    now_local = datetime.now(tz)
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None)


def _build_digest(
    db: SessionLocal,
    accepted_rows: list[ContentItem],
    run_id: str,
    *,
    force_refresh: bool = False,
    angle: str | None = None,
    preferences: PreferenceProfile | None = None,
    temperature: float | None = None,
) -> list[DigestItem]:
    """Cluster accepted rows, run/reuse impact analysis, score, and render
    slides. Shared by the normal daily run and regenerate_from_cache.

    force_refresh=True always recomputes impact (used by regenerate, so an
    angle or updated preferences actually take effect instead of hitting the
    cached impact_json from the original run).
    """
    # Always cluster fresh: a row reused across multiple _build_digest calls
    # (e.g. two regenerates the same day) would otherwise keep a stale
    # cluster_id from the prior run, and the "unclustered" fallback below
    # would then silently skip it since cluster_id no longer looks empty.
    for row in accepted_rows:
        row.cluster_id = None

    source_items = [_row_to_source_item(row) for row in accepted_rows]
    clusters = cluster_items(source_items, threshold=0.86)
    row_by_url = {row.url: row for row in accepted_rows}
    cluster_groups: dict[str, list[ContentItem]] = {}

    for idx, cluster in enumerate(clusters, start=1):
        cluster_id = f"cluster_{idx:03d}"
        for clustered_item in cluster:
            row = row_by_url.get(str(clustered_item.url))
            if row:
                row.cluster_id = cluster_id
                cluster_groups.setdefault(cluster_id, []).append(row)

    for row in accepted_rows:
        if not row.cluster_id:
            row.cluster_id = f"solo_{row.id}"
            cluster_groups.setdefault(row.cluster_id, []).append(row)
    db.commit()

    cluster_primaries: list[tuple[ContentItem, list[ContentItem]]] = []
    for _cid, rows in cluster_groups.items():
        items_in_cluster = [_row_to_source_item(r) for r in rows]
        primary_item = pick_primary_item(items_in_cluster)
        primary_row = row_by_url[str(primary_item.url)]
        supporting_rows = [
            row_by_url[str(s.url)]
            for s in supporting_items(items_in_cluster, primary_item)
        ]
        cluster_primaries.append((primary_row, supporting_rows))

    # source_trust_bias / category_bias are bounded preference nudges that
    # influence ranking only — they never change the transparent signal_score
    # breakdown stored on the item itself.
    trust_bias = preferences.source_trust_bias if preferences else 0.0
    category_bias = preferences.category_bias if preferences else {}

    def _sort_key(pair: tuple[ContentItem, list[ContentItem]]) -> tuple[float, bool]:
        row = pair[0]
        bias = trust_bias + category_bias.get(row.source_category, 0.0)
        return (-((row.authority_score or 0) + bias * 100), row.source_tier != "primary")

    cluster_primaries.sort(key=_sort_key)

    digest_items: list[DigestItem] = []
    for primary_row, supporting_rows in cluster_primaries[: settings.daily_max_items]:
        if primary_row.impact_json and not force_refresh:
            impact = json.loads(primary_row.impact_json)
            corroborating = [
                {
                    "source_id": r.source_id or r.source_name,
                    "display_name": r.source_display_name or r.source_name,
                    "category": r.source_category,
                    "tier": r.source_tier,
                    "authority_score": r.authority_score,
                    "title": r.title,
                    "url": r.url,
                }
                for r in supporting_rows
            ]
            digest = _build_digest_item(primary_row, impact, corroborating)
            if digest:
                digest_items.append(digest)
            continue

        primary_item = _row_to_source_item(primary_row)
        supporting_items_models = [_row_to_source_item(r) for r in supporting_rows]
        primary_item.cleaned_text = merged_source_context(primary_item, supporting_items_models)

        try:
            impact = analyze_impact(
                primary_item,
                corroborating=supporting_items_models,
                user_angle=angle,
                preferences=preferences,
                temperature=temperature,
            )
        except BudgetExceededError as e:
            log_json("pipeline_budget_stop", stage="impact", reason=str(e))
            break

        cluster_size = 1 + len(supporting_rows)
        max_authority = max(
            [primary_row.authority_score or 70]
            + [r.authority_score or 70 for r in supporting_rows]
        )
        effective_authority = max(0, min(100, int(max_authority + trust_bias * 100)))
        has_decision = bool((impact.decision_supported or "").strip())
        breakdown = compute_signal_score(
            novelty_confidence=primary_row.novelty_confidence or 0.0,
            product_impact_confidence=impact.product_impact_confidence,
            business_impact_confidence=impact.business_impact_confidence,
            strategic_relevance_confidence=impact.strategic_relevance_confidence,
            authority_score=effective_authority,
            cluster_size=cluster_size,
            evidence_count=len(impact.supporting_evidence),
            primary_tier=primary_row.source_tier or "primary",
            has_decision=has_decision,
        )

        # recommendation_strictness is a bounded preference nudge applied only
        # to the recommendation label, never to the transparent breakdown.total.
        strictness = preferences.recommendation_strictness if preferences else 0.5
        strictness_adjustment = int((strictness - 0.5) * 20)  # -10..+10
        rec_score = max(0, min(100, breakdown.total - strictness_adjustment))
        rec = recommendation_for_score(rec_score, has_decision=has_decision)

        if rec["recommendation"] == "Ignore":
            # Ignore-tier items are not persisted at all — no impact_json, no
            # digest_item. The bare ContentItem row from ingestion still
            # exists (needed for novelty dedup on future runs), but nothing
            # about this analysis is stored or shown.
            log_json("item_not_stored", item_id=primary_row.id, score=rec_score, reason="ignore_tier")
            continue

        impact = impact.model_copy(update={
            "signal_type": primary_row.source_category,
            "signal_score": breakdown.total,
            "signal_score_breakdown": breakdown.model_dump(),
            "score_explanation": breakdown.explanation,
            "should_you_read": rec,
        })
        primary_row.impact_json = impact.model_dump_json()
        db.commit()

        corroborating = [
            {
                "source_id": r.source_id or r.source_name,
                "display_name": r.source_display_name or r.source_name,
                "category": r.source_category,
                "tier": r.source_tier,
                "authority_score": r.authority_score,
                "title": r.title,
                "url": r.url,
            }
            for r in supporting_rows
        ]
        digest = _build_digest_item(primary_row, impact.model_dump(), corroborating)
        if digest:
            digest_items.append(digest)

    digest_items.sort(key=lambda d: d.signal_score, reverse=True)
    return digest_items


def generate_digest_from_items(items: list[SourceItem], run_id: str | None = None) -> dict:
    init_db()
    db = SessionLocal()
    try:
        accepted_rows: list[ContentItem] = []
        duplicates = 0
        updates = 0
        novel = 0

        for item in items:
            validation = validate_item(item)
            if not validation.ok:
                log_json("validation_failed", reason=validation.reason, source_name=item.display_name, title=item.title)
                continue

            item = normalize_item(item)
            item = embed_item(item)

            exists = db.execute(select(ContentItem).where(ContentItem.url == str(item.url))).scalar_one_or_none()
            if exists:
                duplicates += 1
                continue

            try:
                novelty = detect_novelty(item)
            except BudgetExceededError as e:
                log_json("pipeline_budget_stop", stage="novelty", reason=str(e))
                novelty = NoveltyResult(
                    verdict="NEEDS_HUMAN_REVIEW",
                    confidence=0.0,
                    reasoning="Daily budget cap reached before this item could be evaluated by the novelty agent.",
                )
                _store_item(db, item, novelty)
                break

            row = _store_item(db, item, novelty)

            if novelty.verdict == "DUPLICATE":
                duplicates += 1
                continue
            if novelty.verdict == "UPDATE":
                updates += 1
            if novelty.verdict in ("NEW", "UPDATE"):
                novel += 1
                accepted_rows.append(row)

        run_id = run_id or str(uuid.uuid4())
        preferences = get_preference_profile(settings.telegram_chat_id)
        digest_items = _build_digest(db, accepted_rows, run_id, preferences=preferences)

        briefings = [d.model_dump() for d in digest_items]

        summary = {
            "run_id": run_id,
            "ingested": len(items),
            "novel_items": novel,
            "duplicates": duplicates,
            "updates": updates,
            "sent_items": len(digest_items),
            "digest_items": briefings,
        }
        db.add(SystemEvent(
            run_id=summary["run_id"],
            event_type="daily_digest_generated",
            payload_json=json.dumps(summary, default=str),
        ))
        db.commit()
        return summary
    finally:
        db.close()


def regenerate_from_cache(run_id: str | None = None, *, angle: str | None = None, chat_id: str | None = None) -> dict:
    """Rebuild today's digest from already-ingested rows, without re-fetching
    sources. Used for both the "general retry" regenerate flow and recovery
    from a pipeline failure that left the original run incomplete — in both
    cases we must not hit live sources again, only what's already stored.
    """
    init_db()
    run_id = run_id or f"regenerate_{uuid.uuid4().hex[:8]}"
    chat_id = chat_id or settings.telegram_chat_id
    db = SessionLocal()
    try:
        cutoff = _today_start_utc_naive()
        rows = db.execute(
            select(ContentItem).where(
                ContentItem.created_at >= cutoff,
                ContentItem.novelty_verdict.in_(["NEW", "UPDATE"]),
            )
        ).scalars().all()

        if not rows:
            return {
                "run_id": run_id,
                "ingested": 0,
                "novel_items": 0,
                "duplicates": 0,
                "updates": 0,
                "sent_items": 0,
                "digest_items": [],
            }

        preferences = get_preference_profile(chat_id)
        # A regenerate is explicitly asked to try again with "improved"
        # settings — a modest, bounded temperature reduction for more
        # consistent output, never an unbounded or user-controlled value.
        temperature = max(0.0, settings.model_json_temperature - 0.1)
        digest_items = _build_digest(
            db,
            list(rows),
            run_id,
            force_refresh=True,
            angle=angle,
            preferences=preferences,
            temperature=temperature,
        )

        summary = {
            "run_id": run_id,
            "ingested": len(rows),
            "novel_items": len(rows),
            "duplicates": 0,
            "updates": sum(1 for r in rows if r.novelty_verdict == "UPDATE"),
            "sent_items": len(digest_items),
            "digest_items": [d.model_dump() for d in digest_items],
        }
        db.add(SystemEvent(
            run_id=run_id,
            event_type="digest_regenerated",
            payload_json=json.dumps({"angle": angle, "sent_items": summary["sent_items"]}, default=str),
        ))
        db.commit()
        return summary
    finally:
        db.close()


# Only these two labels are ever pushed to Telegram. File Away is stored
# (see _build_digest) and reachable via the dashboard/API, but doesn't reach
# the user's feed. Ignore is never stored at all.
TELEGRAM_SHOWN_RECOMMENDATIONS = {"Read", "Skim"}


def run_and_send_digest() -> dict:
    run_id = str(uuid.uuid4())
    items = fetch_all_sources()
    summary = generate_digest_from_items(items, run_id=run_id)
    summary["sent_to_telegram"] = send_to_telegram(summary["digest_items"], run_id=run_id) if summary["digest_items"] else 0
    return summary


def send_to_telegram(digest_items: list[dict], run_id: str) -> int:
    """Sends only Read/Skim items to Telegram. Returns the count actually sent."""
    from signalos.workflows.telegram import format_digest_briefing, notify_digest_button, send_message
    chat_id = settings.telegram_chat_id
    shown = [
        item for item in digest_items
        if item.get("should_you_read", {}).get("recommendation") in TELEGRAM_SHOWN_RECOMMENDATIONS
    ]
    total = len(shown)
    for idx, item in enumerate(shown, start=1):
        send_message(chat_id, format_digest_briefing(item, index=idx, total=total))
    if shown:
        notify_digest_button(chat_id)
    return total
