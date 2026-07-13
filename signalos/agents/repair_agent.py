from __future__ import annotations

import json

from signalos.core.llm import call_model
from signalos.core.models import RepairProposal


def draft_repair_proposal(error_text: str, rca_text: str) -> RepairProposal:
    prompt = f"""
Draft a non-destructive repair proposal for human review.
Do not propose autonomous code deployment.

Return JSON only:
{{
  "title": "string",
  "proposal_text": "string",
  "risk_level": "low|medium|high"
}}

Error:
{error_text}

RCA:
{rca_text}
"""
    raw, usage = call_model(
        "repair_agent",
        prompt,
        skill_name="repair-proposal",
        json_mode=True,
    )
    data = json.loads(raw)
    return RepairProposal(**data)
