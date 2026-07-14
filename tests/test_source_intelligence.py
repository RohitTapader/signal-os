from signalos.source_intelligence.scoring import compute_signal_score, explain_signal_score, recommendation_for_score


def test_signal_score_breakdown_has_components():
    breakdown = compute_signal_score(
        novelty_confidence=0.9,
        product_impact_confidence=0.85,
        business_impact_confidence=0.7,
        strategic_relevance_confidence=0.6,
        authority_score=95,
        cluster_size=3,
        evidence_count=2,
        primary_tier="primary",
    )
    assert breakdown.total > 0
    assert len(breakdown.components) == 7
    assert "novelty" in breakdown.explanation.lower() or "Signal" in breakdown.explanation
    text = explain_signal_score(breakdown)
    assert "Breakdown:" in text
    assert "source authority" in text.lower() or "Source Authority" in text


def test_cross_source_cluster_boosts_score():
    solo = compute_signal_score(
        novelty_confidence=0.8,
        product_impact_confidence=0.8,
        business_impact_confidence=0.8,
        strategic_relevance_confidence=0.8,
        authority_score=90,
        cluster_size=1,
        evidence_count=2,
    )
    clustered = compute_signal_score(
        novelty_confidence=0.8,
        product_impact_confidence=0.8,
        business_impact_confidence=0.8,
        strategic_relevance_confidence=0.8,
        authority_score=90,
        cluster_size=3,
        evidence_count=2,
    )
    assert clustered.total >= solo.total


def test_recommendation_decision_changes_reason_not_label():
    # has_decision only sharpens the *reason* text within the top band — the
    # label set is deliberately small (Read/Skim/File Away/Ignore) so the
    # delivery/storage filter (Read+Skim shown, File Away stored only,
    # Ignore dropped) stays simple.
    with_decision = recommendation_for_score(90, has_decision=True)
    without_decision = recommendation_for_score(90, has_decision=False)
    assert with_decision["recommendation"] == "Read"
    assert without_decision["recommendation"] == "Read"
    assert with_decision["reason"] != without_decision["reason"]


def test_recommendation_bands_cover_full_range():
    labels = {recommendation_for_score(s)["recommendation"] for s in (95, 75, 55, 35, 10)}
    assert labels <= {"Read", "Skim", "File Away", "Ignore"}
    assert recommendation_for_score(95)["recommendation"] == "Read"
    assert recommendation_for_score(10)["recommendation"] == "Ignore"
