# backend/api/documents.py
import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth.middleware import get_current_user
from backend.config import settings
from backend.db.database import get_db
from backend.db.models import Document, User
from backend.services.ingest_service import run_ingestion
from backend.services.kg_service import build_knowledge_graph

router = APIRouter(prefix="/documents", tags=["documents"])
log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md"}
MAX_FILE_SIZE      = 50 * 1024 * 1024   # 50 MB


# ── response schema ───────────────────────────────────────────────────────────
class DocumentOut(BaseModel):
    id:          str
    filename:    str
    file_type:   str
    file_size:   int
    status:      str
    error_msg:   str | None
    chunk_count: int
    page_count:  int
    kg_ready:    bool

    model_config = {"from_attributes": True}


# ── POST /documents/upload ────────────────────────────────────────────────────
@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ── validate extension ────────────────────────────────────────────────────
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # ── read + size check ─────────────────────────────────────────────────────
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 50 MB limit.",
        )

    # ── save to disk ──────────────────────────────────────────────────────────
    user_upload_dir = Path(settings.uploads_dir) / current_user.id
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    dest = user_upload_dir / file.filename
    # avoid collisions — append a counter if file already exists
    counter = 1
    while dest.exists():
        dest = user_upload_dir / f"{Path(file.filename).stem}_{counter}{suffix}"
        counter += 1

    dest.write_bytes(content)
    log.info("upload: saved %s (%d bytes) for user %s", dest.name, len(content), current_user.id)

    # ── create DB row ─────────────────────────────────────────────────────────
    doc = Document(
        user_id   = current_user.id,
        filename  = file.filename,
        file_type = suffix.lstrip("."),
        file_path = str(dest),
        file_size = len(content),
        status    = "pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # ── kick off background pipeline ──────────────────────────────────────────
    background_tasks.add_task(run_ingestion, doc.id, db)
    background_tasks.add_task(build_knowledge_graph, doc.id, db)

    log.info("upload: document %s queued for ingestion", doc.id)
    return DocumentOut.model_validate(doc)


# ── GET /documents ────────────────────────────────────────────────────────────
@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [DocumentOut.model_validate(d) for d in docs]


# ── GET /documents/{doc_id} ───────────────────────────────────────────────────
@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_owned_doc(doc_id, current_user.id, db)
    return DocumentOut.model_validate(doc)


# ── DELETE /documents/{doc_id} ────────────────────────────────────────────────
@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_owned_doc(doc_id, current_user.id, db)

    # remove file from disk
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()
        log.info("delete: removed file %s", file_path)

    # remove FAISS index folder
    faiss_path = Path(settings.faiss_dir) / doc_id
    if faiss_path.exists():
        shutil.rmtree(faiss_path)
        log.info("delete: removed FAISS index %s", faiss_path)

    # remove knowledge graph JSON
    graph_path = Path(settings.graphs_dir) / f"{doc_id}.json"
    if graph_path.exists():
        graph_path.unlink()
        log.info("delete: removed graph %s", graph_path)

    db.delete(doc)
    db.commit()


# ── helper ────────────────────────────────────────────────────────────────────
def _get_owned_doc(doc_id: str, user_id: str, db: Session) -> Document:
    """Fetch a document and verify it belongs to the requesting user."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    if doc.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return doc