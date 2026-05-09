# backend/services/ingest_service.py
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import Document

log = logging.getLogger(__name__)


def run_ingestion(document_id: str, db: Session) -> None:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        log.error("ingest: document %s not found", document_id)
        return

    _set_status(doc, "processing", db)

    try:
        from ai.ingestion.router import parse_document
        parsed = parse_document(doc.file_path)
        log.info("ingest: parsed %s — %d pages", doc.filename, parsed.page_count)

        from ai.chunker.chunker import Chunker
        chunks = Chunker(
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        ).chunk_document(parsed)
        log.info("ingest: %d chunks created", len(chunks))

        from ai.embedding.embedder import Embedder
        import numpy as np
        embedder = Embedder(
            model=settings.embed_model,
            ollama_url=f"{settings.ollama_base_url}/api/embeddings",
        )
        embedded = embedder.embed_chunks(chunks)
        log.info("ingest: %d chunks embedded", len(embedded))

        from ai.vectorstore.faiss_store import FAISSStore
        faiss_path = Path(settings.faiss_dir) / doc.id
        store = FAISSStore()
        vectors = np.stack([e.vector for e in embedded])
        ids = [e.chunk_id for e in embedded]
        store.add(ids, vectors)
        store.save(faiss_path)
        log.info("ingest: FAISS index saved → %s", faiss_path)

        from ai.vectorstore.metadata_store import MetadataStore
        meta_store = MetadataStore(db_path=settings.docs_db_path)
        meta_store.insert_chunks([{
            "chunk_id":    e.chunk_id,
            "source_path": e.chunk.source_path,
            "title":       e.chunk.metadata["title"],
            "file_type":   e.chunk.metadata["file_type"],
            "page_num":    e.chunk.page_num,
            "chunk_index": e.chunk.chunk_index,
            "text":        e.chunk.text,
            "token_count": e.chunk.token_count,
            "metadata":    e.chunk.metadata,
        } for e in embedded])
        log.info("ingest: metadata saved to docs.db")

        doc.chunk_count = len(chunks)
        doc.page_count  = parsed.page_count
        _set_status(doc, "ready", db)
        log.info("ingest: document %s → ready", doc.id)

    except Exception as exc:
        log.exception("ingest: failed for document %s", document_id)
        doc.error_msg = str(exc)
        _set_status(doc, "failed", db)


def _set_status(doc: Document, status: str, db: Session) -> None:
    doc.status = status
    db.add(doc)
    db.commit()
    db.refresh(doc)