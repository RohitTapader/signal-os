"""Backward-compatible shim — use signalos.source_intelligence.clustering instead."""

from signalos.source_intelligence.clustering import cluster_items, cosine_similarity, pick_primary_item, supporting_items

__all__ = ["cluster_items", "cosine_similarity", "pick_primary_item", "supporting_items"]
