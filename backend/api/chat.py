"""
backend/api/chat.py

Routes:
    POST /chat/query — RAG query with SSE streaming response

The response is a Server-Sent Events stream. Each event is either:
    data: {"type": "token",     "content": "..."}
    data: {"type": "citation",  "chunks": [...]}
    data: {"type": "done"}
    data: {"type": "error",     "detail": "..."}
"""

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, Document
from backend.auth.middleware import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query:       str
    doc_ids:     list[int] = []   # empty = search across all user docs
    use_graph:   bool      = True  # include knowledge graph context
    stream:      bool      = True


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------
def _event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


async def _stream_response(
    query:        str,
    doc_ids:      list[int],
    use_graph:    bool,
    user_id:      int,
) -> AsyncGenerator[str, None]:
    """Core streaming generator — calls query_service, yields SSE events."""
    try:
        from backend.services.query_service import stream_query

        citations_sent = False
        async for event in stream_query(
            query=query,
            doc_ids=doc_ids,
            user_id=user_id,
            use_graph=use_graph,
        ):
            event_type = event.get("type")

            if event_type == "citation" and not citations_sent:
                yield _event(event)
                citations_sent = True

            elif event_type == "token":
                yield _event(event)

            elif event_type == "done":
                yield _event({"type": "done"})
                return

            elif event_type == "error":
                yield _event(event)
                return

    except Exception as e:
        yield _event({"type": "error", "detail": str(e)})


# ---------------------------------------------------------------------------
# POST /chat/query
# ---------------------------------------------------------------------------
@router.post("/query")
async def query(
    body:         QueryRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # validate doc_ids belong to current user
    if body.doc_ids:
        owned = {
            d.id for d in db.query(Document.id)
            .filter(
                Document.user_id == current_user.id,
                Document.id.in_(body.doc_ids),
                Document.status == "ready",
            ).all()
        }
        invalid = set(body.doc_ids) - owned
        if invalid:
            raise HTTPException(
                status_code=404,
                detail=f"Documents not found or not ready: {list(invalid)}",
            )

    return StreamingResponse(
        _stream_response(
            query=body.query,
            doc_ids=body.doc_ids,
            use_graph=body.use_graph,
            user_id=current_user.id,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # disables nginx buffering
        },
    )