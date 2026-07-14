
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[2]
SOURCE_YAML = ROOT / "signalos" / "config" / "sources.yaml"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(alias="TELEGRAM_CHAT_ID")
    database_url: str = Field(default="sqlite:///./signal.db", alias="DATABASE_URL")
    app_base_url: str = Field(default="http://localhost:8000", alias="APP_BASE_URL")
    timezone: str = Field(default="Asia/Kolkata", alias="TIMEZONE")

    # Targets ~$6/month (30 * 0.20 = $6.00) with headroom before hitting $7.
    # At current model routing + daily_max_items=3, expected spend is ~$0.03-0.05/day,
    # so this cap is a hard safety net for spikes (bad day, retries, heavy feedback volume),
    # not the expected steady-state cost.
    daily_token_cap: int = Field(default=40000, alias="DAILY_TOKEN_CAP")
    daily_spend_cap_usd: float = Field(default=0.20, alias="DAILY_SPEND_CAP_USD")
    daily_max_items: int = Field(default=3, alias="DAILY_MAX_ITEMS")

    # Daily run pulls the prior day's source activity. 36h (not a flat 24h) gives a buffer
    # for feeds with timezone drift or delayed publish timestamps so nothing from
    # yesterday gets silently missed at the 8am IST cutoff.
    ingestion_lookback_hours: int = Field(default=36, alias="INGESTION_LOOKBACK_HOURS")

    model_json_temperature: float = Field(default=0.2, alias="MODEL_JSON_TEMPERATURE")
    model_text_temperature: float = Field(default=0.4, alias="MODEL_TEXT_TEMPERATURE")

    github_token: str | None = Field(default=None, alias="GITHUB_TOKEN")

    novelty_new_threshold: float = 0.75
    novelty_duplicate_threshold: float = 0.90
    novelty_ambiguous_low_confidence: float = 0.60

    # Signal score bands — used by source_intelligence.scoring to pick a
    # grounded PM action label: Read / Skim / File Away / Ignore. Only Read and
    # Skim are delivered to Telegram; File Away is stored but not sent; Ignore
    # is not persisted at all (see signalos.workflows.pipeline._build_digest).
    signal_score_thresholds: dict[str, int] = {
        "read": 85,
        "skim": 50,
        "file_away": 30,
    }

    model_routing: dict[str, str] = {
        "embedding": "text-embedding-3-small",
        "novelty_agent": "gpt-4o-mini",
        "impact_agent": "gpt-4o",
        "feedback_agent": "gpt-4o-mini",
        "rca_agent": "gpt-4o",
        "repair_agent": "gpt-4o",
    }

    def source_configs(self) -> list[dict[str, Any]]:
        if not SOURCE_YAML.exists():
            return []
        data = yaml.safe_load(SOURCE_YAML.read_text(encoding="utf-8")) or {}
        return data.get("sources", [])


settings = Settings()
