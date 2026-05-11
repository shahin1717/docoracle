# backend/services/kg_service.py
import logging
from pathlib import Path

from backend.config import settings
from backend.db.models import Document

log = logging.getLogger(__name__)


def build_knowledge_graph(document_id: str) -> None:
    """Build Knowledge Graph in background"""
    db = None
    try:
        from backend.db.database import SessionLocal
        db = SessionLocal()

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or doc.status != "ready":
            return

        log.info(f"🔨 Building Knowledge Graph for: {doc.filename}")

        from ai.vectorstore.metadata_store import MetadataStore
        meta_store = MetadataStore(db_path=settings.docs_db_path)
        chunks = meta_store.get_chunks_for_doc(doc.file_path)

        if not chunks:
            return

        full_text = "\n".join(c["text"] for c in chunks)

        from knowledge_graph.entity_extractor import EntityExtractor
        entities = EntityExtractor().extract(full_text)

        from knowledge_graph.relation_extractor import RelationExtractor
        triples = RelationExtractor().extract(full_text, entities)

        from knowledge_graph.graph_builder import GraphBuilder
        graph = GraphBuilder().build(entities=entities, triples=triples)

        # Save graph
        from knowledge_graph.graph_store import GraphStore
        g_store = GraphStore(str(settings.graphs_dir))
        g_store.save(graph, document_id)

        try:
            doc.kg_ready = True
            doc.kg_status = "ready"
            db.add(doc)
            db.commit()
            log.info(f"✅ Knowledge Graph built successfully for {document_id} ({graph.number_of_nodes()} nodes)")
        except Exception as update_err:
            if "StaleDataError" in str(type(update_err)):
                log.warning(f"Document {document_id} was deleted before KG could be saved.")
            else:
                raise update_err

    except Exception as e:
        log.exception(f"KG build failed for {document_id}")
        if db:
            try:
                doc = db.query(Document).filter(Document.id == document_id).first()
                if doc:
                    doc.kg_status = "error"
                    db.add(doc)
                    db.commit()
            except Exception:
                pass
    finally:
        if db:
            db.close()


def get_graph_data(document_id: str) -> dict:
    """Return graph for frontend"""
    try:
        from knowledge_graph.graph_store import GraphStore
        from knowledge_graph.graph_exporter import GraphExporter

        g_store = GraphStore(str(settings.graphs_dir))
        graph = g_store.load(document_id)

        exporter = GraphExporter()
        return exporter.to_frontend_json(graph)
    except Exception as e:
        log.error(f"Failed to load graph {document_id}: {e}")
        raise FileNotFoundError(f"Graph not found for document {document_id}")