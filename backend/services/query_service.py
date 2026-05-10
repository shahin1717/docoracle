# backend/services/query_service.py
import logging
from pathlib import Path
from typing import Generator

from backend.config import settings

log = logging.getLogger(__name__)


def stream_answer(
    query: str,
    doc_ids: list[str],
    user_id: str,
    model: str | None = None,        # ← user's chosen model, falls back to settings
) -> Generator[str, None, None]:
<<<<<<< HEAD
    """
    Full RAG pipeline — yields answer tokens one by one.

    Steps:
        1. Embed the query
        2. HybridRetriever  → top-K candidate chunk IDs  (dense + BM25 + RRF)
        3. Reranker          → top rerank_top_k chunks
        4. GraphRetriever    → graph context sentences
        5. build_prompt      → messages list
        6. LLMClient.stream  → yield tokens to caller (FastAPI SSE)
    """
    llm_model = model or settings.llm_model
    log.info("query: using model %s", llm_model)

=======
>>>>>>> main
    try:
        from ai.embedding.embedder import Embedder
        embedder = Embedder(
            model=settings.embed_model,
            ollama_url=f"{settings.ollama_base_url}/api/embeddings",
        )

        from ai.vectorstore.faiss_store import FAISSStore
        from ai.vectorstore.metadata_store import MetadataStore
        from ai.retrieval.dense_retriever import DenseRetriever
        from ai.retrieval.bm25_retriever import BM25Retriever
        from ai.retrieval.hybrid_retriever import HybridRetriever
        from ai.retrieval.reranker import Reranker
        from backend.db.database import SessionLocal
        from backend.db.models import Document as DocumentModel

        meta_store = MetadataStore(db_path=settings.docs_db_path)
<<<<<<< HEAD
        all_chunks  = []
        all_vectors = []
=======
        all_chunks = []
        last_faiss_path = None
>>>>>>> main

        _db = SessionLocal()
        for doc_id in doc_ids:
            faiss_path = Path(settings.faiss_dir) / doc_id
            if not faiss_path.exists():
                log.warning("query: no FAISS index for doc %s — skipping", doc_id)
                continue
            db_doc = _db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
            if not db_doc:
                continue
            chunks = meta_store.get_chunks_for_doc(db_doc.file_path)
            all_chunks.extend(chunks)
            last_faiss_path = faiss_path
        _db.close()

        if not all_chunks or last_faiss_path is None:
            yield "No indexed documents found for your query."
            return

        store = FAISSStore()
        store.load(last_faiss_path)
        dense  = DenseRetriever(store=store, embedder=embedder)
        bm25   = BM25Retriever()
        bm25.index([{"chunk_id": c["chunk_id"], "text": c["text"]} for c in all_chunks])
        hybrid = HybridRetriever(dense=dense, bm25=bm25)
        candidates = hybrid.retrieve(query, top_k=settings.retrieval_top_k)
        log.info("query: %d candidates from hybrid retrieval", len(candidates))

<<<<<<< HEAD
        # ── 4. rerank ─────────────────────────────────────────────────────────
        reranker   = Reranker(embedder=embedder)
=======
        chunk_dicts = [{"chunk_id": c["chunk_id"], "text": c["text"]} for c in all_chunks]
        reranker = Reranker(embedder=embedder)
>>>>>>> main
        top_chunks = reranker.rerank(
            query=query,
            candidates=candidates,
            chunks=chunk_dicts,
        )
        log.info("query: %d chunks after reranking", len(top_chunks))

        graph_context = ""
        try:
            from knowledge_graph.graph_store import GraphStore
            from knowledge_graph.graph_retriever import GraphRetriever
<<<<<<< HEAD

=======
            graphs_dir = Path(settings.graphs_dir)
>>>>>>> main
            all_graph_facts = []
            for doc_id in doc_ids:
                graph_path = Path(settings.graphs_dir) / f"{doc_id}.json"
                if graph_path.exists():
<<<<<<< HEAD
                    g_store  = GraphStore(str(settings.graphs_dir))
                    graph    = g_store.load(doc_id)
                    retriever = GraphRetriever(graph)
                    facts    = retriever.get_context_for_query(query)
                    all_graph_facts.extend(facts)

=======
                    graph = GraphStore(str(graphs_dir)).load(doc_id)
                    facts = GraphRetriever(graph).get_context_for_query(query)
                    if facts:
                        all_graph_facts.append(facts)
>>>>>>> main
            if all_graph_facts:
                graph_context = "\n".join(all_graph_facts)
                log.info("query: graph context added")
        except Exception:
            log.warning("query: graph context unavailable — continuing without it")

        from ai.generation.prompt_builder import build_prompt
<<<<<<< HEAD
        chunk_ids = [c.chunk_id for c in top_chunks]
        messages  = build_prompt(
            query=query,
            chunk_ids=chunk_ids,
            store=meta_store,
            graph_context=graph_context,
        )
=======
        chunk_ids = [c[0] for c in top_chunks]
        messages = build_prompt(query=query, chunk_ids=chunk_ids, metadata_store=meta_store)
        if graph_context:
            messages[1]["content"] = graph_context + "\n\n" + messages[1]["content"]
>>>>>>> main

        from ai.generation.llm_client import LLMClient
        llm = LLMClient(
<<<<<<< HEAD
            base_url=settings.ollama_base_url,
            model=llm_model,               # ← user's chosen model
=======
            model=settings.llm_model,
            ollama_url=f"{settings.ollama_base_url}/api/chat",
>>>>>>> main
        )
        yield from llm.stream(messages)

    except Exception as exc:
        log.exception("query: pipeline error")
        yield f"\n\n[Error: {exc}]"


def get_source_chunks(chunk_ids: list[str]) -> list[dict]:
<<<<<<< HEAD
    """Return chunk text + metadata for citation cards."""
=======
>>>>>>> main
    from ai.vectorstore.metadata_store import MetadataStore
    meta_store = MetadataStore(db_path=settings.docs_db_path)
    return [meta_store.get_chunk(cid) for cid in chunk_ids if cid]