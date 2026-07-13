from signalos.core.models import SourceItem
from signalos.workflows.normalize import normalize_item

def test_normalize_item():
    item = SourceItem(
        source_name="x",
        source_type="rss",
        title="Hello",
        url="https://example.com",
        raw_text="<p>Hi</p>",
    )
    norm = normalize_item(item)
    assert "Hi" in norm.cleaned_text
