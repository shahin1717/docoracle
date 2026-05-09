# backend/api/chat.py
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_user
from backend.db.database import get_db
from backend.db.models import Document, User
from backend.services.query_service import get_source_chunks, stream_answer

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger(__name__)


# ── request schema ────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query:   str
    doc_ids: list[str]


# ── POST /chat/query ──────────────────────────────────────────────────────────
@router.post("/query")
async def chat_query(
    body: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    SSE streaming endpoint.

    Event types:
        data: {"type": "token",   "content": "<token>"}
        data: {"type": "sources", "content": [...chunks...]}
        data: {"type": "done"}
        data: {"type": "error",   "content": "<message>"}
    """
    if not body.query.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Query cannot be empty.",
        )
    if not body.doc_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Select at least one document.",
        )

    # verify ownership + readiness
    for doc_id in body.doc_ids:
        doc = db.query(Document).filter(
            Document.id == doc_id,
            Document.user_id == current_user.id,
        ).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
        if doc.status != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"Document '{doc.filename}' is still being processed.",
            )

    # pass user's chosen model into the pipeline
    model = current_user.preferred_model  # None → query_service falls back to settings

    return StreamingResponse(
        _event_stream(body.query, body.doc_ids, current_user.id, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── SSE generator ─────────────────────────────────────────────────────────────
async def _event_stream(
    query: str,
    doc_ids: list[str],
    user_id: str,
    model: str | None,
) -> AsyncGenerator[str, None]:
    collected_tokens = []
    chunk_ids_used   = []

    try:
        for token in stream_answer(query, doc_ids, user_id, model=model):
            if isinstance(token, dict) and token.get("chunk_ids"):
                chunk_ids_used = token["chunk_ids"]
                continue
            collected_tokens.append(token)
            yield _sse({"type": "token", "content": token})

        if chunk_ids_used:
            sources = get_source_chunks(chunk_ids_used)
            yield _sse({"type": "sources", "content": sources})

        yield _sse({"type": "done"})

    except Exception as exc:
        log.exception("chat: stream error for user %s", user_id)
        yield _sse({"type": "error", "content": str(exc)})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"