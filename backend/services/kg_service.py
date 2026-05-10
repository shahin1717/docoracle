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
    db = None
    try:
        from backend.db.database import SessionLocal
        db = SessionLocal()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            log.error(f"Document {document_id} not found for KG build")
            return

        if doc.status != "ready":
            log.warning(f"Document {document_id} not ready yet — skipping KG")
            return

        log.info(f"Starting KG build for {doc.filename}")

        from ai.vectorstore.metadata_store import MetadataStore
        meta_store = MetadataStore(db_path=settings.docs_db_path)
        chunks = meta_store.get_chunks_for_doc(doc.file_path)

        if not chunks:
            log.warning(f"No chunks found for doc {document_id}")
            return

        full_text = "\n".join(c["text"] for c in chunks)

        from knowledge_graph.entity_extractor import EntityExtractor
        entity_extractor = EntityExtractor()
        entities = entity_extractor.extract(full_text)

        from knowledge_graph.relation_extractor import RelationExtractor
        relation_extractor = RelationExtractor()
        triples = relation_extractor.extract(full_text, entities)

        from knowledge_graph.graph_builder import GraphBuilder
        builder = GraphBuilder()
        graph = builder.build(entities=entities, triples=triples)

        from knowledge_graph.graph_store import GraphStore
        g_store = GraphStore(str(settings.graphs_dir))
        g_store.save(graph, document_id)

        doc.kg_ready = True
        db.add(doc)
        db.commit()

        log.info(f"✅ Knowledge Graph built successfully for {document_id}")

    except Exception as exc:
        log.exception(f"KG build failed for document {document_id}")
        # KG failure is non-fatal
    finally:
        if db:
            db.close()
            
            
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