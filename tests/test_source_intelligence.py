from signalos.source_intelligence.scoring import compute_signal_score, explain_signal_score


def test_signal_score_breakdown_has_components():
    breakdown = compute_signal_score(
        novelty_confidence=0.9,
        impact_confidence=0.85,
        authority_score=95,
        cluster_size=3,
        evidence_count=2,
        primary_tier="primary",
    )
    assert breakdown.total > 0
    assert len(breakdown.components) == 5
    assert "novelty" in breakdown.explanation.lower() or "Signal" in breakdown.explanation
    text = explain_signal_score(breakdown)
    assert "Breakdown:" in text
    assert "source authority" in text.lower() or "Source Authority" in text


def test_cross_source_cluster_boosts_score():
    solo = compute_signal_score(
        novelty_confidence=0.8,
        impact_confidence=0.8,
        authority_score=90,
        cluster_size=1,
        evidence_count=2,
    )
    clustered = compute_signal_score(
        novelty_confidence=0.8,
        impact_confidence=0.8,
        authority_score=90,
        cluster_size=3,
        evidence_count=2,
    )
    assert clustered.total >= solo.total
