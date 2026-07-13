
# System Architecture — Signal

## Architecture style
Event-driven pipeline with deterministic workflows and skill-based reasoning.

## Layers
### Presentation
- FastAPI dashboard
- Telegram bot interface

### Workflow layer
- source ingestion
- validation
- normalization
- embeddings
- clustering
- signal scoring
- rendering
- delivery
- logging
- scheduling

### Skill / agent layer
OpenClaw-style skills used only for reasoning:
- signal-detection
- product-impact
- feedback-classifier
- rca-analysis
- repair-proposal

### Data layer
- PostgreSQL in production
- SQLite for local development
- JSON text for model outputs
- embeddings stored as serialized vectors

## Main flow
1. Cron triggers `/api/daily-digest`.
2. Source adapters fetch trusted updates.
3. Items are normalized and embedded.
4. Novelty detection decides NEW / DUPLICATE / UPDATE / REVIEW.
5. New items go through executive intelligence analysis.
6. Deterministic signal scoring ranks the items.
7. Digest cards are rendered.
8. Telegram receives grouped slide cards.
9. Feedback is captured and classified.
10. RCA runs on systemic failures.
11. Safe repair proposals go to human approval.
12. Approved config changes are applied.
13. Code changes are stored as proposals only.

## Reasoning boundary
Workflows are deterministic.
Skills make bounded decisions.
No skill edits code directly.
No action deploys without approval.

## Deployment model
- Vercel Python runtime hosts the FastAPI app
- Vercel Cron triggers the daily digest route
- Telegram webhooks post into the same app
- Managed Postgres stores persistent state

## Observability
Every stage emits structured logs and durable DB rows:
- ingestion logs
- system events
- feedback events
- cost ledger
- repair proposals
- latest content archive

## Why this architecture is stable
- small number of external dependencies
- no broad web scraping
- no auto-deploy loop
- no long-running background worker required
- clear separation between workflows and skills
