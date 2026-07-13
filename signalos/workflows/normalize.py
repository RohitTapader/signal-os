from __future__ import annotations

import re
from bs4 import BeautifulSoup

from signalos.core.models import SourceItem


def clean_html(text: str) -> str:
    soup = BeautifulSoup(text, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    cleaned = soup.get_text(" ", strip=True)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_item(item: SourceItem) -> SourceItem:
    text = f"{item.title}. {item.raw_text}"
    item.cleaned_text = clean_html(text)[:5000]
    return item
