# backend/api/chat.py
import json
import logging
from typing import AsyncGenerator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_user
from backend.db.database import get_db, SessionLocal
from backend.db.models import Document, User, ChatSession, ChatMessage
from backend.services.query_service import get_source_chunks, stream_answer, generate_chat_title

router = APIRouter(prefix="/chat", tags=["chat"])
log = logging.getLogger(__name__)


# ── request schema ────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    query:   str
    session_id: str | None = None


# ── GET /chat/sessions ────────────────────────────────────────────────────────
@router.get("/sessions")
def get_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions = db.query(ChatSession).filter(
        ChatSession.user_id == current_user.id
    ).order_by(ChatSession.updated_at.desc()).all()
    
    return [{"id": s.id, "title": s.title, "updated_at": s.updated_at} for s in sessions]


# ── POST /chat/sessions ───────────────────────────────────────────────────────
@router.post("/sessions")
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_session = ChatSession(user_id=current_user.id, title="New Chat")
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {"id": new_session.id, "title": new_session.title}


# ── GET /chat/sessions/{session_id} ───────────────────────────────────────────
@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    return {
        "id": session.id,
        "title": session.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at
            }
            for m in messages
        ]
    }


# ── DELETE /chat/sessions/{session_id} ────────────────────────────────────────
@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return {"status": "ok"}


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
        data: {"type": "session", "content": "<session_id>"}
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

    # Handle chat session first
    session_id = body.session_id
    if not session_id:
        title = generate_chat_title(body.query, model=current_user.preferred_model)
        new_session = ChatSession(user_id=current_user.id, title=title)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        session_id = new_session.id
    else:
        existing = db.query(ChatSession).filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        if not existing:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        
        existing.updated_at = datetime.utcnow()
        # If it's a default title, try to generate a better one using document context
        if existing.title == "New Chat" or existing.title.startswith("Chat: "):
            session_docs = db.query(Document).filter(Document.session_id == session_id).all()
            doc_titles = [d.filename for d in session_docs]
            existing.title = generate_chat_title(body.query, doc_titles=doc_titles, model=current_user.preferred_model)
        db.commit()

    # Automatically fetch doc_ids for this session
    session_docs = db.query(Document).filter(
        Document.session_id == session_id,
        Document.user_id == current_user.id
    ).all()
    
    if not session_docs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No documents uploaded to this chat session.",
        )
        
    doc_ids = [d.id for d in session_docs]

    # verify readiness
    for doc in session_docs:
        if doc.status != "ready":
            raise HTTPException(
                status_code=409,
                detail=f"Document '{doc.filename}' is still being processed.",
            )

    # Save user query to DB
    user_msg = ChatMessage(session_id=session_id, role="user", content=body.query)
    db.add(user_msg)
    db.commit()

    # Fetch past messages (excluding the one we just added to pass as history before the new prompt)
    # Wait, if we fetch all, we get the current query too. Let's fetch all except the one we just added?
    # Or just pass the past messages up to now.
    past_messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id,
        ChatMessage.id != user_msg.id
    ).order_by(ChatMessage.created_at.asc()).all()
    
    chat_history = [{"role": m.role, "content": m.content} for m in past_messages]

    # pass user's chosen model into the pipeline
    model = current_user.preferred_model  # None → query_service falls back to settings

    return StreamingResponse(
        _event_stream(body.query, doc_ids, current_user.id, model, session_id, chat_history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── SSE generator ─────────────────────────────────────────────────────────────
async def _event_stream(
    query: str,
    doc_ids: list[str],
    user_id: str,
    model: str | None,
    session_id: str,
    chat_history: list[dict],
) -> AsyncGenerator[str, None]:
    collected_tokens = []
    chunk_ids_used   = []

    # Send the session ID first
    yield _sse({"type": "session", "content": session_id})

    try:
        for token in stream_answer(query, doc_ids, user_id, model=model, chat_history=chat_history):
            if isinstance(token, dict) and token.get("chunk_ids"):
                chunk_ids_used = token["chunk_ids"]
                continue
            collected_tokens.append(token)
            yield _sse({"type": "token", "content": token})

        if chunk_ids_used:
            sources = get_source_chunks(chunk_ids_used)
            yield _sse({"type": "sources", "content": sources})

        yield _sse({"type": "done"})

        # Save assistant message
        assistant_content = "".join(collected_tokens)
        _save_assistant_message(session_id, assistant_content)

    except Exception as exc:
        log.exception("chat: stream error for user %s", user_id)
        yield _sse({"type": "error", "content": str(exc)})


def _save_assistant_message(session_id: str, content: str):
    db = SessionLocal()
    try:
        msg = ChatMessage(session_id=session_id, role="assistant", content=content)
        db.add(msg)
        db.commit()
    except Exception as e:
        log.error(f"Failed to save assistant message: {e}")
    finally:
        db.close()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"