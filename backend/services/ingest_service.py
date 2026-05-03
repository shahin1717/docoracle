"""
backend/services/ingest_service.py

Orchestrates the full ingestion pipeline for an uploaded document:
    parse → chunk → embed → store vectors + metadata → build knowledge graph

Called by documents.py background task after a file is saved to disk.
Returns (chunk_count, has_graph) so the Document record can be updated.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ingest_document(file_path: str, doc_id: int, user_id: int) -> tuple[int, bool]:
    """
    Run the full ingestion pipeline.

    Parameters
    ----------
    file_path : absolute path to the uploaded file on disk
    doc_id    : Document.id — used to namespace FAISS + graph storage
    user_id   : User.id — stored in chunk metadata for filtering

    Returns
    -------
    (chunk_count, has_graph)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Upload not found: {file_path}")

    # ------------------------------------------------------------------
    # 1. Parse
    # ------------------------------------------------------------------
    from ai.ingestion.router import parse_document
    logger.info(f"[ingest] parsing {path.name}")
    parsed = parse_document(str(path))

    if not parsed.text.strip():
        raise ValueError("Document appears to be empty or image-only")

    # ------------------------------------------------------------------
    # 2. Chunk
    # ------------------------------------------------------------------
    from ai.chunker.chunker import Chunker
    logger.info(f"[ingest] chunking")
    chunker = Chunker(chunk_size=512, overlap=64)
    chunks  = chunker.chunk(parsed)

    if not chunks:
        raise ValueError("No chunks produced from document")

    # ------------------------------------------------------------------
    # 3. Embed
    # ------------------------------------------------------------------
    from ai.embedding.embedder import Embedder
    logger.info(f"[ingest] embedding {len(chunks)} chunks")
    embedder       = Embedder()
    embedded_chunks = embedder.embed_chunks(chunks)

    # ------------------------------------------------------------------
    # 4. Store vectors (FAISS) + metadata (SQLite docs.db)
    # ------------------------------------------------------------------
    from ai.vectorstore.faiss_store    import FAISSStore
    from ai.vectorstore.metadata_store import MetadataStore

    faiss_store = FAISSStore(index_id=f"user_{user_id}")
    meta_store  = MetadataStore()

    logger.info(f"[ingest] storing vectors + metadata")
    faiss_store.add(embedded_chunks, doc_id=doc_id)
    meta_store.add(embedded_chunks,  doc_id=doc_id)

    faiss_store.save()

    # ------------------------------------------------------------------
    # 5. Knowledge graph
    # ------------------------------------------------------------------
    has_graph = False
    try:
        from knowledge_graph.entity_extractor   import EntityExtractor
        from knowledge_graph.relation_extractor  import RelationExtractor
        from knowledge_graph.graph_builder       import GraphBuilder
        from knowledge_graph.graph_store         import GraphStore

        logger.info(f"[ingest] building knowledge graph")
        entities  = EntityExtractor().extract(parsed.text)
        triples   = RelationExtractor().extract(parsed.text)
        graph     = GraphBuilder().build(entities, triples)
        GraphStore().save(graph, doc_id=doc_id)
        has_graph = True

    except Exception as e:
        # KG failure is non-fatal — RAG still works without it
        logger.warning(f"[ingest] knowledge graph failed (non-fatal): {e}")

    logger.info(f"[ingest] done — {len(chunks)} chunks, has_graph={has_graph}")
    return len(chunks), has_graph