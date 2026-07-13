from __future__ import annotations

import requests

from signalos.core.config import settings
from signalos.core.models import SourceItem
from signalos.ingestion.rss import _to_source_item
from signalos.source_intelligence.models import SourceDefinition


def fetch_github_releases(defn: SourceDefinition) -> list[SourceItem]:
    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    items: list[SourceItem] = []
    for repo in defn.repos:
        owner, name = repo.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{name}/releases?per_page={defn.max_results}"
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        for rel in resp.json():
            title = rel.get("name") or rel.get("tag_name")
            body = rel.get("body") or ""
            html_url = rel.get("html_url")
            if not title or not html_url:
                continue

            repo_defn = defn.model_copy(update={
                "display_name": f"{defn.display_name} ({repo})",
                "id": f"{defn.id}_{repo.replace('/', '_')}",
            })
            items.append(
                _to_source_item(
                    repo_defn,
                    title=title,
                    link=html_url,
                    summary=body or title,
                    published=rel.get("published_at"),
                    author=f"{owner}/{name}",
                    source_type="github",
                )
            )
    return items
