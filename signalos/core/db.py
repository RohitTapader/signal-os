from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from signalos.core.config import settings


def _normalized_database_url(url: str) -> str:
    """Managed Postgres providers (Vercel Storage, Heroku-style, etc.) commonly
    hand out 'postgres://' URLs, but SQLAlchemy 2.0 only accepts 'postgresql://'."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


DATABASE_URL = _normalized_database_url(settings.database_url)

connect_args: dict[str, Any] = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(30))
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContentItem(Base):
    __tablename__ = "content_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_name: Mapped[str] = mapped_column(String(120))
    source_display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source_type: Mapped[str] = mapped_column(String(30))
    source_category: Mapped[str] = mapped_column(String(60), default="media")
    source_tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    authority_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(800))
    url: Mapped[str] = mapped_column(Text, unique=True)
    published_at: Mapped[str | None] = mapped_column(String(60), nullable=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    cleaned_text: Mapped[str] = mapped_column(Text)
    embedding_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    novelty_verdict: Mapped[str | None] = mapped_column(String(40), nullable=True)
    novelty_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    novelty_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    cluster_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemEvent(Base):
    __tablename__ = "system_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    event_type: Mapped[str] = mapped_column(String(120))
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedbackEvent(Base):
    __tablename__ = "feedback_event"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80))
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RepairProposalRow(Base):
    __tablename__ = "repair_proposal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    proposal_text: Mapped[str] = mapped_column(Text)
    risk_level: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(40), default="pending_review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CostLedger(Base):
    __tablename__ = "cost_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    task_type: Mapped[str] = mapped_column(String(120))
    model_name: Mapped[str] = mapped_column(String(80))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SystemSetting(Base):
    __tablename__ = "system_setting"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UserPreferenceState(Base):
    """Bounded, per-chat preference profile. Every field has a hard clamp
    (signalos.core.feedback_guardrails.PREFERENCE_BOUNDS) and all writes go
    through signalos.core.preferences, which enforces a shared daily change
    budget — this table can only ever move in small, pre-approved steps."""
    __tablename__ = "user_preference_state"

    chat_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    technical_depth: Mapped[float] = mapped_column(Float, default=0.5)
    summary_length: Mapped[float] = mapped_column(Float, default=0.5)
    recommendation_strictness: Mapped[float] = mapped_column(Float, default=0.5)
    source_trust_bias: Mapped[float] = mapped_column(Float, default=0.0)
    category_bias_json: Mapped[str] = mapped_column(Text, default="{}")
    daily_change_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_change_date: Mapped[str] = mapped_column(String(10), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PendingInteraction(Base):
    """Tracks the single in-flight multi-turn Telegram follow-up per chat
    (e.g. awaiting feedback elaboration or a regenerate angle). Stateless
    webhook deliveries look this up to know what a plain-text reply means."""
    __tablename__ = "pending_interaction"

    chat_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    kind: Mapped[str] = mapped_column(String(60))
    context_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_content_item_columns()


def _migrate_content_item_columns() -> None:
    """Lightweight SQLite migration for source intelligence metadata."""
    inspector = inspect(engine)
    if "content_item" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("content_item")}
    additions = {
        "source_id": "VARCHAR(80)",
        "source_display_name": "VARCHAR(200)",
        "source_tier": "VARCHAR(20)",
        "authority_score": "INTEGER",
    }
    with engine.begin() as conn:
        for name, col_type in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE content_item ADD COLUMN {name} {col_type}"))
