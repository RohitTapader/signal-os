# ADR 0001 — Use FastAPI on Vercel Python Runtime

## Status
Accepted

## Context
The system needs HTTP routes for:
- daily cron execution
- Telegram webhook handling
- dashboard access
- lightweight archive APIs

## Decision
Use a FastAPI ASGI app as the Vercel Python entrypoint.

## Consequences
Positive:
- one deployable runtime
- webhook-friendly
- cron-friendly
- simple local development

Tradeoffs:
- production persistence requires managed Postgres
- long-running jobs are not a fit; digest execution must stay bounded
