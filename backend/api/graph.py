# backend/api/graph.py
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_user
from backend.db.database import get_db
from backend.db.models import Document, User
from backend.services.kg_service import get_graph_data

router = APIRouter(prefix="/graph", tags=["graph"])
log = logging.getLogger(__name__)


# ── GET /graph/{doc_id} ───────────────────────────────────────────────────────
@router.get("/{doc_id}")
def get_graph(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Returns knowledge graph JSON for react-force-graph.

    Response shape:
        {
            "nodes": [{"id": "...", "label": "...", "size": 1}, ...],
            "links": [{"source": "...", "target": "...", "relation": "..."}, ...]
        }
    """
    # ── ownership check ───────────────────────────────────────────────────────
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == current_user.id,
    ).first()

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    # ── kg not built yet ──────────────────────────────────────────────────────
    if not doc.kg_ready:
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Knowledge graph is still being built. Try again shortly.",
        )

    # ── load + export ─────────────────────────────────────────────────────────
    try:
        graph_data = get_graph_data(doc_id)
        log.info(
            "graph: served %d nodes, %d links for doc %s",
            len(graph_data.get("nodes", [])),
            len(graph_data.get("links", [])),
            doc_id,
        )
        return graph_data

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Graph file missing. Re-upload the document to rebuild.",
        )
    except Exception as exc:
        log.exception("graph: failed to load graph for doc %s", doc_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load graph: {exc}",
        )