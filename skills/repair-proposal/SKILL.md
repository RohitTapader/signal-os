---
name: repair-proposal
description: Draft a non-destructive repair proposal for human review.
---

# Repair Proposal Skill

You are drafting a repair proposal, not auto-fixing code.

Rules:
- Never suggest destructive autonomous action.
- Never say code should be auto-applied.
- Focus on probable root cause and a safe human-reviewable proposal.
- Output JSON only.

Required schema:
{
  "title": "string",
  "proposal_text": "string",
  "risk_level": "low|medium|high"
}
