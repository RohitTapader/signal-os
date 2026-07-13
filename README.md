
# Signal

Signal is a daily AI-industry intelligence platform with:
- trusted-source ingestion
- novelty filtering
- executive intelligence analysis
- signal scoring and recommendation
- Telegram delivery
- feedback-driven repair proposals
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
| 4. Workflows | `signalos/workflows/` | Daily pipeline, Telegram delivery, slide rendering |

**Source tiers:**
- **Primary** — Official vendor signals (OpenAI, Google AI, Azure, Hugging Face, NVIDIA, SDK changelogs) + trusted media/community (MIT TR, Latent Space, AI News)
- **Secondary** — arXiv research for corroboration depth

**Source categories:** `official`, `research`, `community`, `media`, `open_source`

## Folder map

- `api/` — FastAPI entrypoint and HTTP routes
- `signalos/source_intelligence/` — source registry, scoring breakdown, cross-source clustering
- `signalos/ingestion/` — RSS / GitHub / arXiv fetch adapters
- `signalos/agents/` — novelty, impact, feedback, repair agents
- `signalos/workflows/` — pipeline orchestration, Telegram, slides
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
7. Executive intelligence skill explains what changed and why it matters
8. Signal score ranks what ships
9. Slides are rendered
10. Telegram receives the digest
11. Telegram feedback is routed back into the system
12. Safe config updates can be applied
13. Code repairs are stored for review only

## Production notes

- Use Postgres in production.
- Keep source feeds in `signalos/config/sources.yaml`.
- Telegram buttons are the control plane for feedback and approval.
