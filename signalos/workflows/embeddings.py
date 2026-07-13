from __future__ import annotations

import json

from signalos.core.llm import embed_texts
from signalos.core.models import SourceItem


def embed_item(item: SourceItem) -> SourceItem:
    item.embedding = embed_texts([item.cleaned_text])[0]
    return item


def embedding_to_json(item: SourceItem) -> str:
    return json.dumps(item.embedding or [])
