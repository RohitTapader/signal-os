
# PRD — Signal

## Overview
Signal is a daily AI-industry intelligence platform that ingests high-quality trusted sources, detects what is genuinely new, computes a Signal Score, explains why it matters to senior product leaders, and delivers a curated executive digest via Telegram and a web dashboard.

## Problem
AI professionals are overwhelmed by duplicated announcements, weak summaries, noisy feeds, and ungrounded opinions. They need a trustworthy way to identify signal, not just consume more information.

## Users
Primary:
- AI Product Managers
- Technical Product Managers
- AI Engineers
- Founders / Strategy leads

## Core jobs to be done
- See what changed today
- Know whether it is actually new
- Understand why it matters
- Decide whether to read now or later
- Drill into the source evidence
- Report issues and have the system improve safely

## Scope (V1)
- Trusted-source ingestion
- Content normalization
- Embeddings and novelty detection
- Executive intelligence analysis
- Signal scoring and recommendation
- Digest rendering as Telegram-friendly slides
- Telegram delivery and feedback
- RCA and bounded repair proposals
- Dashboard archive
- Offline evaluation

## Non-goals
- Open web search
- Automatic code deployment
- Social media as a primary source
- Learning cards / spaced repetition
- General-purpose chatbot behavior

## Success metrics
- Novelty precision
- Duplicate suppression rate
- Groundedness of executive intelligence
- Signal score ranking usefulness
- Telegram delivery success
- User feedback rate
- Cost per digest
- Latency per digest

## Guardrails
- No auto-deploys
- No destructive writes without approval
- Strict schemas for all model outputs
- Source allowlist
- Cost caps and retry caps
- Auditable logs for every stage

## Release criteria
Launch only after:
- offline novelty benchmark passes
- executive intelligence summaries are grounded
- signal score ordering is sensible
- Telegram delivery is stable
- repair proposals require approval
- cost stays under budget
