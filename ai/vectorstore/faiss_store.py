import numpy as np
import faiss
import pickle
from pathlib import Path


class FAISSStore:
    """
    Stores and searches embedding vectors using FAISS.
    Uses cosine similarity (inner product on normalized vectors).
    """

    def __init__(self, dim: int = 768):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)  # inner product = cosine on normalized vecs
        self._chunk_ids: list[str] = []      # maps FAISS position → chunk_id

    def add(self, chunk_ids: list[str], vectors: np.ndarray):
        """Add vectors to the index. vectors shape: (n, dim)"""
        normalized = self._normalize(vectors)
        self.index.add(normalized)
        self._chunk_ids.extend(chunk_ids)

    def search(self, query_vector: np.ndarray, top_k: int = 5) -> list[tuple[str, float]]:
        """
        Search for top_k most similar chunks.
        Returns list of (chunk_id, score) sorted by score descending.
        """
        normalized = self._normalize(query_vector.reshape(1, -1))
        scores, indices = self.index.search(normalized, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            results.append((self._chunk_ids[idx], float(score)))
        return results

    def save(self, path: str | Path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(path / "index.faiss"))
        with open(path / "chunk_ids.pkl", "wb") as f:
            pickle.dump(self._chunk_ids, f)

    def load(self, path: str | Path):
        path = Path(path)
        self.index = faiss.read_index(str(path / "index.faiss"))
        with open(path / "chunk_ids.pkl", "rb") as f:
            self._chunk_ids = pickle.load(f)

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return (vectors / norms).astype(np.float32)

    @property
    def size(self) -> int:
        return self.index.ntotal