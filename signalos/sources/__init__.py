"""Backward-compatible re-exports — prefer signalos.ingestion."""

from signalos.ingestion.arxiv import fetch_arxiv
from signalos.ingestion.collector import collect_all_sources
from signalos.ingestion.github import fetch_github_releases
from signalos.ingestion.rss import fetch_rss_feed

__all__ = ["collect_all_sources", "fetch_arxiv", "fetch_github_releases", "fetch_rss_feed"]
