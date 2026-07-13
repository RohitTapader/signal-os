from __future__ import annotations

from signalos.core.models import DigestItem, SourceItem
from signalos.source_intelligence.models import CorroboratingSource, SignalScoreBreakdown


def build_corroborating_sources(items: list[SourceItem]) -> list[CorroboratingSource]:
    return [
        CorroboratingSource(
            source_id=item.source_id,
            display_name=item.display_name,
            category=item.source_category,
            tier=item.tier,
            authority_score=item.authority_score,
            title=item.title,
            url=str(item.url),
        )
        for item in items
    ]


def build_intelligence_briefing(
    *,
    primary: SourceItem,
    supporting: list[SourceItem],
    digest: DigestItem,
    score_breakdown: SignalScoreBreakdown,
) -> dict:
    """Single cross-source intelligence briefing — interview-friendly output object."""
    corroborating = build_corroborating_sources(supporting)
    return {
        **digest.model_dump(),
        "briefing_type": "cross_source_intelligence",
        "primary_source": {
            "id": primary.source_id,
            "display_name": primary.display_name,
            "category": primary.source_category,
            "tier": primary.tier,
            "authority_score": primary.authority_score,
            "url": str(primary.url),
        },
        "corroborating_sources": [c.model_dump() for c in corroborating],
        "source_count": 1 + len(corroborating),
        "signal_score_breakdown": score_breakdown.model_dump(),
        "score_explanation": score_breakdown.explanation,
    }


def merged_source_context(primary: SourceItem, supporting: list[SourceItem], max_chars: int = 6000) -> str:
    """Combine primary + secondary source text for richer impact analysis."""
    blocks = [
        f"PRIMARY SOURCE [{primary.display_name} | {primary.source_category} | authority {primary.authority_score}]",
        f"Title: {primary.title}",
        primary.cleaned_text,
    ]
    for item in supporting:
        blocks.append(f"\nSECONDARY SOURCE [{item.display_name} | {item.tier} | {item.source_category}]")
        blocks.append(f"Title: {item.title}")
        blocks.append(item.cleaned_text[:1200])
    text = "\n".join(blocks)
    return text[:max_chars]
