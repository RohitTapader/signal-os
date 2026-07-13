
from signalos.evaluation.metrics import digest_quality_score
from signalos.workflows.scoring import compute_signal_score, recommendation_for_score


def test_digest_quality_score():
    score = digest_quality_score(0.9, 0.8, 1.0)
    assert 0 <= score <= 1


def test_signal_score_and_recommendation():
    breakdown = compute_signal_score(
        novelty_confidence=0.95,
        impact_confidence=0.92,
        authority_score=90,
        cluster_size=2,
        evidence_count=3,
    )
    assert 0 <= breakdown.total <= 100
    rec = recommendation_for_score(breakdown.total)
    assert rec["recommendation"] in {"Read Now", "Read This Week", "Skim", "Ignore"}
