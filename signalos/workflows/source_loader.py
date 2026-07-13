from __future__ import annotations

from signalos.core.models import SourceItem
from signalos.ingestion.collector import collect_all_sources


def discover_sources() -> list[SourceItem]:
    """Discover items from the curated source intelligence catalog."""
    return collect_all_sources()
