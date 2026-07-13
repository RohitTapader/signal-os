from signalos.evaluation.feedback_metrics import (
    digest_satisfaction_improvement,
    feedback_category_accuracy,
    guardrail_violation_rate,
    preference_adaptation_quality,
    regenerate_success_rate,
)


def test_feedback_category_accuracy():
    labeled = [("too_technical", "too_technical"), ("too_verbose", "not_relevant"), ("other", "other")]
    assert feedback_category_accuracy(labeled) == round(2 / 3, 4)


def test_feedback_category_accuracy_empty():
    assert feedback_category_accuracy([]) == 0.0


def test_preference_adaptation_quality_directional():
    before = {"technical_depth": 0.5, "source_trust_bias": 0.0}
    after = {"technical_depth": 0.35, "source_trust_bias": 0.0}
    expected = {"technical_depth": -1, "source_trust_bias": 0}
    assert preference_adaptation_quality(before, after, expected) == 1.0


def test_preference_adaptation_quality_wrong_direction():
    before = {"technical_depth": 0.5}
    after = {"technical_depth": 0.6}
    expected = {"technical_depth": -1}
    assert preference_adaptation_quality(before, after, expected) == 0.0


def test_regenerate_success_rate():
    assert regenerate_success_rate([True, True, False, True]) == 0.75
    assert regenerate_success_rate([]) == 0.0


def test_digest_satisfaction_improvement():
    assert digest_satisfaction_improvement(0.6, 0.8) == 0.2


def test_guardrail_violation_rate():
    assert guardrail_violation_rate(100, 3) == 0.03
    assert guardrail_violation_rate(0, 0) == 0.0
