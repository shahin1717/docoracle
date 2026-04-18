from ai.retrieval.dense_retriever import DenseRetriever
from ai.retrieval.bm25_retriever import BM25Retriever


class HybridRetriever:
    """
    Combines dense (FAISS) and sparse (BM25) results
    using Reciprocal Rank Fusion (RRF).

    RRF formula: score = sum(1 / (k + rank))
    where k=60 is a constant that dampens the effect of high ranks.

    Why RRF instead of weighted sum?
    - No need to tune weights
    - Scores from dense and sparse are on different scales — RRF
      only cares about rank position, not raw score values
    """

    def __init__(self, dense: DenseRetriever, bm25: BM25Retriever, k: int = 60):
        self.dense = dense
        self.bm25 = bm25
        self.k = k

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        dense_results = self.dense.retrieve(query, top_k=top_k * 2)
        bm25_results  = self.bm25.retrieve(query, top_k=top_k * 2)

        rrf_scores: dict[str, float] = {}

        for rank, (chunk_id, _) in enumerate(dense_results, start=1):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (self.k + rank)

        for rank, (chunk_id, _) in enumerate(bm25_results, start=1):
            rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0) + 1 / (self.k + rank)

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]