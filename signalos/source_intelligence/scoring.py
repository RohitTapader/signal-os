from __future__ import annotations

from signalos.core.config import settings
from signalos.source_intelligence.models import SignalScoreBreakdown, SignalScoreComponent


def compute_signal_score(
    *,
    novelty_confidence: float,
    impact_confidence: float,
    authority_score: int,
    cluster_size: int,
    evidence_count: int,
    primary_tier: str = "primary",
) -> SignalScoreBreakdown:
    """Transparent signal score with per-component breakdown for PM explainability."""

    novelty_raw = max(0.0, min(1.0, novelty_confidence)) * 100
    impact_raw = max(0.0, min(1.0, impact_confidence)) * 100
    authority_raw = float(max(0, min(100, authority_score)))
    cluster_raw = min(100.0, max(0.0, (cluster_size - 1) * 25.0))
    evidence_raw = min(100.0, max(0.0, evidence_count * 20.0))

    weights = {
        "novelty": 0.28,
        "impact": 0.28,
        "source_authority": 0.24,
        "cross_source_corroboration": 0.12,
        "evidence_depth": 0.08,
    }

    components = [
        SignalScoreComponent(
            name="novelty",
            weight=weights["novelty"],
            raw_score=round(novelty_raw, 1),
            weighted_points=round(weights["novelty"] * novelty_raw, 1),
            explanation=f"Novelty confidence {novelty_confidence:.0%} — how new vs. prior signals in our corpus.",
        ),
        SignalScoreComponent(
            name="impact",
            weight=weights["impact"],
            raw_score=round(impact_raw, 1),
            weighted_points=round(weights["impact"] * impact_raw, 1),
            explanation=f"Impact confidence {impact_confidence:.0%} — expected product/business relevance for an AI PM.",
        ),
        SignalScoreComponent(
            name="source_authority",
            weight=weights["source_authority"],
            raw_score=round(authority_raw, 1),
            weighted_points=round(weights["source_authority"] * authority_raw, 1),
            explanation=f"Source authority {authority_score}/100 — trust weight from curated catalog ({primary_tier} tier).",
        ),
        SignalScoreComponent(
            name="cross_source_corroboration",
            weight=weights["cross_source_corroboration"],
            raw_score=round(cluster_raw, 1),
            weighted_points=round(weights["cross_source_corroboration"] * cluster_raw, 1),
            explanation=(
                f"{cluster_size} source(s) in cluster — "
                + ("multiple independent sources agree on this signal." if cluster_size > 1 else "single-source signal, no cross-source corroboration yet.")
            ),
        ),
        SignalScoreComponent(
            name="evidence_depth",
            weight=weights["evidence_depth"],
            raw_score=round(evidence_raw, 1),
            weighted_points=round(weights["evidence_depth"] * evidence_raw, 1),
            explanation=f"{evidence_count} grounded evidence item(s) extracted from source text.",
        ),
    ]

    total = int(round(sum(c.weighted_points for c in components)))
    total = max(0, min(100, total))
    recommendation = recommendation_for_score(total)

    explanation = (
        f"Signal {total}/100 → {recommendation['recommendation']}. "
        f"Top drivers: {', '.join(_top_drivers(components))}. "
        f"{recommendation['reason']}"
    )

    return SignalScoreBreakdown(total=total, components=components, explanation=explanation)


def explain_signal_score(breakdown: SignalScoreBreakdown) -> str:
    lines = [f"Signal Score: {breakdown.total}/100", breakdown.explanation, "", "Breakdown:"]
    for comp in breakdown.components:
        pct = int(comp.weight * 100)
        lines.append(
            f"• {comp.name.replace('_', ' ').title()} ({pct}% weight): "
            f"{comp.raw_score:.0f} raw → +{comp.weighted_points:.1f} pts — {comp.explanation}"
        )
    return "\n".join(lines)


def recommendation_for_score(score: int) -> dict[str, str]:
    if score >= settings.signal_score_thresholds["read_now"]:
        return {
            "recommendation": "Read Now",
            "reason": "High-authority source with strong novelty, impact, and corroboration.",
        }
    if score >= settings.signal_score_thresholds["read_this_week"]:
        return {
            "recommendation": "Read This Week",
            "reason": "Relevant AI PM signal worth reviewing soon.",
        }
    if score >= settings.signal_score_thresholds["skim"]:
        return {
            "recommendation": "Skim",
            "reason": "Useful context but not urgent for today's product decisions.",
        }
    return {
        "recommendation": "Ignore",
        "reason": "Low priority for current AI PM focus window.",
    }


def _top_drivers(components: list[SignalScoreComponent], n: int = 2) -> list[str]:
    ranked = sorted(components, key=lambda c: c.weighted_points, reverse=True)
    return [f"{c.name.replace('_', ' ')} (+{c.weighted_points:.0f})" for c in ranked[:n]]
