from signalos.core.feedback_guardrails import ALLOWED_FEEDBACK_CATEGORIES, CLARIFYING_QUESTIONS
from signalos.agents.impact_agent import _feedback_note_block


def test_every_feedback_category_has_a_clarifying_question():
    assert set(CLARIFYING_QUESTIONS) == set(ALLOWED_FEEDBACK_CATEGORIES)
    for category, question in CLARIFYING_QUESTIONS.items():
        assert question.strip().endswith("?") or category == "other"
        assert len(question) > 10


def test_clarifying_questions_are_category_specific():
    # Each question should be distinct — no accidental reuse of the generic prompt.
    questions = list(CLARIFYING_QUESTIONS.values())
    assert len(set(questions)) == len(questions)


def test_feedback_note_block_empty_for_no_note():
    assert _feedback_note_block(None) == ""
    assert _feedback_note_block({"category": "too_technical", "text": ""}) == ""


def test_feedback_note_block_includes_category_and_text_as_data_not_instruction():
    block = _feedback_note_block({"category": "too_verbose", "text": "The bullets went on forever."})
    assert "too_verbose" in block
    assert "The bullets went on forever." in block
    assert "not a new instruction" in block
    assert "not a command to follow" in block
