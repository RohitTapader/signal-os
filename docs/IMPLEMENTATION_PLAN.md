
# Implementation Plan (Cursor)

## 0. Install first
- Python 3.12
- Cursor
- Git
- uv
- Telegram bot token
- OpenAI API key
- SQLite for local development (no install needed)
- PostgreSQL URL for production

## 1. Create the repo
In Cursor:
1. Open an empty folder named `signalos`
2. Create the folder structure from the scaffold
3. Paste files in the order below

## 2. Paste files in this order

### Foundation
1. `pyproject.toml`
2. `requirements.txt`
3. `.env.example`
4. `vercel.json`
5. `README.md`

### Core
6. `signalos/core/config.py`
7. `signalos/core/db.py`
8. `signalos/core/models.py`
9. `signalos/core/logging.py`
10. `signalos/core/skill_registry.py`
11. `signalos/core/llm.py`

### Sources
12. `signalos/sources/rss_source.py`
13. `signalos/sources/arxiv_source.py`
14. `signalos/sources/github_source.py`

### Workflows
15. `signalos/workflows/validation.py`
16. `signalos/workflows/normalize.py`
17. `signalos/workflows/embeddings.py`
18. `signalos/workflows/scoring.py`
19. `signalos/workflows/clustering.py`
20. `signalos/workflows/render.py`
21. `signalos/workflows/telegram.py`
22. `signalos/workflows/repair_policy.py`
23. `signalos/workflows/event_router.py`
24. `signalos/workflows/pipeline.py`

### Agents / skills
25. `signalos/agents/novelty_agent.py`
26. `signalos/agents/impact_agent.py`
27. `signalos/agents/feedback_agent.py`
28. `signalos/agents/rca_agent.py`
29. `signalos/agents/repair_agent.py`
30. `skills/signal-detection/SKILL.md`
31. `skills/product-impact/SKILL.md`
32. `skills/feedback-classifier/SKILL.md`
33. `skills/rca-analysis/SKILL.md`
34. `skills/repair-proposal/SKILL.md`

### Runtime
35. `api/app.py`
36. `main.py`

### Dashboard / docs / tests
37. `public/index.html`
38. `public/app.js`
39. `docs/PRD.md`
40. `docs/ARCHITECTURE.md`
41. `docs/EVALUATION.md`
42. ADR files in `docs/ADR/`
43. `tests/test_novelty.py`
44. `tests/test_metrics.py`

## 3. Add env vars
Copy `.env.example` to `.env` and fill:
- OPENAI_API_KEY
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- DATABASE_URL
- APP_BASE_URL

## 4. Local run
```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn api.app:app --reload --port 8000
```

## 5. Validate in order
1. Open `http://localhost:8000/api/health`
2. Open `http://localhost:8000/docs`
3. Run `GET /api/daily-digest`
4. Check Telegram delivery
5. Open `http://localhost:8000/` for the dashboard
6. Open `http://localhost:8000/api/latest` to confirm signal scores and executive summaries

## 6. Vercel deploy
- Push to GitHub
- Import into Vercel
- Set env vars
- Deploy

## 7. Telegram
- Set webhook to `https://<your-domain>/api/telegram-webhook`
- Cron hits `GET /api/daily-digest`
