"""
backend/api/graph.py

Routes:
    GET /graph/{doc_id}          — full KG for react-force-graph
    GET /graph/{doc_id}/subgraph — subgraph around a query term
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User, Document
from backend.auth.middleware import get_current_user

router = APIRouter(prefix="/graph", tags=["graph"])


def _get_ready_doc(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id      == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"Document is not ready (status: {doc.status})")
    if not doc.has_graph:
        raise HTTPException(status_code=404, detail="No knowledge graph available for this document")
    return doc


# ---------------------------------------------------------------------------
# GET /graph/{doc_id}
# ---------------------------------------------------------------------------
@router.get("/{doc_id}")
def get_graph(
    doc_id: int,
    db:     Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the full knowledge graph in react-force-graph JSON format."""
    doc = _get_ready_doc(doc_id, current_user, db)

    from backend.services.kg_service import get_graph_data
    return get_graph_data(doc_id)


# ---------------------------------------------------------------------------
# GET /graph/{doc_id}/subgraph
# ---------------------------------------------------------------------------
@router.get("/{doc_id}/subgraph")
def get_subgraph(
    doc_id: int,
    query:  str     = Query(..., description="Term to build subgraph around"),
    depth:  int     = Query(2,  description="Hop depth", ge=1, le=4),
    db:     Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a subgraph centred on nodes matching the query term."""
    doc = _get_ready_doc(doc_id, current_user, db)

    from backend.services.kg_service import get_subgraph_data
    return get_subgraph_data(doc_id, query, depth)