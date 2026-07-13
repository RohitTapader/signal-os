from __future__ import annotations

from urllib.parse import quote

import feedparser

from signalos.core.models import SourceItem


def fetch_arxiv(query: str, category: str = "research", max_results: int = 10) -> list[SourceItem]:
    api_url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={quote(query)}&start=0&max_results={max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    feed = feedparser.parse(api_url)

    items: list[SourceItem] = []
    for entry in feed.entries:
        items.append(
            SourceItem(
                source_name="arxiv_ai",
                source_type="arxiv",
                title=entry.title,
                url=entry.link,
                published_at=getattr(entry, "published", None),
                author=getattr(entry, "author", None),
                raw_text=getattr(entry, "summary", entry.title),
                cleaned_text="",
                source_category=category,
            )
        )
    return items
