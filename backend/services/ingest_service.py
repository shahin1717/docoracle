# backend/services/ingest_service.py
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import Document

log = logging.getLogger(__name__)


# ── main entry point ──────────────────────────────────────────────────────────
def run_ingestion(document_id: str, db: Session) -> None:
    """
    Full ingestion pipeline for one document.
    Called in a background task after upload.

    Steps:
        1. Load Document row, mark status = processing
        2. Parse file  → ParsedDocument
        3. Chunk text  → list[Chunk]
        4. Embed chunks → list[EmbeddedChunk]
        5. Save vectors → FAISSStore
        6. Save text   → MetadataStore
        7. Mark status = ready
        8. On any error → mark status = failed, store error_msg
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        log.error("ingest: document %s not found", document_id)
        return

    _set_status(doc, "processing", db)

    try:
        # ── 1. parse ──────────────────────────────────────────────────────────
        from ai.ingestion.router import parse_document
        parsed = parse_document(doc.file_path)
        log.info("ingest: parsed %s — %d sections", doc.filename, len(parsed.sections))

        # ── 2. chunk ──────────────────────────────────────────────────────────
        from ai.chunker.chunker import Chunker
        chunker = Chunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )
        chunks = chunker.chunk(parsed)
        log.info("ingest: %d chunks created", len(chunks))

        # ── 3. embed ──────────────────────────────────────────────────────────
        from ai.embedding.embedder import Embedder
        embedder = Embedder(
            base_url=settings.ollama_base_url,
            model=settings.embed_model,
        )
        embedded = embedder.embed_chunks(chunks)
        log.info("ingest: %d chunks embedded", len(embedded))

        # ── 4. save vectors ───────────────────────────────────────────────────
        from ai.vectorstore.faiss_store import FAISSStore
        faiss_path = Path(settings.faiss_dir) / doc.id
        store = FAISSStore(index_path=str(faiss_path))
        store.add(embedded)
        store.save()
        log.info("ingest: FAISS index saved → %s", faiss_path)

        # ── 5. save metadata ──────────────────────────────────────────────────
        from ai.vectorstore.metadata_store import MetadataStore
        meta_store = MetadataStore(db_path=settings.docs_db_path)
        meta_store.add(embedded, source_doc_id=doc.id)
        log.info("ingest: metadata saved to docs.db")

        # ── 6. update document row ────────────────────────────────────────────
        doc.chunk_count = len(chunks)
        doc.page_count  = parsed.page_count if hasattr(parsed, "page_count") else 0
        _set_status(doc, "ready", db)
        log.info("ingest: document %s → ready", doc.id)

    except Exception as exc:
        log.exception("ingest: failed for document %s", document_id)
        doc.error_msg = str(exc)
        _set_status(doc, "failed", db)


# ── helpers ───────────────────────────────────────────────────────────────────
def _set_status(doc: Document, status: str, db: Session) -> None:
    doc.status = status
    db.add(doc)
    db.commit()
    db.refresh(doc)