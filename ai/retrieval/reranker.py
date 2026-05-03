import requests


OLLAMA_URL = "http://localhost:11434/api/embeddings"


class Reranker:
    """
    Cross-encoder style reranker using embedding similarity.

    For each (query, chunk) pair we compute the cosine similarity
    of their embeddings and re-sort. This is a lightweight reranker
    that doesn't need a separate cross-encoder model.

    On your machine you can upgrade this to use
    cross-encoder/ms-marco-MiniLM-L-6-v2 via sentence-transformers
    for significantly better reranking quality.
    """

    def __init__(self, embedder, top_k: int = 5):
        self.embedder = embedder
        self.top_k = top_k

    def rerank(
        self,
        query: str,
        candidates: list[tuple[str, float]],
        chunks: list[dict],
    ) -> list[tuple[str, float]]:
        """
        candidates: list of (chunk_id, score) from hybrid retriever
        chunks:     list of chunk dicts with chunk_id and text
        Returns reranked list of (chunk_id, score).
        """
        if not candidates:
            return []

        import numpy as np

        query_vec = self.embedder.embed_text(query)
        text_by_id = {c["chunk_id"]: c["text"] for c in chunks}

        scored = []
        for chunk_id, _ in candidates:
            text = text_by_id.get(chunk_id, "")
            if not text:
                continue
            chunk_vec = self.embedder.embed_text(text)
            score = float(np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec) + 1e-8
            ))
            scored.append((chunk_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:self.top_k]