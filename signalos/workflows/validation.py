from __future__ import annotations

from dataclasses import dataclass

from signalos.core.models import SourceItem


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""


def validate_item(item: SourceItem) -> ValidationResult:
    if not item.title or len(item.title.strip()) < 4:
        return ValidationResult(False, "title too short")
    if not str(item.url).startswith("http"):
        return ValidationResult(False, "invalid url")
    combined = f"{item.title} {item.raw_text}".strip()
    if len(combined) < 50:
        return ValidationResult(False, "content too short")
    return ValidationResult(True, "ok")
