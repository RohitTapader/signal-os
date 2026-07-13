from __future__ import annotations

import json

from signalos.core.llm import call_model
from signalos.core.models import RCAResult


def analyze_root_cause(error_text: str, context_text: str) -> RCAResult:
    prompt = f"""
Analyze the failure and return JSON only.

Required schema:
{{
  "title": "string",
  "likely_cause": "string",
  "affected_component": "string",
  "risk_level": "low|medium|high",
  "suggested_fix": "string",
  "rollback_plan": "string",
  "confidence": 0-1
}}

Error:
{error_text}

Context:
{context_text}
"""
    raw, usage = call_model(
        "rca_agent",
        prompt,
        skill_name="rca-analysis",
        json_mode=True,
    )
    data = json.loads(raw)
    return RCAResult(**data)
