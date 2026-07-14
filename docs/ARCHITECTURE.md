
# System Architecture — Signal

## Product framing
Signal is a decision-support system for AI Product Managers, not a research summarizer. That
framing shapes the architecture directly: the deterministic layers exist to keep ranking and
delivery explainable and cheap, and the one LLM-driven step exists specifically to answer four
PM-relevant questions per item (what changed, why it matters to a PM, who should care, what
decision it informs) rather than to write a general-purpose summary. See ADR 0006.

## Architecture style
Event-driven pipeline with deterministic workflows and skill-based reasoning. Deterministic
code owns ingestion, ranking, and delivery; skills are used only where the input is genuinely
ambiguous free text that needs synthesis. See ADR 0002 for why this split exists and what
"ambiguous" means in practice.

## Layers
### Presentation
- FastAPI dashboard
- Telegram bot interface

### Workflow layer (deterministic)
- source ingestion
- validation
- normalization
- embeddings
- clustering (cross-source corroboration / trend momentum)
- signal scoring — the 7-factor PM-relevance score and the recommendation-label mapping are
  plain code, not LLM output (`signalos/source_intelligence/scoring.py`)
- Telegram message rendering
- delivery
- logging
- scheduling

### Skill / agent layer (bounded reasoning only)
OpenClaw-style skills used only for reasoning that requires reading free text and making a
judgment call — never for anything ranking- or delivery-related:
- signal-detection — ambiguous novelty calls (is this genuinely new vs. a near-duplicate)
- product-impact — executive synthesis: what changed, why it matters to a PM, who should
  care, what decision it informs, and three independent confidence sub-scores (product /
  business / strategic) that feed the deterministic scorer
- feedback-classifier — free-text user feedback into bounded categories
- rca-analysis — internal reliability tooling, not a customer-facing feature
- repair-proposal — internal reliability tooling, not a customer-facing feature

Notably, **the recommendation label itself is not agent output.** The product-impact skill
estimates confidence sub-scores and states whether a concrete decision/audience is grounded
in the source; `recommendation_for_score()` (deterministic) turns that into one of four PM
action labels — Read, Skim, File Away, Ignore. This keeps ranking auditable and reproducible
independent of LLM variance. Only Read and Skim are delivered to Telegram; File Away is stored
but not sent; Ignore is not persisted at all (see ADR 0006).

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
5. New items go through executive intelligence analysis (product-impact skill) — what
   changed, why it matters to a PM, who should care, what decision it informs, plus
   product/business/strategic confidence sub-scores.
6. Deterministic signal scoring combines novelty, product impact, business impact, strategic
   relevance, source authority, trend momentum, and evidence strength into one explainable score.
7. A deterministic mapping turns the score into one of four PM action labels (Read / Skim /
   File Away / Ignore) — never a raw number, never LLM-chosen.
8. Read and Skim items are composed as Telegram-native text; File Away is stored only; Ignore
   is dropped without being persisted.
9. Telegram delivers the decision briefing with feedback buttons.
10. Feedback is captured and classified.
11. RCA runs on systemic failures (internal reliability only).
12. Safe repair proposals go to human approval.
13. Approved config changes are applied.
14. Code changes are stored as proposals only.

## Reasoning boundary
Workflows are deterministic.
Skills make bounded decisions — synthesis and confidence estimation from free text, never
ranking or label decisions.
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
- ranking and recommendation labels are reproducible from stored data without re-calling an LLM
