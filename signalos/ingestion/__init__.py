"""Ingestion adapters — fetch raw items from external feeds defined in the source catalog."""

from signalos.ingestion.collector import collect_all_sources

__all__ = ["collect_all_sources"]
