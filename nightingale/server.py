"""Nightingale web server — local clinical documentation interface."""

import os
import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from nightingale.engine import NightingaleEngine

app = FastAPI(title="Nightingale", docs_url=None, redoc_url=None)

# Global engine instance
_engine: NightingaleEngine | None = None


def get_engine() -> NightingaleEngine:
    global _engine
    if _engine is None:
        _engine = NightingaleEngine()
    return _engine


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Main interface."""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    with open(html_path) as f:
        return f.read()


# ---------- API ----------

@app.post("/api/start-shift")
async def start_shift():
    engine = get_engine()
    engine.start_shift()
    return {"status": "ok", "message": "Shift started"}


@app.post("/api/document")
async def document(request: Request):
    body = await request.json()
    text = body.get("text", "")
    fmt = body.get("format", "assessment")
    engine = get_engine()

    def stream():
        for token in engine.document(text, format=fmt):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/update")
async def update_patient(request: Request):
    body = await request.json()
    text = body.get("text", "")
    engine = get_engine()

    def stream():
        for token in engine.update_patient(text):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.post("/api/ask")
async def ask_question(request: Request):
    body = await request.json()
    text = body.get("text", "")
    engine = get_engine()

    def stream():
        for token in engine.ask(text):
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/patients")
async def get_patients():
    engine = get_engine()
    return engine.get_patients()


@app.post("/api/save-shift")
async def save_shift():
    engine = get_engine()
    path = engine.save_shift()
    return {"status": "ok", "path": path}


@app.post("/api/load-shift")
async def load_shift(request: Request):
    body = await request.json()
    path = body.get("path", "")
    engine = get_engine()
    engine.load_shift(path)
    return {"status": "ok", "patients": engine.get_patients()}


@app.post("/api/end-shift")
async def end_shift():
    engine = get_engine()
    engine.end_shift()
    return {"status": "ok"}


@app.get("/api/shifts")
async def list_shifts():
    """List saved shift files for handoff loading."""
    shifts_dir = os.path.expanduser("~/.nightingale/shifts")
    if not os.path.exists(shifts_dir):
        return []

    shifts = []
    for f in sorted(Path(shifts_dir).glob("*.npz"), reverse=True):
        meta_path = str(f).replace('.npz', '_shift.json')
        meta = {}
        if os.path.exists(meta_path):
            with open(meta_path) as mf:
                meta = json.load(mf)
        shifts.append({
            'path': str(f),
            'filename': f.name,
            'saved_at': meta.get('saved_at', ''),
            'patients': len(meta.get('patients', {})),
        })
    return shifts
