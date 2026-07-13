from __future__ import annotations

import feedparser

from signalos.core.models import SourceItem
from signalos.source_intelligence.models import SourceDefinition


def fetch_rss_feed(defn: SourceDefinition, limit: int | None = None) -> list[SourceItem]:
    if not defn.url:
        return []

    feed = feedparser.parse(defn.url)
    max_items = limit or defn.max_results
    items: list[SourceItem] = []

    for entry in feed.entries[:max_items]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        published = getattr(entry, "published", None)
        author = getattr(entry, "author", None)

        if not title or not link:
            continue

        items.append(_to_source_item(defn, title=title, link=link, summary=summary, published=published, author=author))

    return items


def _to_source_item(
    defn: SourceDefinition,
    *,
    title: str,
    link: str,
    summary: str,
    published: str | None,
    author: str | None,
    source_type: str = "rss",
) -> SourceItem:
    return SourceItem(
        source_id=defn.id,
        display_name=defn.display_name,
        source_name=defn.id,
        source_type=source_type,
        title=title,
        url=link,
        published_at=published,
        author=author,
        raw_text=summary or title,
        cleaned_text="",
        source_category=defn.category,
        tier=defn.tier,
        authority_score=defn.authority_score,
        signal_topic=defn.topics[0] if defn.topics else "general",
    )
