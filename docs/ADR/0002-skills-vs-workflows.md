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

Within "executive intelligence generation," the skill is bounded further: it synthesizes what
changed, why it matters to a PM, who should care, what decision it informs, and three
independent confidence sub-scores — it does not choose the recommendation label. Label
selection is a deterministic function of the score band plus whether a concrete decision is
grounded (`signalos/source_intelligence/scoring.py::recommendation_for_score`), so the same
stored inputs always produce the same label regardless of LLM variance. See ADR 0006 for why
this distinction (decision support vs. research summarization) matters for the product.

## Consequences
Positive:
- easier debugging
- clearer tests
- lower token costs
- easier governance
- deterministic signal scoring and ranking
- recommendation labels are reproducible from stored data without re-calling an LLM

Tradeoffs:
- skill prompts must be maintained carefully
- reasoning capability is bounded by the skill instructions
