from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2] / "skills"


@lru_cache(maxsize=32)
def load_skill(skill_name: str) -> dict[str, str]:
    skill_path = SKILLS_ROOT / skill_name / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")
    raw = skill_path.read_text(encoding="utf-8")
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        frontmatter = parts[1].strip() if len(parts) > 1 else ""
        body = parts[2].strip() if len(parts) > 2 else raw
    else:
        frontmatter = ""
        body = raw
    return {"name": skill_name, "frontmatter": frontmatter, "body": body, "path": str(skill_path)}
