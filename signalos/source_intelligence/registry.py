from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml
from pydantic import TypeAdapter

from signalos.core.config import SOURCE_YAML
from signalos.source_intelligence.models import SOURCE_CATEGORY_LABELS, SourceDefinition

_source_adapter = TypeAdapter(list[SourceDefinition])


class SourceRegistry:
    """Loads and queries the curated source catalog for AI Product Managers."""

    def __init__(self, sources: list[SourceDefinition], categories: dict[str, str]):
        self.sources = sources
        self.categories = categories
        self._by_id = {s.id: s for s in sources}

    def get(self, source_id: str) -> SourceDefinition | None:
        return self._by_id.get(source_id)

    def enabled_sources(self) -> list[SourceDefinition]:
        return [s for s in self.sources if s.enabled]

    def primary_sources(self) -> list[SourceDefinition]:
        return [s for s in self.enabled_sources() if s.tier == "primary"]

    def secondary_sources(self) -> list[SourceDefinition]:
        return [s for s in self.enabled_sources() if s.tier == "secondary"]

    def category_label(self, category: str) -> str:
        return self.categories.get(category) or SOURCE_CATEGORY_LABELS.get(category, category)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "categories": self.categories,
            "tiers": {
                "primary": "Official product signals — releases, changelogs, platform updates",
                "secondary": "Research depth — arXiv papers that corroborate or extend primary signals",
            },
            "sources": [
                {
                    "id": s.id,
                    "display_name": s.display_name,
                    "category": s.category,
                    "category_label": self.category_label(s.category),
                    "tier": s.tier,
                    "authority_score": s.authority_score,
                    "type": s.type,
                    "topics": s.topics,
                    "description": s.description,
                    "enabled": s.enabled,
                }
                for s in self.sources
            ],
        }


def load_source_registry(path=None) -> SourceRegistry:
    yaml_path = path or SOURCE_YAML
    if not yaml_path.exists():
        return SourceRegistry([], SOURCE_CATEGORY_LABELS)

    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    raw_sources = data.get("sources", [])
    normalized = [_normalize_legacy_source(item) for item in raw_sources]
    sources = _source_adapter.validate_python(normalized)
    categories = {**SOURCE_CATEGORY_LABELS, **(data.get("category_labels") or {})}
    return SourceRegistry(sources, categories)


@lru_cache(maxsize=1)
def get_registry() -> SourceRegistry:
    return load_source_registry()


def _normalize_legacy_source(item: dict[str, Any]) -> dict[str, Any]:
    """Map older flat configs to the new source intelligence schema."""
    if "display_name" in item and "authority_score" in item:
        return item

    legacy_category = item.get("category", "general")
    category_map = {
        "model_release": "official",
        "tooling_sdk": "open_source",
        "research": "research",
        "industry_funding": "media",
        "benchmark": "media",
        "regulation": "official",
        "general": "media",
    }
    return {
        "id": item.get("id") or item.get("name"),
        "display_name": item.get("display_name") or item.get("name", "").replace("_", " ").title(),
        "category": item.get("source_category") or category_map.get(legacy_category, "media"),
        "tier": item.get("tier", "secondary" if item.get("type") == "arxiv" else "primary"),
        "authority_score": item.get("authority_score", 70),
        "type": item.get("type"),
        "url": item.get("url"),
        "query": item.get("query"),
        "repos": item.get("repos", []),
        "max_results": item.get("max_results", 10),
        "topics": item.get("topics", [legacy_category]),
        "description": item.get("description", ""),
        "enabled": item.get("enabled", True),
    }
