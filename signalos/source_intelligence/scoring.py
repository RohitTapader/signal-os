from __future__ import annotations

from signalos.core.config import settings
from signalos.source_intelligence.models import SignalScoreBreakdown, SignalScoreComponent


def compute_signal_score(
    *,
    novelty_confidence: float,
    product_impact_confidence: float,
    business_impact_confidence: float,
    strategic_relevance_confidence: float,
    authority_score: int,
    cluster_size: int,
    evidence_count: int,
    primary_tier: str = "primary",
    has_decision: bool = False,
) -> SignalScoreBreakdown:
    """Transparent, PM-relevant signal score with a per-component breakdown.

    Deterministic given its inputs — the only non-deterministic part of the
    pipeline is the LLM estimating the three confidence sub-scores from
    source text (signalos.agents.impact_agent); everything from here down
    (weighting, banding, the recommendation label) is plain code.
    """

    novelty_raw = max(0.0, min(1.0, novelty_confidence)) * 100
    product_raw = max(0.0, min(1.0, product_impact_confidence)) * 100
    business_raw = max(0.0, min(1.0, business_impact_confidence)) * 100
    strategic_raw = max(0.0, min(1.0, strategic_relevance_confidence)) * 100
    authority_raw = float(max(0, min(100, authority_score)))
    # Trend momentum proxy: how many independent sources are already covering
    # this story. No separate momentum model — cross-source corroboration is
    # the deterministic, evidence-based signal for "this is picking up."
    momentum_raw = min(100.0, max(0.0, (cluster_size - 1) * 25.0))
    evidence_raw = min(100.0, max(0.0, evidence_count * 20.0))

    weights = {
        "novelty": 0.20,
        "product_impact": 0.18,
        "business_impact": 0.18,
        "strategic_relevance": 0.14,
        "source_authority": 0.16,
        "trend_momentum": 0.08,
        "evidence_strength": 0.06,
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
            name="product_impact",
            weight=weights["product_impact"],
            raw_score=round(product_raw, 1),
            weighted_points=round(weights["product_impact"] * product_raw, 1),
            explanation=f"Product impact confidence {product_impact_confidence:.0%} — how much this changes what an AI PM builds or ships.",
        ),
        SignalScoreComponent(
            name="business_impact",
            weight=weights["business_impact"],
            raw_score=round(business_raw, 1),
            weighted_points=round(weights["business_impact"] * business_raw, 1),
            explanation=f"Business impact confidence {business_impact_confidence:.0%} — how much this moves a concrete business metric.",
        ),
        SignalScoreComponent(
            name="strategic_relevance",
            weight=weights["strategic_relevance"],
            raw_score=round(strategic_raw, 1),
            weighted_points=round(weights["strategic_relevance"] * strategic_raw, 1),
            explanation=f"Strategic relevance confidence {strategic_relevance_confidence:.0%} — competitive/positioning weight beyond immediate product or revenue impact.",
        ),
        SignalScoreComponent(
            name="source_authority",
            weight=weights["source_authority"],
            raw_score=round(authority_raw, 1),
            weighted_points=round(weights["source_authority"] * authority_raw, 1),
            explanation=f"Source authority {authority_score}/100 — trust weight from curated catalog ({primary_tier} tier).",
        ),
        SignalScoreComponent(
            name="trend_momentum",
            weight=weights["trend_momentum"],
            raw_score=round(momentum_raw, 1),
            weighted_points=round(weights["trend_momentum"] * momentum_raw, 1),
            explanation=(
                f"{cluster_size} source(s) covering this — "
                + ("multiple independent sources means real momentum, not a one-off." if cluster_size > 1 else "single-source so far, no corroborated momentum yet.")
            ),
        ),
        SignalScoreComponent(
            name="evidence_strength",
            weight=weights["evidence_strength"],
            raw_score=round(evidence_raw, 1),
            weighted_points=round(weights["evidence_strength"] * evidence_raw, 1),
            explanation=f"{evidence_count} grounded evidence item(s) extracted from source text.",
        ),
    ]

    total = int(round(sum(c.weighted_points for c in components)))
    total = max(0, min(100, total))
    recommendation = recommendation_for_score(total, has_decision=has_decision)

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


def recommendation_for_score(score: int, *, has_decision: bool = False) -> dict[str, str]:
    """Deterministic score-band → grounded PM action label.

    Four labels only: Read, Skim, File Away, Ignore. Read and Skim are the
    only labels delivered to Telegram; File Away is stored but not sent;
    Ignore is not persisted at all (see signalos.workflows.pipeline._build_digest).
    has_decision (from the agent's decision_supported field) only changes the
    *reason* text within the top band, not the label itself.
    """
    t = settings.signal_score_thresholds
    if score >= t["read"]:
        if has_decision:
            return {
                "recommendation": "Read",
                "reason": "This directly informs a decision you're likely facing — worth reading in full today.",
            }
        return {
            "recommendation": "Read",
            "reason": "High-confidence, high-relevance signal — worth reading in full today.",
        }
    if score >= t["skim"]:
        return {
            "recommendation": "Skim",
            "reason": "Relevant, but a quick scan is enough — no immediate action needed.",
        }
    if score >= t["file_away"]:
        return {
            "recommendation": "File Away",
            "reason": "Low urgency right now, but may be useful reference later.",
        }
    return {
        "recommendation": "Ignore",
        "reason": "Low relevance to current AI PM priorities.",
    }


def _top_drivers(components: list[SignalScoreComponent], n: int = 2) -> list[str]:
    ranked = sorted(components, key=lambda c: c.weighted_points, reverse=True)
    return [f"{c.name.replace('_', ' ')} (+{c.weighted_points:.0f})" for c in ranked[:n]]
