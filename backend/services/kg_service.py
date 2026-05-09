# backend/services/kg_service.py
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import Document

log = logging.getLogger(__name__)


# ── build ─────────────────────────────────────────────────────────────────────
def build_knowledge_graph(document_id: str, db: Session) -> None:
    """
    Build and persist a knowledge graph for one document.
    Called as a BackgroundTask after ingestion completes.

    Steps:
        1. Load chunk texts from MetadataStore
        2. Extract entities
        3. Extract relations → triples
        4. Build NetworkX DiGraph
        5. Save graph JSON to data/graphs/<doc_id>.json
        6. Mark document.kg_ready = True
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        log.error("kg: document %s not found", document_id)
        return

    if doc.status != "ready":
        log.warning("kg: document %s not ready yet — skipping KG build", document_id)
        return

    log.info("kg: starting graph build for %s", doc.filename)

    try:
        # ── 1. load chunk texts ───────────────────────────────────────────────
        from ai.vectorstore.metadata_store import MetadataStore
        meta_store = MetadataStore(db_path=settings.docs_db_path)
        chunks = meta_store.get_chunks_for_doc(doc.file_path)

        if not chunks:
            log.warning("kg: no chunks found for doc %s", document_id)
            return

        full_text = "\n".join(c["text"] for c in chunks)
        log.info("kg: loaded %d chunks, %d chars", len(chunks), len(full_text))

        # ── 2. extract entities ───────────────────────────────────────────────
        from knowledge_graph.entity_extractor import EntityExtractor
        entity_extractor = EntityExtractor()
        entities = entity_extractor.extract(full_text)
        log.info("kg: %d entities extracted", len(entities))

        # ── 3. extract relations ──────────────────────────────────────────────
        from knowledge_graph.relation_extractor import RelationExtractor
        relation_extractor = RelationExtractor()
        triples = relation_extractor.extract(full_text, entities)
        log.info("kg: %d triples extracted", len(triples))

        # ── 4. build graph ────────────────────────────────────────────────────
        from knowledge_graph.graph_builder import GraphBuilder
        builder = GraphBuilder()
        graph = builder.build(entities=entities, triples=triples)
        log.info(
            "kg: graph built — %d nodes, %d edges",
            graph.number_of_nodes(),
            graph.number_of_edges(),
        )

        # ── 5. save graph ─────────────────────────────────────────────────────
        from knowledge_graph.graph_store import GraphStore
        graphs_dir = str(settings.graphs_dir)
        g_store = GraphStore(graphs_dir)
        g_store.save(graph, document_id)
        log.info("kg: graph saved → %s/%s.json", graphs_dir, document_id)

        # ── 6. mark kg_ready ──────────────────────────────────────────────────
        doc.kg_ready = True
        db.add(doc)
        db.commit()
        log.info("kg: document %s kg_ready = True", document_id)

    except Exception as exc:
        log.exception("kg: build failed for document %s", document_id)
        # KG failure is non-fatal — document stays usable for RAG


# ── serve ─────────────────────────────────────────────────────────────────────
def get_graph_data(document_id: str) -> dict:
    """
    Load and return graph JSON for the frontend (react-force-graph format).
    Raises FileNotFoundError if the graph hasn't been built yet.
    """
    from knowledge_graph.graph_store import GraphStore
    from knowledge_graph.graph_exporter import GraphExporter

    graphs_dir = str(settings.graphs_dir)
    g_store = GraphStore(graphs_dir)

    graph_path = Path(settings.graphs_dir) / f"{document_id}.json"
    if not graph_path.exists():
        raise FileNotFoundError(f"Graph not found for document {document_id}")

    graph = g_store.load(document_id)
    exporter = GraphExporter()
    return exporter.to_frontend_json(graph)