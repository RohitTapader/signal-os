from __future__ import annotations

import numpy as np

from signalos.core.models import SourceItem


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=float)
    vb = np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def cluster_items(items: list[SourceItem], threshold: float = 0.86) -> list[list[SourceItem]]:
    """Cross-source clustering — groups same story across OpenAI blog + GitHub + arXiv etc."""
    clusters: list[list[SourceItem]] = []
    used: set[int] = set()

    for i, item in enumerate(items):
        if i in used or not item.embedding:
            continue
        cluster = [item]
        used.add(i)
        for j, other in enumerate(items[i + 1 :], start=i + 1):
            if j in used or not other.embedding:
                continue
            if cosine_similarity(item.embedding, other.embedding) >= threshold:
                cluster.append(other)
                used.add(j)
        clusters.append(cluster)

    return clusters


def pick_primary_item(cluster: list[SourceItem]) -> SourceItem:
    """Prefer primary-tier, highest-authority source as briefing anchor."""

    def sort_key(item: SourceItem) -> tuple[int, int, int]:
        tier_rank = 0 if item.tier == "primary" else 1
        return (tier_rank, -item.authority_score, 0 if item.source_category == "official" else 1)

    return sorted(cluster, key=sort_key)[0]


def supporting_items(cluster: list[SourceItem], primary: SourceItem) -> list[SourceItem]:
    return [item for item in cluster if str(item.url) != str(primary.url)]
