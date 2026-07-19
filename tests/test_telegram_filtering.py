from signalos.workflows import pipeline as pl
import signalos.workflows.telegram as telegram


def _item(recommendation: str, headline: str) -> dict:
    return {
        "headline": headline,
        "should_you_read": {"recommendation": recommendation, "reason": "because"},
        "source_category": "official",
        "source_display_name": "Src",
        "what_changed": [],
        "supporting_evidence": [],
    }


def _patch_telegram():
    sent, button_calls = [], []
    original_send, original_button = telegram.send_message, telegram.notify_digest_button
    telegram.send_message = lambda chat_id, text, reply_markup=None: sent.append(text)
    telegram.notify_digest_button = lambda chat_id: button_calls.append(chat_id)
    return sent, button_calls, (original_send, original_button)


def _restore_telegram(originals):
    telegram.send_message, telegram.notify_digest_button = originals


def test_send_to_telegram_only_sends_read_and_skim():
    sent, button_calls, originals = _patch_telegram()
    try:
        digest_items = [
            _item("Read", "Read item"),
            _item("Skim", "Skim item"),
            _item("File Away", "Filed item"),
        ]
        count = pl.send_to_telegram(digest_items, run_id="test")

        assert count == 2
        assert len(sent) == 2
        assert any("Read item" in s for s in sent)
        assert any("Skim item" in s for s in sent)
        assert not any("Filed item" in s for s in sent)
        assert len(button_calls) == 1
    finally:
        _restore_telegram(originals)


def test_send_to_telegram_skips_button_when_nothing_shown():
    sent, button_calls, originals = _patch_telegram()
    try:
        digest_items = [_item("File Away", "Filed item"), _item("Ignore", "Ignored item")]
        count = pl.send_to_telegram(digest_items, run_id="test")

        assert count == 0
        assert sent == []
        assert button_calls == []
    finally:
        _restore_telegram(originals)
