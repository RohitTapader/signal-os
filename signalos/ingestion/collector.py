from __future__ import annotations

from datetime import datetime, timedelta, timezone

from dateutil import parser as date_parser

from signalos.core.config import settings
from signalos.core.logging import log_json
from signalos.core.models import SourceItem
from signalos.ingestion.arxiv import fetch_arxiv
from signalos.ingestion.github import fetch_github_releases
from signalos.ingestion.rss import fetch_rss_feed
from signalos.source_intelligence.registry import SourceRegistry, get_registry


def _within_lookback(item: SourceItem, cutoff: datetime) -> bool:
    """Keep the item if it was published on/after the cutoff. Items with an
    unparseable or missing published date are kept rather than silently dropped."""
    if not item.published_at:
        return True
    try:
        published = date_parser.parse(item.published_at)
    except (ValueError, OverflowError):
        return True
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return published >= cutoff


def collect_all_sources(registry: SourceRegistry | None = None) -> list[SourceItem]:
    """Fetch from all enabled sources; primary sources first, then by authority.

    Restricted to the prior day's activity (settings.ingestion_lookback_hours),
    matching the daily 8am IST run pulling what happened the previous day.
    """
    reg = registry or get_registry()
    items: list[SourceItem] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.ingestion_lookback_hours)

    for defn in reg.enabled_sources():
        try:
            fetched = _fetch_definition(defn)
            in_window = [item for item in fetched if _within_lookback(item, cutoff)]
            items.extend(in_window)
            log_json(
                "ingestion_success",
                source_id=defn.id,
                display_name=defn.display_name,
                category=defn.category,
                tier=defn.tier,
                item_count=len(in_window),
                skipped_stale=len(fetched) - len(in_window),
            )
        except Exception as exc:
            log_json("ingestion_failure", source_id=defn.id, display_name=defn.display_name, error=str(exc))

    return sorted(items, key=lambda item: (0 if item.tier == "primary" else 1, -item.authority_score))


def _fetch_definition(defn) -> list[SourceItem]:
    if defn.type in ("rss", "atom"):
        return fetch_rss_feed(defn)
    if defn.type == "arxiv":
        return fetch_arxiv(defn)
    if defn.type == "github":
        return fetch_github_releases(defn)
    return []
