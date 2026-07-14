
# PRD — Signal

## Overview
Signal is a decision-support system for AI Product Managers — not a news summarizer, not a
research digest. Every day it ingests high-quality trusted sources, filters for what is
genuinely new, and asks one question per item: **is this worth an AI PM's attention today,
and if so, what should they do about it?** Items that pass are turned into a decision
briefing — what changed, why it matters to a PM specifically, who should care, and what
decision it informs — delivered via Telegram with a grounded, actionable recommendation.

## Problem
AI professionals are overwhelmed by duplicated announcements, weak summaries, noisy feeds,
and ungrounded opinions. Existing digests describe *what happened*; they don't tell a PM
*what to do about it*. Signal exists to close that gap: surface only what's genuinely
relevant to PM decision-making, and frame it as a decision, not a headline.

## Users
Primary:
- AI Product Managers
- Technical Product Managers
- AI Engineers
- Founders / Strategy leads

## Core jobs to be done
- See what changed today
- Know whether it is actually new
- Understand why it matters *to an AI PM specifically* — not just "why it's interesting"
- Know who should care and what decision it informs
- Decide what to do about it: read now, evaluate, compare against current approach, watch,
  skim, file away, or ignore — never a vague "read later"
- Drill into the source evidence
- Report issues and have the system improve safely

## Product positioning (enforced everywhere — code, prompts, docs)
- Signal is not a news summarizer.
- Signal is an AI PM intelligence and decision-support system.
- Signal helps AI PMs decide what is worth attention today, and why.
- The product surfaces only signals genuinely relevant to PM decision-making — an item that
  is merely research-interesting with no product, business, or strategic angle should rank
  low and read as low-priority, not be dressed up with a manufactured "roadmap implication."

## Scope (V1)
- Trusted-source ingestion
- Content normalization
- Embeddings and novelty detection
- Executive intelligence analysis framed as PM decision support (what changed / why it
  matters to a PM / who should care / what decision it informs / confidence and evidence)
- PM-relevant signal scoring and a grounded recommendation label
- Telegram-delivered decision briefings
- Telegram delivery and feedback
- Bounded config-level repair proposals for the system's own operation (not a customer-facing
  feature — an internal reliability mechanism; see ADR 0004)
- Dashboard archive
- Offline evaluation

## Non-goals
- Open web search
- Automatic code deployment
- Social media as a primary source
- Learning cards / spaced repetition
- General-purpose chatbot behavior
- RCA / bug-fixing as a customer-facing product feature (it exists only as internal
  governance for the system's own reliability — see ADR 0004)

## Success metrics
- PM relevance of what ships (not just novelty/summarization quality)
- Actionability of the recommendation label
- Groundedness and evidence quality of executive intelligence
- Novelty precision and duplicate suppression rate
- Signal score ranking usefulness against PM judgment
- Telegram delivery success
- User feedback rate
- Cost per digest
- Latency per digest

See `docs/EVALUATION.md` for the full PM-focused metric set and launch gates.

## Guardrails
- No auto-deploys
- No destructive writes without approval
- Strict schemas for all model outputs
- Source allowlist
- Cost caps and retry caps
- Auditable logs for every stage
- Recommendation labels are computed deterministically from score + grounded signals, never
  chosen by the LLM directly (see ADR 0002 and ADR 0006)

## Release criteria
Launch only after:
- offline novelty benchmark passes
- executive intelligence is grounded, evidence-backed, and free of manufactured roadmap/metric claims
- signal score ordering reflects genuine PM relevance, not just novelty
- recommendation labels are meaningfully differentiated (a PM reading "Read Now" vs "Watch"
  should be able to tell why without reading the score breakdown)
- Telegram delivery is stable
- repair proposals require approval
- cost stays under budget
