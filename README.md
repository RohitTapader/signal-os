
# Signal

Signal is a decision-support system for AI Product Managers — not a news summarizer. Every
day it filters trusted sources down to what's genuinely worth a PM's attention, and frames
each item as a decision briefing (what changed, why it matters to a PM, who should care, what
decision it informs) with a grounded action label, not a vague "read later." See
`docs/ADR/0006-pm-decision-support-not-research-digest.md` for the full rationale.

Signal ships with:
- trusted-source ingestion
- novelty filtering
- PM decision-intelligence synthesis (executive analysis framed as a decision, not a summary)
- 7-factor PM-relevance signal scoring and a grounded recommendation label (Read / Skim /
  File Away / Ignore) — only Read and Skim reach Telegram; File Away is archived, not sent;
  Ignore is not stored
- Telegram delivery as text decision briefings
- feedback-driven, bounded preference adaptation and repair proposals (internal reliability
  tooling, not a customer-facing feature)
- offline evaluation

## What to install

1. Python 3.12
2. Git
3. Cursor
4. uv (recommended)
5. Vercel CLI (optional but useful)
6. Telegram bot token from BotFather
7. OpenAI API key
8. PostgreSQL for production (SQLite is fine locally)

## Local setup

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and `signalos/config/sources.yaml`.

### Optional: evaluation/observability tooling

Not used by the running app — only needed if you're building out offline eval or tracing
(see `docs/EVALUATION.md`). Kept out of the base install to avoid bloating the Vercel
production build.

```bash
uv pip install -r requirements-eval.txt
# or: uv pip install -e ".[eval]"
```

Includes `arize-phoenix` (`phoenix serve` starts its local tracing UI), `arize-phoenix-evals`,
`arize-phoenix-client`, and `ragas`.

## Run locally

```bash
uvicorn api.app:app --reload --port 8000
```

Open:
- http://localhost:8000

## Vercel deployment

1. Push to GitHub
2. Import repo into Vercel
3. Set environment variables in Vercel
4. Add a Telegram webhook to:
   - `https://<your-domain>/api/telegram-webhook`
5. Let Vercel Cron hit:
   - `GET /api/daily-digest`

## Important notes

- Use a managed Postgres database in production.
- SQLite is fine for local development only.
- The system does not auto-deploy code changes.
- Repair proposals are stored for human approval.

## Architecture (interview-friendly)

Signal is a **4-layer AI intelligence system** for Product Managers:

| Layer | Package | What it does |
|-------|---------|--------------|
| 1. Source Intelligence | `signalos/source_intelligence/` | Curated source catalog, authority scores, cross-source clustering, transparent signal scoring |
| 2. Ingestion | `signalos/ingestion/` | RSS, GitHub, arXiv adapters that fetch from the catalog |
| 3. Agents | `signalos/agents/` | LLM skills — novelty detection, impact analysis, feedback |
| 4. Workflows | `signalos/workflows/` | Daily pipeline, deterministic PM-relevance scoring, Telegram delivery |

**Source tiers:**
- **Primary** — Official vendor signals (OpenAI, Google AI, Azure, Hugging Face, NVIDIA, SDK changelogs) + trusted media/community (MIT TR, Latent Space, AI News)
- **Secondary** — arXiv research for corroboration depth

**Source categories:** `official`, `research`, `community`, `media`, `open_source`

## Folder map

- `api/` — FastAPI entrypoint and HTTP routes
- `signalos/source_intelligence/` — source registry, scoring breakdown, cross-source clustering
- `signalos/ingestion/` — RSS / GitHub / arXiv fetch adapters
- `signalos/agents/` — novelty, impact, feedback, repair agents
- `signalos/workflows/` — pipeline orchestration, Telegram delivery
- `signalos/core/` — config, DB, models, LLM routing
- `signalos/config/sources.yaml` — curated AI PM source catalog
- `skills/` — OpenClaw-style markdown skills
- `docs/` — PRD, architecture, ADRs
- `public/` — dashboard files
- `tests/` — lightweight tests

## Step-by-step build order

See `docs/IMPLEMENTATION_PLAN.md` for the exact file order to paste into Cursor.

## Daily flow

1. Vercel Cron calls `/api/daily-digest`
2. Source ingestion fetches trusted feeds
3. Validation filters bad items
4. Normalization cleans content
5. Embeddings are created
6. Novelty skill decides NEW / DUPLICATE / UPDATE
7. Executive intelligence skill answers what changed, why it matters to a PM, who should
   care, and what decision it informs
8. Deterministic 7-factor signal score ranks what ships, and maps to a grounded PM action
   label (Read Now / Evaluate / Compare Against Current Approach / Watch / Skim / File Away / Ignore)
9. Telegram receives the decision briefing as text
10. Telegram feedback is routed back into the system
11. Safe config/preference updates can be applied
12. Code repairs are stored for review only

## Production notes

- Use Postgres in production.
- Keep source feeds in `signalos/config/sources.yaml`.
- Telegram buttons are the control plane for feedback and approval.
