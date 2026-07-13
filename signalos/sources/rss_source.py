from __future__ import annotations

import feedparser

from signalos.core.models import SourceItem


def fetch_rss_feed(source_name: str, feed_url: str, category: str = "general") -> list[SourceItem]:
    feed = feedparser.parse(feed_url)
    items: list[SourceItem] = []

    for entry in feed.entries[:10]:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
        published = getattr(entry, "published", None)
        author = getattr(entry, "author", None)

        if not title or not link:
            continue

        items.append(
            SourceItem(
                source_name=source_name,
                source_type="rss",
                title=title,
                url=link,
                published_at=published,
                author=author,
                raw_text=summary or title,
                cleaned_text="",
                source_category=category,
            )
        )

    return items
