from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from signalos.core.config import settings
from signalos.core.db import ContentItem, FeedbackEvent, RepairProposalRow, SessionLocal, init_db
from signalos.core.logging import log_json
from signalos.source_intelligence.registry import get_registry
from signalos.workflows.event_router import route_telegram_update
from signalos.workflows.telegram import send_message
from signalos.workflows.pipeline import fetch_all_sources, generate_digest_from_items, run_and_send_digest

app = FastAPI(title="Signal", version="0.1.0")
init_db()

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"


@app.get("/", include_in_schema=False)
def home():
    index = PUBLIC / "index.html"
    if index.exists():
        return FileResponse(index)
    return HTMLResponse("<h1>Signal</h1><p>Dashboard not found.</p>")


@app.get("/app.js", include_in_schema=False)
def app_js():
    js = PUBLIC / "app.js"
    if js.exists():
        return FileResponse(js)
    return PlainTextResponse("console.log('Signal dashboard missing');", media_type="application/javascript")


@app.get("/api/sources")
def sources_catalog():
    return get_registry().to_public_dict()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/daily-digest")
def daily_digest():
    summary = run_and_send_digest()
    return JSONResponse(summary)


@app.get("/api/latest")
def latest():
    db = SessionLocal()
    try:
        rows = db.query(ContentItem).order_by(ContentItem.id.desc()).limit(10).all()
        items = []
        for r in rows:
            impact = json.loads(r.impact_json) if r.impact_json else None
            items.append({
                "id": r.id,
                "title": r.title,
                "url": r.url,
                "source_id": r.source_id,
                "source_name": r.source_name,
                "source_display_name": r.source_display_name,
                "source_category": r.source_category,
                "source_tier": r.source_tier,
                "authority_score": r.authority_score,
                "novelty_verdict": r.novelty_verdict,
                "novelty_confidence": r.novelty_confidence,
                "impact": impact,
                "cluster_id": r.cluster_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })
        return {"items": items}
    finally:
        db.close()


@app.get("/api/repairs")
def repairs():
    db = SessionLocal()
    try:
        rows = db.query(RepairProposalRow).order_by(RepairProposalRow.id.desc()).limit(50).all()
        return {
            "items": [
                {
                    "id": r.id,
                    "title": r.title,
                    "proposal_text": r.proposal_text,
                    "risk_level": r.risk_level,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }
    finally:
        db.close()


@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request):
    update = await request.json()
    route_telegram_update(update)
    return {"ok": True}


@app.post("/api/debug/regenerate")
def debug_regenerate():
    items = fetch_all_sources()
    summary = generate_digest_from_items(items, run_id="manual_regenerate")
    return JSONResponse(summary)


@app.post("/api/debug/feedback")
async def debug_feedback(request: Request):
    payload = await request.json()
    text = payload.get("text", "")
    if not text:
        return JSONResponse({"error": "missing text"}, status_code=400)
    db = SessionLocal()
    try:
        db.add(FeedbackEvent(event_type="debug", text=text, payload_json=json.dumps(payload)))
        db.commit()
    finally:
        db.close()
    log_json("debug_feedback", text=text)
    return {"ok": True}


@app.post("/api/debug/test-telegram")
def debug_test_telegram():
    try:
        send_message(settings.telegram_chat_id, "✅ Signal test message: Telegram integration is working.")
        return {"ok": True, "message": "sent"}
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)
