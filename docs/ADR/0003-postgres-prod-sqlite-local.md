# ADR 0003 — Use Postgres in production, SQLite locally

## Status
Accepted

## Context
The system needs durable state for:
- content archive
- system events
- feedback
- repair proposals
- cost ledger

## Decision
Use SQLite for local development and managed Postgres in production.

## Consequences
Positive:
- easy local setup
- persistent production state
- simple schema migrations initially

Tradeoffs:
- production DB must be configured before rollout
- SQLite should not be used for production persistence
