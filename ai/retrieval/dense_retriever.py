import numpy as np
from ai.vectorstore.faiss_store import FAISSStore
from ai.embedding.embedder import Embedder


class DenseRetriever:
    """
    Searches FAISS index using the query embedding.
    Returns chunk_ids ranked by cosine similarity.
    """

    def __init__(self, store: FAISSStore, embedder: Embedder):
        self.store = store
        self.embedder = embedder

    def retrieve(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """Returns list of (chunk_id, score)."""
        vector = self.embedder.embed_text(query)
        return self.store.search(vector, top_k=top_k)