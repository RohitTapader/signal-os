from __future__ import annotations

import requests

from signalos.core.config import settings
from signalos.core.models import SourceItem


def fetch_github_releases(owner: str, repo: str, category: str = "tooling_sdk", max_results: int = 5) -> list[SourceItem]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    url = f"https://api.github.com/repos/{owner}/{repo}/releases?per_page={max_results}"
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    items: list[SourceItem] = []
    for rel in resp.json():
        title = rel.get("name") or rel.get("tag_name")
        body = rel.get("body") or ""
        html_url = rel.get("html_url")
        if not title or not html_url:
            continue

        items.append(
            SourceItem(
                source_name=f"github:{owner}/{repo}",
                source_type="github",
                title=title,
                url=html_url,
                published_at=rel.get("published_at"),
                raw_text=body or title,
                cleaned_text="",
                source_category=category,
            )
        )
    return items
