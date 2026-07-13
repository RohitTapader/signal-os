from __future__ import annotations

from urllib.parse import quote

import feedparser

from signalos.core.models import SourceItem
from signalos.ingestion.rss import _to_source_item
from signalos.source_intelligence.models import SourceDefinition


def fetch_arxiv(defn: SourceDefinition) -> list[SourceItem]:
    query = defn.query or "cat:cs.AI OR cat:cs.LG OR cat:cs.CL"
    api_url = (
        "http://export.arxiv.org/api/query?"
        f"search_query={quote(query)}&start=0&max_results={defn.max_results}"
        "&sortBy=submittedDate&sortOrder=descending"
    )
    feed = feedparser.parse(api_url)

    items: list[SourceItem] = []
    for entry in feed.entries:
        items.append(
            _to_source_item(
                defn,
                title=entry.title,
                link=entry.link,
                summary=getattr(entry, "summary", entry.title),
                published=getattr(entry, "published", None),
                author=getattr(entry, "author", None),
                source_type="arxiv",
            )
        )
    return items
