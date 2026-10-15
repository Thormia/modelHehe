"""API FastAPI cho chatbot.

Chạy:  uvicorn backend.api:app --host 0.0.0.0 --port 8000   (từ thư mục Hybrid-database-main)
Giao diện chat thử: http://localhost:8000/
"""
import os
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.pipeline import build_default_pipeline  # noqa: E402

PIPELINE = {}


@asynccontextmanager
async def lifespan(app):
    PIPELINE["p"] = build_default_pipeline()
    yield


app = FastAPI(title="Chatbot tâm lý - thực dưỡng", lifespan=lifespan)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


@app.post("/chat")
async def chat(body: ChatIn):
    sid = body.session_id or uuid.uuid4().hex
    return await run_in_threadpool(PIPELINE["p"].handle, sid, body.message.strip())


@app.get("/session/{session_id}")
def get_session(session_id: str):
    return PIPELINE["p"].store.get(session_id)


@app.delete("/session/{session_id}")
def delete_session(session_id: str):
    PIPELINE["p"].store.delete(session_id)
    return {"deleted": session_id}


@app.get("/health")
def health():
    if "p" not in PIPELINE:
        raise HTTPException(503, "pipeline chưa sẵn sàng")
    return {"status": "ok"}


@app.get("/")
def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))
