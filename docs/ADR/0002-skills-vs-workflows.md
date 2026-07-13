# ADR 0002 — Use Skills for reasoning, workflows for deterministic code

## Status
Accepted

## Context
The product needs agentic reasoning without turning every step into an agent.

## Decision
Use OpenClaw-style markdown skills only for:
- novelty detection
- executive intelligence generation
- feedback classification
- RCA
- repair proposals

Keep ingestion, normalization, clustering, signal scoring, rendering, delivery, and scheduling deterministic.

## Consequences
Positive:
- easier debugging
- clearer tests
- lower token costs
- easier governance
- deterministic signal scoring and ranking

Tradeoffs:
- skill prompts must be maintained carefully
- reasoning capability is bounded by the skill instructions
