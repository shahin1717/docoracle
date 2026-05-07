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
) -> Generator[str, None, None]:
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
    try:
        # ── 1. embed query ────────────────────────────────────────────────────
        from ai.embedding.embedder import Embedder
        embedder = Embedder(
            base_url=settings.ollama_base_url,
            model=settings.embed_model,
        )
        query_vector = embedder.embed_text(query)

        # ── 2. load stores for each requested document ────────────────────────
        from ai.vectorstore.faiss_store import FAISSStore
        from ai.vectorstore.metadata_store import MetadataStore

        meta_store = MetadataStore(db_path=settings.docs_db_path)

        # merge FAISS indices from all selected docs
        from ai.retrieval.dense_retriever import DenseRetriever
        from ai.retrieval.bm25_retriever import BM25Retriever
        from ai.retrieval.hybrid_retriever import HybridRetriever
        from ai.retrieval.reranker import Reranker

        all_chunks = []
        all_vectors = []

        for doc_id in doc_ids:
            faiss_path = Path(settings.faiss_dir) / doc_id
            if not faiss_path.exists():
                log.warning("query: no FAISS index for doc %s — skipping", doc_id)
                continue
            store = FAISSStore(index_path=str(faiss_path))
            store.load()
            chunks = meta_store.get_chunks_for_doc(doc_id)
            all_chunks.extend(chunks)
            all_vectors.extend(store.get_all_vectors())

        if not all_chunks:
            yield "No indexed documents found for your query."
            return

        # ── 3. hybrid retrieval ───────────────────────────────────────────────
        dense    = DenseRetriever(vectors=all_vectors, chunks=all_chunks)
        bm25     = BM25Retriever(chunks=all_chunks)
        hybrid   = HybridRetriever(dense=dense, bm25=bm25)

        candidates = hybrid.retrieve(
            query=query,
            query_vector=query_vector,
            top_k=settings.retrieval_top_k,
        )
        log.info("query: %d candidates from hybrid retrieval", len(candidates))

        # ── 4. rerank ─────────────────────────────────────────────────────────
        reranker = Reranker(embedder=embedder)
        top_chunks = reranker.rerank(
            query=query,
            query_vector=query_vector,
            candidates=candidates,
            top_k=settings.rerank_top_k,
        )
        log.info("query: %d chunks after reranking", len(top_chunks))

        # ── 5. graph context ──────────────────────────────────────────────────
        graph_context = ""
        try:
            from knowledge_graph.graph_store import GraphStore
            from knowledge_graph.graph_retriever import GraphRetriever

            graphs_dir = Path(settings.graphs_dir)
            all_graph_facts = []

            for doc_id in doc_ids:
                graph_path = graphs_dir / f"{doc_id}.json"
                if graph_path.exists():
                    g_store = GraphStore(str(graphs_dir))
                    graph = g_store.load(doc_id)
                    retriever = GraphRetriever(graph)
                    facts = retriever.get_context_for_query(query)
                    all_graph_facts.extend(facts)

            if all_graph_facts:
                graph_context = "\n".join(all_graph_facts)
                log.info("query: %d graph facts added", len(all_graph_facts))

        except Exception:
            log.warning("query: graph context unavailable — continuing without it")

        # ── 6. build prompt ───────────────────────────────────────────────────
        from ai.generation.prompt_builder import build_prompt
        chunk_ids = [c.chunk_id for c in top_chunks]
        messages = build_prompt(
            query=query,
            chunk_ids=chunk_ids,
            store=meta_store,
            graph_context=graph_context,
        )

        # ── 7. stream tokens ──────────────────────────────────────────────────
        from ai.generation.llm_client import LLMClient
        llm = LLMClient(
            base_url=settings.ollama_base_url,
            model=settings.llm_model,
        )
        log.info("query: streaming from %s", settings.llm_model)
        yield from llm.stream(messages)

    except Exception as exc:
        log.exception("query: pipeline error")
        yield f"\n\n[Error: {exc}]"


def get_source_chunks(chunk_ids: list[str]) -> list[dict]:
    """
    Return chunk text + metadata for citation cards.
    Called after streaming completes with the chunk_ids used.
    """
    from ai.vectorstore.metadata_store import MetadataStore
    meta_store = MetadataStore(db_path=settings.docs_db_path)
    return [meta_store.get_chunk(cid) for cid in chunk_ids if cid]