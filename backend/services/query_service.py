"""
backend/services/query_service.py

Orchestrates the full RAG query pipeline:
    embed query → hybrid retrieve → rerank → graph context
    → build prompt → stream LLM tokens

Yields SSE-ready event dicts consumed by chat.py.
"""

import logging
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# How many chunks to retrieve and rerank
TOP_K_RETRIEVE = 20
TOP_K_RERANK   = 5


async def stream_query(
    query:     str,
    doc_ids:   list[int],
    user_id:   int,
    use_graph: bool = True,
) -> AsyncGenerator[dict, None]:
    """
    Async generator that yields event dicts:
        {"type": "citation", "chunks": [...]}   — sent once before tokens
        {"type": "token",    "content": "..."}  — one per streamed token
        {"type": "done"}                        — final event
        {"type": "error",    "detail": "..."}   — on failure
    """
    try:
        # --------------------------------------------------------------
        # 1. Embed the query
        # --------------------------------------------------------------
        from ai.embedding.embedder import Embedder
        embedder    = Embedder()
        query_vec   = embedder.embed_text(query)

        # --------------------------------------------------------------
        # 2. Hybrid retrieval (dense + BM25 → RRF fusion)
        # --------------------------------------------------------------
        from ai.vectorstore.faiss_store    import FAISSStore
        from ai.vectorstore.metadata_store import MetadataStore
        from ai.retrieval.hybrid_retriever import HybridRetriever

        faiss_store = FAISSStore(index_id=f"user_{user_id}")
        meta_store  = MetadataStore()

        retriever   = HybridRetriever(faiss_store, meta_store)
        candidates  = retriever.retrieve(
            query=query,
            query_vector=query_vec,
            doc_ids=doc_ids if doc_ids else None,
            top_k=TOP_K_RETRIEVE,
        )

        # --------------------------------------------------------------
        # 3. Rerank
        # --------------------------------------------------------------
        from ai.retrieval.reranker import Reranker
        reranker  = Reranker()
        top_chunks = reranker.rerank(query_vec, candidates, top_k=TOP_K_RERANK)

        # --------------------------------------------------------------
        # 4. Graph context (optional)
        # --------------------------------------------------------------
        graph_context = ""
        if use_graph and doc_ids:
            graph_context = _get_graph_context(query, doc_ids)

        # --------------------------------------------------------------
        # 5. Emit citations before streaming starts
        # --------------------------------------------------------------
        citation_data = [
            {
                "chunk_id":  c.chunk_id,
                "text":      c.text[:300],   # preview only
                "source":    c.metadata.get("source", ""),
                "page":      c.metadata.get("page_num"),
            }
            for c in top_chunks
        ]
        yield {"type": "citation", "chunks": citation_data}

        # --------------------------------------------------------------
        # 6. Build prompt
        # --------------------------------------------------------------
        from ai.generation.prompt_builder import build_prompt
        messages = build_prompt(
            query=query,
            chunks=top_chunks,
            graph_context=graph_context,
        )

        # --------------------------------------------------------------
        # 7. Stream tokens from Ollama
        # --------------------------------------------------------------
        from ai.generation.llm_client import LLMClient
        client = LLMClient()

        for token in client.stream(messages):
            yield {"type": "token", "content": token}

        yield {"type": "done"}

    except Exception as e:
        logger.error(f"[query_service] stream_query failed: {e}", exc_info=True)
        yield {"type": "error", "detail": str(e)}


def _get_graph_context(query: str, doc_ids: list[int]) -> str:
    """
    Collect graph context strings for each doc and join them.
    Non-fatal — returns empty string on any failure.
    """
    parts = []
    try:
        from knowledge_graph.graph_store     import GraphStore
        from knowledge_graph.graph_retriever import GraphRetriever

        store = GraphStore()
        for doc_id in doc_ids:
            graph = store.load(doc_id=doc_id)
            if graph is None:
                continue
            retriever = GraphRetriever(graph)
            ctx = retriever.get_context_for_query(query)
            if ctx:
                parts.append(ctx)
    except Exception as e:
        logger.warning(f"[query_service] graph context failed (non-fatal): {e}")

    return "\n\n".join(parts)