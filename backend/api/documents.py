"""
backend/api/documents.py

Routes:
    POST   /documents/upload      — upload a file, trigger ingestion
    GET    /documents             — list current user's documents
    GET    /documents/{id}        — get single document metadata
    DELETE /documents/{id}        — delete document + all its data
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.db.database import get_db
from backend.db.models import User, Document
from backend.auth.middleware import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).resolve().parents[3]
UPLOAD_DIR  = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md"}
MAX_FILE_SIZE_MB   = 50


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
class DocumentOut(BaseModel):
    id:            int
    filename:      str
    original_name: str
    file_type:     str
    file_size:     int
    status:        str
    chunk_count:   int | None
    has_graph:     bool
    uploaded_at:   datetime
    processed_at:  datetime | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _get_doc_or_404(doc_id: int, user: User, db: Session) -> Document:
    doc = db.query(Document).filter(
        Document.id == doc_id,
        Document.user_id == user.id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _safe_filename(user_id: int, original: str) -> str:
    """Prefix with user_id + timestamp to avoid collisions."""
    suffix = Path(original).suffix.lower()
    stem   = Path(original).stem[:40]          # trim long names
    ts     = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{user_id}_{ts}_{stem}{suffix}"


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------
@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db:   Session    = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --- validate extension ---
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    # --- read & size-check ---
    contents = await file.read()
    size_mb   = len(contents) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Max is {MAX_FILE_SIZE_MB} MB.",
        )

    # --- save to disk ---
    safe_name = _safe_filename(current_user.id, file.filename)
    dest_path = UPLOAD_DIR / safe_name
    dest_path.write_bytes(contents)

    # --- create DB record ---
    doc = Document(
        user_id=current_user.id,
        filename=safe_name,
        original_name=file.filename,
        file_type=suffix.lstrip("."),
        file_size=len(contents),
        file_path=str(dest_path),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # --- kick off ingestion in background ---
    background_tasks.add_task(_run_ingestion, doc.id)

    return doc


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------
@router.get("", response_model=list[DocumentOut])
def list_documents(
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


# ---------------------------------------------------------------------------
# GET /documents/{id}
# ---------------------------------------------------------------------------
@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    db:     Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_doc_or_404(doc_id, current_user, db)


# ---------------------------------------------------------------------------
# DELETE /documents/{id}
# ---------------------------------------------------------------------------
@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    db:     Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = _get_doc_or_404(doc_id, current_user, db)

    # remove file from disk
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except Exception:
        pass  # don't block deletion if file already gone

    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Background ingestion task
# (calls ingest_service — wired up once services/ is built)
# ---------------------------------------------------------------------------
def _run_ingestion(doc_id: int):
    """
    Runs after upload returns. Updates doc status in the DB.
    Imports ingest_service lazily so the API starts even if AI deps
    aren't fully installed yet.
    """
    from backend.db.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        try:
            from backend.services.ingest_service import ingest_document
            chunk_count, has_graph = ingest_document(doc.file_path, doc.id, doc.user_id)

            doc.status      = "ready"
            doc.chunk_count = chunk_count
            doc.has_graph   = has_graph
            doc.processed_at = datetime.now(timezone.utc)

        except Exception as e:
            doc.status        = "failed"
            doc.error_message = str(e)

        db.commit()
    finally:
        db.close()