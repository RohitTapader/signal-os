
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class SourceItem(BaseModel):
    source_id: str = ""
    display_name: str = ""
    source_name: str
    source_type: Literal["rss", "arxiv", "github", "html", "cli", "atom"]
    title: str
    url: HttpUrl
    published_at: Optional[str] = None
    author: Optional[str] = None
    raw_text: str
    cleaned_text: str = ""
    category: Optional[str] = None
    embedding: Optional[list[float]] = None
    source_category: str = "media"
    tier: Literal["primary", "secondary"] = "primary"
    authority_score: int = Field(default=70, ge=0, le=100)
    signal_topic: str = "general"


class NoveltyResult(BaseModel):
    verdict: Literal["NEW", "DUPLICATE", "UPDATE", "NEEDS_HUMAN_REVIEW"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    similar_item_ids: list[int] = Field(default_factory=list)


class ImpactResult(BaseModel):
    # Executive intelligence fields. These are intentionally richer than a plain summary.
    signal_type: str = "general"
    signal_score: int = Field(default=0, ge=0, le=100)
    signal_score_breakdown: dict | None = None
    score_explanation: str = ""
    headline: str
    context: str = ""
    executive_summary: str = ""
    whats_new: str = ""
    what_changed: list[str] = Field(default_factory=list)
    key_innovation: str = ""
    pm_takeaway: str = ""
    # Direct, specific strategic callouts for an AI PM — deliberately separate from
    # the more general why_it_matters bullets so a reader gets one concrete "so what"
    # per axis instead of having to infer it from a paragraph.
    roadmap_relevance: str = ""
    business_metric_impact: str = ""
    why_it_matters: dict[str, str | list[str]] = Field(
        default_factory=lambda: {
            "product": "",
            "business": "",
            "competitive": "",
            "product_business": [],
        }
    )
    recommended_action: str = ""
    companies_impacted: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    source_url: str
    supporting_evidence: list[dict[str, str]] = Field(default_factory=list)
    limitations: str = ""
    should_you_read: dict[str, str] = Field(
        default_factory=lambda: {"recommendation": "Read Later", "reason": ""}
    )


class PreferenceProfile(BaseModel):
    """Bounded per-chat preference state. Values are clamped by
    signalos.core.feedback_guardrails.PREFERENCE_BOUNDS on every write —
    this model only ever reflects the result of small, fixed-step deltas."""
    technical_depth: float = Field(default=0.5, ge=0.0, le=1.0)
    summary_length: float = Field(default=0.5, ge=0.0, le=1.0)
    recommendation_strictness: float = Field(default=0.5, ge=0.0, le=1.0)
    source_trust_bias: float = Field(default=0.0, ge=-0.2, le=0.2)
    category_bias: dict[str, float] = Field(default_factory=dict)


class FeedbackClassification(BaseModel):
    category: Literal[
        "content_accuracy",
        "wrong_novelty_call",
        "source_broken",
        "slide_rendering_bug",
        "other",
    ]
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class RCAResult(BaseModel):
    title: str
    likely_cause: str
    affected_component: str
    risk_level: Literal["low", "medium", "high"]
    suggested_fix: str
    rollback_plan: str
    confidence: float = Field(ge=0, le=1)


class RepairProposal(BaseModel):
    title: str
    proposal_text: str
    risk_level: Literal["low", "medium", "high"]
    status: str = "pending_review"


class DigestItem(BaseModel):
    item_id: int
    title: str
    source_id: str = ""
    source_name: str
    source_display_name: str = ""
    source_category: str = "media"
    source_tier: str = "primary"
    authority_score: int = 70
    source_url: str
    category_tag: str
    headline: str
    context: str = ""
    executive_summary: str = ""
    whats_new: str = ""
    key_innovation: str = ""
    pm_takeaway: str = ""
    roadmap_relevance: str = ""
    business_metric_impact: str = ""
    signal_type: str = "general"
    signal_score: int = 0
    signal_score_breakdown: dict | None = None
    score_explanation: str = ""
    corroborating_sources: list[dict[str, str | int]] = Field(default_factory=list)
    source_count: int = 1
    what_changed: list[str]
    why_it_matters: dict[str, str | list[str]]
    recommended_action: str = ""
    companies_impacted: list[str] = Field(default_factory=list)
    confidence: float
    should_you_read: dict[str, str] = Field(
        default_factory=lambda: {"recommendation": "Read Later", "reason": ""}
    )
    supporting_evidence: list[dict[str, str]] = Field(default_factory=list)
    limitations: str = ""
    published_at: str | None = None


class RunSummary(BaseModel):
    run_id: str
    ingested: int
    novel_items: int
    sent_items: int
    duplicates: int
    updates: int
    errors: int = 0
    started_at: datetime
    finished_at: datetime | None = None
