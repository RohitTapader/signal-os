from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceCategory = Literal["official", "research", "community", "media", "open_source"]
SourceTier = Literal["primary", "secondary"]
IngestionType = Literal["rss", "arxiv", "github", "atom"]

SOURCE_CATEGORY_LABELS: dict[str, str] = {
    "official": "Official",
    "research": "Research",
    "community": "Community",
    "media": "Media",
    "open_source": "Open Source",
}


class SourceDefinition(BaseModel):
    """Curated source catalog entry — human-friendly and interview-explainable."""

    id: str
    display_name: str
    category: SourceCategory
    tier: SourceTier
    authority_score: int = Field(ge=0, le=100)
    type: IngestionType
    url: str | None = None
    query: str | None = None
    repos: list[str] = Field(default_factory=list)
    max_results: int = 10
    topics: list[str] = Field(default_factory=list)
    description: str = ""
    enabled: bool = True


class SignalScoreComponent(BaseModel):
    name: str
    weight: float
    raw_score: float
    weighted_points: float
    explanation: str


class SignalScoreBreakdown(BaseModel):
    total: int = Field(ge=0, le=100)
    components: list[SignalScoreComponent]
    explanation: str


class CorroboratingSource(BaseModel):
    source_id: str
    display_name: str
    category: str
    tier: str
    authority_score: int
    title: str
    url: str
